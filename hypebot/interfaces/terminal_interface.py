# Copyright 2019 The Hypebot Authors. All rights reserved.
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
"""A simple interface that allows a single user to communicate via terminal.

This enables easy testing of hypebot locally without depending on any external
chat applications. The easiest way to utilize this is to pipe the logs to a file
and use stdout/stdin as your "chat application".
  tail -f $PATH_TO_LOG

By default it treats the messages as coming from `terminal-user`, you can
simulate different users by inputing [$USER]$MESSAGE. E.g., [user1]! v

You can also simulate talking a different channel by inputting
[#$CHANNEL]$MESSAGE. E.g., [#testing] ! v. Combining this and the previous nick
override, you can simulate private messages:

[#nick|nick] debug store

Note order of channel and user override does not matter.

If you need to see the full proto Message response, you can set
`return_text_only` to False in the params for the interface.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from hypebot.core import params_lib
from hypebot.interfaces import interface_lib
from hypebot.protos.channel_pb2 import Channel


class TerminalInterface(interface_lib.BaseChatInterface):
  """See file comments."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      interface_lib.BaseChatInterface.DEFAULT_PARAMS, {
          'default_user': 'terminal-user',
          'default_channel': '#hypebot',
          'return_text_only': True,
      })

  def Loop(self):
    while True:
      channel = Channel(
          id=self._params.default_channel,
          visibility=Channel.PUBLIC,
          name=self._params.default_channel)
      nick = self._params.default_user
      message = raw_input('> ').decode('utf-8')
      overrides = self._ExtractOverrides(message)
      if overrides:
        channel, nick, message = overrides
      self._on_message_fn(channel, nick, message)

  def _ExtractOverrides(self, raw_message):
    """Returns nothing, or the overrides parsed for a channel, nick, and msg."""
    message_regex = re.compile(r'^\[(#?\w+)(?:\|(#?\w+))?\]\s*(.+)')
    match = message_regex.match(raw_message)
    if not match:
      return
    nick = self._params.default_user
    channel_name = self._params.default_channel
    visibility = Channel.PUBLIC
    for i in range(1, 3):
      nick_or_channel = match.group(i)
      if not nick_or_channel:
        break
      if nick_or_channel.startswith('#'):
        channel_name = nick_or_channel
      else:
        nick = nick_or_channel
    if nick.lower() == channel_name.strip('#').lower():
      visibility = Channel.PRIVATE
    message = match.group(3)
    return (Channel(id=channel_name, visibility=visibility, name=channel_name),
            nick, message)

  def Who(self, user):
    self._user_tracker.AddHuman(user)

  def WhoAll(self):
    self._user_tracker.AddHuman(self.DEFAULT_USER)

  def SendMessage(self, channel, message):
    if self._params.return_text_only:
      print('%s' % '\n'.join(msg.text for msg in message.messages))
    else:
      print('%s\n%s' % (channel, message))

  def Notice(self, channel, message):
    print('NOTICE\n%s\n%s' % (channel, message))

  def Topic(self, channel, new_topic):
    print('TOPIC\n%s\n%s' % (channel, new_topic))
