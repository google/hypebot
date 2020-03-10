# Copyright 2018 The Hypebot Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Library for commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from functools import partial
from functools import wraps
import random
import re
from threading import Lock
import time

from absl import logging

from hypebot import hype_types
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2

from typing import Any, Callable, Dict, List, Optional, Text, Tuple


class BaseCommand(object):
  """Base class for commands."""

  DEFAULT_PARAMS = params_lib.HypeParams({
      # See _Ratelimit for details.
      'ratelimit': {
          'enabled': True,
          # One of USER, GLOBAL, or CHANNEL. Calls from the same scope are
          # rate-limitted.
          'scope': 'USER',
          # Minimum number of seconds to pass between calls.
          'interval': 5,
          # Will only ratelimit if _Handle returns a value.
          'return_only': False,
      },
      # Which channels (rooms) should handle the message.
      #
      # This operates in addition to the parsers and is useful for surfacing
      # different commands for different communities. E.g., !who could be
      # handled by different commands for a LoL or Overwatch channel.
      #
      # Default allows all channels to utilize command.  Otherwise, supply a
      # list of channels where the specified id must be a prefix of the incoming
      # message's channel.id.
      'channels': [''],
      # Alternatively, which channels should not handle the message. This takes
      # precedence over 'channels'.
      #
      # Default allows all channels to handle the message.
      'avoid_channels': [],
      # If the command should be invoked in all channels that match channels
      # above, or only the ones listed in core.params.main_channels.
      'main_channel_only': True,
      # By default, parsers may provide a `target_user` in their kwargs which
      # gets auto-converted into a User proto if the correponsing user exists.
      # If the user does not exist, the command will respond "Unknown user
      # $target_user" and not call the underlying `_Handle` method. If you
      # override this to `True`, it will create a fake user with user_id and
      # display_name set to target_user if the user does not exist.
      'target_any': False,
  })

  # Used to ignore a level of scoping.
  _DEFAULT_SCOPE = 'all'

  def __init__(self, params, core):
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    self._params.Lock()
    self.command_prefix = '%' if core.params.execution_mode.dev else '!'
    self._core = core
    self._parsers = []
    self._last_called = defaultdict(lambda: defaultdict(float))
    self._ratelimit_lock = Lock()
    self._spook_replies = util_lib.WeightedCollection(messages.SPOOKY_STRINGS)

  def Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
             message: Text) -> hype_types.CommandResponse:
    """Attempt to handle the message.

    First we check if this command is available for this channel. Then, we
    compare message against all parsers. If one of them accepts the message,
    send the parsed command to the internal _Handle function.

    Args:
      channel: Channel from which the message was received.
      user: User who invoked the command.
      message: Raw message from application.

    Returns:
      Response message from command.
    """
    if not self._InScope(channel):
      return
    for parser in self._parsers:
      take, args, kwargs = parser(channel, user, message)
      if take:
        if 'target_user' in kwargs and kwargs['target_user'] is not None:
          target_user = self._ParseCommandTarget(
              user, kwargs['target_user'], message)
          if not target_user:
            return 'Unrecognized user %s' % kwargs['target_user']
          kwargs['target_user'] = target_user

        # Ensure we don't handle the same message twice.
        return self._Ratelimit(channel, user, *args, **kwargs)

  def _InScope(self, channel: channel_pb2.Channel):
    """Determine if channel is in scope."""
    # DMs and system internal commands are always allowed.
    if channel.visibility in [
        channel_pb2.Channel.PRIVATE, channel_pb2.Channel.SYSTEM
    ]:
      return True
    # Channel scope
    if (not util_lib.MatchesAny(self._params.channels, channel) or
        util_lib.MatchesAny(self._params.avoid_channels, channel)):
      return False
    # MainChannelOnly
    if (self._params.main_channel_only and
        not util_lib.MatchesAny(self._core.params.main_channels, channel)):
      return False

    return True

  def _Ratelimit(self, channel: channel_pb2.Channel, user: user_pb2.User, *args,
                 **kwargs):
    """Ratelimits calls/responses from Handling the message.

    In general this, prevents the same user, channel, or global triggering a
    command in quick succession. This works by timing calls and verifying that
    future calls have exceeded the interval before invocation.

    Some commands like to handle every message, but only respond to a few. E.g.,
    MissingPing needs every message to record the most recent user, but only
    sends a response when someone types '?'. In this case, we always execute the
    command and only ratelimit the response. The restriction being, that it is
    safe to call on every invocation. E.g., do not transfer hypecoins.

    Args:
      channel: Passed through to _Handle.
      user: Passed through to _Handle.
      *args: Passed through to _Handle.
      **kwargs: Passed through to _Handle.

    Returns:
      Optional message(s) to reply to the channel.
    """
    if (not self._params.ratelimit.enabled or channel.visibility in [
        channel_pb2.Channel.PRIVATE, channel_pb2.Channel.SYSTEM
    ]):
      return self._Handle(channel, user, *args, **kwargs)

    scoped_channel = channel_pb2.Channel()
    scoped_channel.CopyFrom(channel)
    scoped_user_id = user.user_id
    if self._params.ratelimit.scope == 'GLOBAL':
      scoped_channel.id = self._DEFAULT_SCOPE
      scoped_user_id = self._DEFAULT_SCOPE
    elif self._params.ratelimit.scope == 'CHANNEL':
      scoped_user_id = self._DEFAULT_SCOPE

    with self._ratelimit_lock:
      t = time.time()
      delta_t = t - self._last_called[scoped_channel.id][scoped_user_id]
      response = None
      if self._params.ratelimit.return_only:
        response = self._Handle(channel, user, *args, **kwargs)
        if not response:
          return

      if delta_t < self._params.ratelimit.interval:
        logging.info('Call to %s._Handle ratelimited in %s for %s: %s < %s',
                     self.__class__.__name__, scoped_channel.id, scoped_user_id,
                     delta_t, self._params.ratelimit.interval)
        self._Reply(user, random.choice(messages.RATELIMIT_MEMES))
        return

      self._last_called[scoped_channel.id][scoped_user_id] = t
      return response or self._Handle(channel, user, *args, **kwargs)

  def _ParseCommandTarget(self, user: user_pb2.User, target_user: Text,
                          message: Text) -> Optional[user_pb2.User]:
    """Processes raw target_user into a User class, resolving 'me' to user."""
    # An empty target_user defaults to the calling user
    if target_user.strip() in ('', 'me'):
      self._core.last_command = partial(self.Handle, message=message)
      return user
    real_user = self._core.interface.FindUser(target_user)
    if self._params.target_any and not real_user:
      real_user = user_pb2.User(user_id=target_user, display_name=target_user)
    return real_user

  def _Reply(self, *args, **kwargs):
    return self._core.Reply(*args, **kwargs)

  def _Spook(self, user: user_pb2.User) -> None:
    """Creates a spooky encounter with user."""
    logging.info('Spooking %s', user)
    self._Reply(user, self._spook_replies.GetAndDownweightItem())

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User, *args,
              **kwargs):
    """Internal method that handles the command.

    *args and **kwargs are the logical arguments returned by the parsers.

    Args:
      channel: Where to send the reply.
      user: User who invoked the command.
      *args: defined by subclass
      **kwargs: defined by subclass

    Returns:
      Optional message(s) to reply to the channel.
    """
    pass


class BasePublicCommand(BaseCommand):
  """Same as BaseCommand, but defaults to no ratelimiter."""

  DEFAULT_PARAMS = params_lib.MergeParams(BaseCommand.DEFAULT_PARAMS,
                                          {'ratelimit': {
                                              'enabled': False
                                          }})


def _AddParserInInit(cls, parser: Callable, has_prefix: bool = False) -> None:
  original_init = cls.__init__

  def NewInit(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    bound_parser = parser
    if has_prefix:
      bound_parser = partial(parser, command_prefix=self.command_prefix)
    self._parsers.append(bound_parser)  # pylint: disable=protected-access

  cls.__init__ = NewInit


def _ParseArgs(match):
  """Returns a list of args and dict of kwargs based on match groups."""
  args = list(match.groups())
  kwargs = match.groupdict()
  for arg in kwargs.values():
    args.remove(arg)
  return args, kwargs


def CommandRegexParser(pattern: Text,
                       flags: int = re.DOTALL,
                       reply_to_public: bool = True,
                       reply_to_private: bool = True,
                       reply_to_system: bool = False):
  """Decorator to add a command-style regex parser to a class.

  A command is case insensitive and takes the form <prefix><regex><whitespace>
  where the prefix is optional when called from a private channel.

  Args:
    pattern: Regular expression to try to match against messages.
    flags: Regular expression flags.
    reply_to_public: Whether to respond to public channels or not.
    reply_to_private: Whether to respond to private channels or not.
    reply_to_system: Whether to respond to system channels or not.

  Returns:
    Decorator that adds parser to class.
  """

  def Parser(channel: channel_pb2.Channel, unused_user: user_pb2.User,
             message: Text,
             command_prefix: Text) -> Tuple[bool, List[Any], Dict[Text, Any]]:
    """Determine if message should be handled.

    Args:
      channel: Where the message originated.
      unused_user: user name
      message: message
      command_prefix: required prefix to any command

    Returns:
      {tuple<boolean, *args, **kwargs} Whether to take message and parsed
        args/kwargs.
    """
    is_public = channel.visibility == channel_pb2.Channel.PUBLIC
    is_private = channel.visibility == channel_pb2.Channel.PRIVATE
    is_system = channel.visibility == channel_pb2.Channel.SYSTEM
    # Cannot precompile since this depends on the channel.
    match = re.match(
        r'(?i)^%s%s%s\s*$' %
        (command_prefix, '' if is_public else '?', pattern),
        message,
        flags=flags)
    if (match and (reply_to_public or not is_public) and
        (reply_to_private or not is_private) and
        (reply_to_system or not is_system)):
      args, kwargs = _ParseArgs(match)
      return True, args, kwargs
    return False, [], {}

  def Decorator(cls):
    _AddParserInInit(cls, Parser, has_prefix=True)
    return cls

  return Decorator


def SystemCommandRegexParser(pattern: Text, flags: int = re.DOTALL):
  """Shorthand for CommandRegexParser with only reply_to_system=True.

  Args:
    pattern: Regular expression to try to match against messages.
    flags: Regular expression flags.

  Returns:
    Decorator that adds parser to class.
  """
  return CommandRegexParser(
      pattern,
      flags=flags,
      reply_to_public=False,
      reply_to_private=False,
      reply_to_system=True)


def RegexParser(pattern):
  """Decorator to add a regex parser to a class.

  Match groups are returned as *args for command.

  Args:
    pattern: {string} Regular expression to try to match against messages.

  Returns:
    {callable} Decorator that adds parser to class.
  """
  regex = re.compile(pattern)

  def Parser(unused_channel: channel_pb2.Channel, unused_user: user_pb2.User,
             message: Text) -> Tuple[bool, List, Dict]:
    """Determine if message should be handled.

    Args:
      message: Message to parse.

    Returns:
      Whether to take message and parsed args/kwargs.
    """
    match = regex.search(message)
    if match:
      args, kwargs = _ParseArgs(match)
      return True, args, kwargs
    return False, [], {}

  def Decorator(cls):
    _AddParserInInit(cls, Parser)
    return cls

  return Decorator


def PublicParser(cls):
  """Parser that handles all public channels."""

  def Parser(channel: channel_pb2.Channel, unused_user: user_pb2.User,
             message: Text) -> Tuple[bool, List[Any], Dict]:
    if channel.visibility == channel_pb2.Channel.PUBLIC:
      return True, [message], {}
    return False, [], {}

  _AddParserInInit(cls, Parser)
  return cls


# === Handler Decorators ===
# Put these decorators on _Handle to filter what is handled regardless of parser
# triggering. Useful for ratelimiting or channel specific behavior.
# TODO: Make class decorators or conditional within command params.
# Left as similar to previous behavior for now.


def PrivateOnly(fn):
  """Decorator to restrict handling to queries."""

  @wraps(fn)
  def Wrapped(fn_self, channel: channel_pb2.Channel, user: user_pb2.User, *args,
              **kwargs):
    if channel.visibility == channel_pb2.Channel.PRIVATE:
      return fn(fn_self, channel, user, *args, **kwargs)

  return Wrapped


def LimitPublicLines(max_lines: int = 6):
  """Decorator factory to restrict lines returned to a public channel.

  When the command's response exceeds max_lines and targets a public
  channel, the response is re-routed to the calling user and a brief message is
  left in the target channel as an indication.

  Args:
    max_lines: Maximum number of lines to send to a public channel.

  Returns:
    Decorator.
  """

  def Decorator(fn):
    """Decorator to restrict lines returned to a public channel."""

    @wraps(fn)
    def Wrapped(fn_self, channel: channel_pb2.Channel, user: user_pb2.User,
                *args, **kwargs):
      msg = fn(fn_self, channel, user, *args, **kwargs)
      if channel.visibility == channel_pb2.Channel.PUBLIC and isinstance(
          msg, list) and len(msg) > max_lines:
        # TODO: Switch to calling _core.interface.SendMessage.
        getattr(fn_self, '_core').Reply(user, msg)
        return u'It\'s long so I sent it privately.'
      return msg

    return Wrapped

  return Decorator


def HumansOnly(message='I\'m sorry %s, I\'m afraid I can\'t do that'):
  """Decorator to restrict handling to humans."""

  def Decorator(fn):
    """Decorator to restrict handling to only humans."""

    @wraps(fn)
    def Wrapped(fn_self, channel: channel_pb2.Channel, user: user_pb2.User,
                *args, **kwargs):
      if user.bot:
        return message % user.display_name
      else:
        return fn(fn_self, channel, user, *args, **kwargs)

    return Wrapped

  return Decorator


def RequireReady(obj_name):
  """Decorator which calls the decorated fn only if obj reports it is ready.

  Args:
    obj_name: The name of the object that must be ready for the call to fn to
      succeed. Note that if the decorated function's owning class (e.g. the
      first positional arg normally called `self`) does not have an object with
      this name, fn will never be called.

  Returns:
    Decorator.
  """

  def Decorator(fn):
    """Actual decorator to require an object is ready."""

    @wraps(fn)
    def Wrapped(fn_self, *args, **kwargs):
      """The wrapped version of fn called in place of fn."""
      obj = fn_self
      for attr in obj_name.split('.'):
        obj = getattr(obj, attr, None)
      if obj and obj.IsReady():
        return fn(fn_self, *args, **kwargs)

      bot_name = getattr(fn_self, '_core').name
      if not obj:
        return '%s is not enabled for %s' % (obj_name, bot_name)
      else:
        return '%s.%s is still loading data, please try again later.' % (
            bot_name, obj_name)

    return Wrapped

  return Decorator


class TextCommand(BaseCommand):
  """Randomly chooses a line from params.choices to say."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      BaseCommand.DEFAULT_PARAMS,
      {'choices': ['Do not forget to override me.']})

  def __init__(self, *args):
    super(TextCommand, self).__init__(*args)
    self._choices = util_lib.WeightedCollection(self._params.choices)

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User):
    if self._choices:
      item = self._choices.GetAndDownweightItem()
      if '{person}' in item:
        item = item.format(item, person=user)
      if item.startswith('/me '):
        item = '%s %s' % (self._core.params.name, item[4:])
      return item
