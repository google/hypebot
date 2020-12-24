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
"""Library for interfaces."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc

from absl import logging
from hypebot import hype_types
from hypebot.core import params_lib
from hypebot.protos import user_pb2
from six import with_metaclass
from typing import Optional, Text


class BaseChatInterface(with_metaclass(abc.ABCMeta)):
  """The interface base class.

  An `interface` allows hypebot to communicate with a chat application (e.g.,
  IRC, Discord, FireChat). This is an application-agnostic way of sending and
  receiving messages and information about users.
  """

  DEFAULT_PARAMS = params_lib.HypeParams({
      # Display name used when chatting.
      'name': 'chatbot',
  })

  def __init__(self, params):
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    self._params.Lock()
    self._channels = set()

  def RegisterHandlers(self, on_message_fn, user_tracker, user_prefs):
    """Register handlers from the bot onto the interface.

    Allows the interface to communicate asynchronously to the bot when messages
    or user information comes.

    Args:
      on_message_fn: {callable(Channel, User, message)} Function that will be
        called in response to an incoming message.
      user_tracker: {UserTracker} Where to store results of Who/WhoAll requests.
      user_prefs: {SyncedDict} Persistent user preferences.
    """
    self._channels = set()
    self._on_message_fn = on_message_fn
    self._user_tracker = user_tracker
    self._user_prefs = user_prefs

  def Join(self, channel: hype_types.Channel):
    """Bring the power of hype to the desired channel.

    The base class only maintains a list of active channels. Subclasses are
    responsible for actually joining the channel.

    Args:
      channel: {Channel} channel name to join.
    """
    self._channels.add(channel.id)

  def Leave(self, channel: hype_types.Channel):
    """We do not condone this behavior.

    The base class only maintains a list of active channels. Subclasses are
    responsible for actually leaving the channel.

    Args:
      channel: {Channel} channel to leave.
    """
    if channel.id in self._channels:
      self._channels.remove(channel.id)
    else:
      logging.warning('Tried to leave channel that I never joined: %s', channel)

  @abc.abstractmethod
  def Loop(self):
    """Listen to messages from the chat application indefinitely.

    Loop steals the current thread.
    """
    raise NotImplementedError()

  def FindUser(self, query: Text) -> Optional[user_pb2.User]:
    """Find user with the given name or user_id.

    Attempts to find a user proto for the given query. Some interfaces provide
    an annotation syntax to allow specifying a specific user. Since these aren't
    universal, the Interface will convert it into the user_id for the command.
    However, we would also like to support referring to a user by their display
    name directly. If specifying the display name, it is possible for it not to
    be unique.

    Args:
      query: Either user_id or display name of user.

    Returns:
      The full user proto of the desired user or None if no user exists or the
      query does not resolve to a unique user.
    """
    users = self._user_tracker.AllUsers()
    matches = []
    for user in users:
      if user.user_id == query:
        return user
      if user.display_name.lower() == query.lower():
        matches.append(user)
    if len(matches) == 1:
      return matches[0]
    return None

  @abc.abstractmethod
  def WhoAll(self):
    """Request that all users be added to the user tracker."""
    raise NotImplementedError()

  # TODO: Eliminate Optional from the message type.
  @abc.abstractmethod
  def SendMessage(self, channel: hype_types.Channel,
                  message: Optional[hype_types.Message]):
    """Send a message to the given channel.

    Args:
      channel: channel to receive message.
      message: message to send to the channel.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def SendDirectMessage(self, user: user_pb2.User, message: hype_types.Message):
    raise NotImplementedError()

  # TODO: Eliminate Optional from the message type.
  @abc.abstractmethod
  def Notice(self, channel: hype_types.Channel, message: hype_types.Message):
    """Send a notice to the channel.

    Some applications (IRC) support a different type of message to a channel.
    This is used to broadcast a message not in response to a user input. E.g.,
    match start time or scheduled bet resolution.

    Args:
      channel: channel to send notice.
      message: notice to send to the channel.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def Topic(self, channel: hype_types.Channel, new_topic: Text):
    """Changes the "topic" of channel to new_topic.

    Args:
      channel: channel to change the topic of.
      new_topic: new topic to set.
    """
    raise NotImplementedError()

