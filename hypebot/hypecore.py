# Copyright 2018 The Hypebot Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The core of all things hype."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from threading import Lock
import time

from absl import logging
from concurrent import futures

from hypebot import hype_types
from hypebot.core import async_lib
from hypebot.core import schedule_lib
from hypebot.core import util_lib
from hypebot.core import zombie_lib
from hypebot.interfaces import interface_lib
from hypebot.news import news_factory
from hypebot.plugins import coin_lib
from hypebot.plugins import deploy_lib
from hypebot.plugins import hypestack_lib
from hypebot.plugins import inventory_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2
from hypebot.proxies import proxy_factory
from hypebot.stocks import stock_factory
from hypebot.storage import storage_factory
from hypebot.storage import storage_lib
from typing import Any, Callable, Dict, Optional, Text


class RequestTracker(object):
  """Tracks user requests that require confirmation."""

  _REQUEST_TIMEOUT_SEC = 60

  def __init__(self, reply_fn: Callable) -> None:
    self._reply_fn = reply_fn
    self._pending_requests = {}  # type: Dict[Text, Dict]
    self._pending_requests_lock = Lock()

  def HasPendingRequest(self, user: hype_types.User) -> bool:
    with self._pending_requests_lock:
      return user.user_id in self._pending_requests

  def RequestConfirmation(self,
                          user: hype_types.User,
                          summary: Text,
                          request_details: Dict,
                          action_fn: Callable,
                          parse_fn: Optional[Callable] = None) -> None:
    """Create a user request that must be confirmed before action is taken.

    This is a very generic flow useful for any command/bot service that would
    like to double-check with the user before some action is taken (e.g. filing
    an issue). There can be only a single pending request per user at a time.
    When there is an outstanding request for user, all other calls to this
    function will fail until either the user confirms or denies their pending
    request, or _REQUEST_TIMEOUT_SEC has elapsed.

    Args:
      user: The user making the request.
      summary: Summary of the request, used in confirmation message.
      request_details: Information passed to action_fn upon confirmation.
      action_fn: Function called if user confirms this request.
      parse_fn: Function used to parse a user's response.

    Returns:
      None
    """
    now = time.time()
    with self._pending_requests_lock:
      previous_request = self._pending_requests.get(user.user_id, None)
      if previous_request:
        if now - previous_request['timestamp'] < self._REQUEST_TIMEOUT_SEC:
          self._reply_fn(user,
                         'Confirm prior request before submitting another.')
          return
        del self._pending_requests[user.user_id]

      request_details['timestamp'] = now
      request_details['action'] = action_fn
      if not parse_fn:
        parse_fn = lambda x: x.lower().startswith('y')
      request_details['parse'] = parse_fn
      self._pending_requests[user.user_id] = request_details
      self._reply_fn(user, 'Confirm %s?' % summary)

  def ResolveRequest(self, user: hype_types.User, user_msg: Text) -> None:
    """Resolves a pending request, taking the linked action if confirmed."""
    now = time.time()
    with self._pending_requests_lock:
      request_details = self._pending_requests.get(user.user_id)
      if not request_details:
        return
      if not request_details['parse'](user_msg):
        self._reply_fn(user, 'Cancelling request.')
      elif now - request_details['timestamp'] >= self._REQUEST_TIMEOUT_SEC:
        self._reply_fn(user, 'You took too long to confirm, try again.')
      else:
        self._reply_fn(
            user, request_details.get('action_text', 'Confirmation accepted.'))
        request_details['action'](user, request_details)
      del self._pending_requests[user]


class OutputUtil(object):
  """Allows plugins to send output without a reference to Core."""

  def __init__(self, output_fn: Callable) -> None:
    self._output_fn = output_fn

  def LogAndOutput(self, log_level: int, channel: channel_pb2.Channel,
                   message: hype_types.CommandResponse) -> None:
    """Logs message at log_level, then sends it to channel via Output."""
    logging.log(log_level, message)
    self.Output(channel, message)

  def Output(self, channel: channel_pb2.Channel,
             message: hype_types.CommandResponse) -> None:
    """Outputs a message to channel."""
    self._output_fn(channel, message)


class UserPreferences(object):
  """Manages users preferences and stores them across bot reloads."""

  # Master list of useable preferences. Dict of pref => default value.
  _PREFS = {
      'location': 'MTV',
      'temperature_unit': 'F',
      'stocks': 'GOOG,GOOGL',
      # Comma separated list of your summoner names. First is considered main.
      'lol_summoner': None,
      'lol_region': 'NA',
      '_dynamite_dm': None,
      # Maps 'user/####' to '$ldap'.
      '_dynamite_ldap': None,
  }
  _SUBKEY = 'preferences'

  def __init__(self, store: storage_lib.HypeStore):
    self._store = store

  def IsValid(self, pref: Text) -> bool:
    """Returns if a preference is recognized.

    Args:
      pref: The name of the preference.

    Returns:
      True if the preference is recognized.
    """
    return pref in self._PREFS

  def Get(self, user: user_pb2.User, pref: Text) -> Text:
    """Get user's preference value.

    Args:
      user: The user for which to look up the preference.
      pref: The preference of the user.

    Returns:
      The user's preference or the default value for the preferenece. Returns
      None if the preference is invalid.
    """
    if not self.IsValid(pref):
      logging.warning('Tried to access an invalid pref: %s', pref)
      return None

    user_prefs = self.GetAll(user)
    return user_prefs.get(pref, self._PREFS[pref])

  def Set(self, user: user_pb2.User, pref: Text, value: Text) -> None:
    """Set user's preference to value.

    If preference is invalid, nothing happens.

    Args:
      user: The user.
      pref: Name of preference.
      value: Value to set preference.
    """
    if not self.IsValid(pref):
      return
    self._store.RunInTransaction(self._Set, user, pref, value)

  def _Set(self, user: user_pb2.User, pref: Text, value: Text,
           tx: storage_lib.HypeTransaction) -> None:
    """See Set(...) for details."""
    user_prefs = self._store.GetJsonValue(user.user_id, self._SUBKEY, tx) or {}
    if not value:
      del user_prefs[pref]
    else:
      user_prefs[pref] = value
    self._store.SetJsonValue(user.user_id, self._SUBKEY, user_prefs, tx)

  def GetAll(self, user: user_pb2.User) -> Dict[Text, Text]:
    return self._store.GetJsonValue(user.user_id, self._SUBKEY) or {}


class Core(object):
  """The core of hypebot.

  Any state or service that is needed by more than one command.
  """

  def __init__(
      self,
      params: Any,  # HypeParams
      interface: interface_lib.BaseChatInterface) -> None:
    """Constructs core of hypebot.

    Args:
      params: Bot parameters.
      interface: This will always be the original interface that the bot was
        created with, and never the CaptureInterface during nested calls. For
        this reason, you should only call Join/Part and potentially Notice/Topic
        on this interface.  Don't call SendMessage or else it can send messages
        never intended for human consumption.
    """
    self.params = params
    self.name = self.params.name
    self.interface = interface
    self.output_util = OutputUtil(self.Reply)

    self.store = storage_factory.CreateFromParams(self.params.storage)
    cached_type = self.params.storage.get('cached_type')
    if cached_type:
      self.cached_store = storage_factory.Create(
          cached_type, self.params.storage.get(self.params.storage.type))
    else:
      logging.info('No cached_type found for storage, using default store.')
      self.cached_store = self.store

    self.user_tracker = util_lib.UserTracker()
    self.user_prefs = UserPreferences(self.cached_store)
    self.timezone = self.params.time_zone
    self.scheduler = schedule_lib.HypeScheduler(self.timezone)
    self.executor = futures.ThreadPoolExecutor(max_workers=8)
    self.runner = async_lib.AsyncRunner(self.executor)
    self.inventory = inventory_lib.InventoryManager(self.store)
    self.proxy = proxy_factory.Create(self.params.proxy.type, self.store)
    self.zombie_manager = zombie_lib.ZombieManager()
    self.request_tracker = RequestTracker(self.Reply)
    self.bank = coin_lib.Bank(self.store, self.name.lower())
    self.bets = coin_lib.Bookie(self.store, self.bank, self.inventory)
    self.stocks = stock_factory.CreateFromParams(self.params.stocks, self.proxy)
    self.deployment_manager = deploy_lib.DeploymentManager(
        self.name.lower(), self.bank, self.output_util, self.executor)
    self.hypestacks = hypestack_lib.HypeStacks(self.store, self.bank,
                                               self.Reply)
    self.news = news_factory.CreateFromParams(self.params.news, self.proxy)
    self.betting_games = []
    self.last_command = None
    self.default_channel = self.params.default_channel

  def Reply(self,
            channel: hype_types.Target,
            msg: hype_types.CommandResponse,
            default_channel: Optional[channel_pb2.Channel] = None,
            limit_lines: bool = False,
            max_public_lines: int = 6,
            user: Optional[hype_types.User] = None,
            log: bool = False,
            log_level: int = logging.INFO) -> None:
    """Sends a message to the channel.

    Leaving Reply on the HypeCore allows replacing the interface to process
    nested commands. However, some change will be needed in order to actually
    create an OutputUtil for HBDS without a HypeCore.

    Args:
      channel: Who/where to send the message.
      msg: The message to send.
      default_channel: Who/where to send the message if no channel is specified.
      limit_lines: Whether to limit lines or not.
      max_public_lines: Maximum number of lines to send to a public channel.
      user: If specified, where to send the message if its too long.
      log: Whether to also log the message.
      log_level: How important the log is.
    """
    if not msg:
      return

    if log:
      text_msg = msg
      logging.log(log_level, text_msg, exc_info=log_level == logging.ERROR)

    channel = channel or default_channel
    if not channel:
      logging.info('Attempted to send message with no channel: %s', msg)
      return
    # Support legacy Reply to users as a string.
    if not isinstance(channel, channel_pb2.Channel):
      self.interface.SendDirectMessage(channel, util_lib.MakeMessage(msg))
      return

    if (limit_lines and channel.visibility == channel_pb2.Channel.PUBLIC and
        isinstance(msg, list) and len(msg) > max_public_lines):
      if user:
        self.interface.SendMessage(
            channel, util_lib.MakeMessage('It\'s long so I sent it privately.'))
        self.interface.SendDirectMessage(user, util_lib.MakeMessage(msg))
      else:
        # If there is no user, just truncate and send to channel.
        self.interface.SendMessage(
            channel, util_lib.MakeMessage(msg[:max_public_lines] + ['...']))
    else:
      self.interface.SendMessage(channel, util_lib.MakeMessage(msg))

  def PublishMessage(self,
                     topic: Text,
                     msg: hype_types.CommandResponse,
                     notice: bool = False) -> None:
    """Sends a message to the channels subscribed to a topic.

    Args:
      topic: Name of the topic on which to publish the message.
      msg: The message to send.
      notice: If true, use interface.Notice instead of interface.SendMessage.
    """
    if not msg:
      return
    if not topic:
      logging.warning('Attempted to publish message with no topic: %s', msg)
      return
    channels = self.params.subscriptions.get(topic, [])
    if not channels:
      logging.info('No subscriptions for topic %s, dropping: %s', topic, msg)
      return
    message = util_lib.MakeMessage(msg)
    for channel in channels:
      channel = channel_pb2.Channel(
          visibility=channel_pb2.Channel.PUBLIC, **channel)
      if notice:
        self.interface.Notice(channel, message)
      else:
        self.interface.SendMessage(channel, message)

  def ReloadData(self) -> bool:
    """Asynchronous reload of all data on core.

    Searches for any attribute that has a ReloadData function and calls it.

    Returns:
      Whether reload triggered or not since it was still running.
    """
    if not self.runner.IsIdle():
      logging.info('Runner not idle, can not trigger reload.')
      return False

    self.proxy.FlushCache()
    for obj in self.__dict__.values():
      if hasattr(obj, 'ReloadData'):
        logging.info('Triggering reload for: %s', obj.__class__.__name__)
        self.runner.RunAsync(obj.ReloadData)
    return True
