# Lint as: python3
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

Any channel name starting with '#sys' will have its visibility set to SYSTEM
(see channel.proto).

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
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2

_COLOR_PATTERN = re.compile(
    r'\x03(?P<fg>\d\d)(?:|,(?P<bg>\d\d))(?P<txt>.*?)\x0f')
_IRC_TO_TERM_COLORS = {
    '00': '37;1',
    '01': '30',
    '02': '34',
    '03': '32',
    '04': '31;1',
    '05': '31',
    '06': '35',
    '07': '33',
    '08': '33;1',
    '09': '32;1',
    '10': '36',
    '11': '36;1',
    '12': '34;1',
    '13': '35;1',
    '14': '30;1',
    '15': '37',
}


class TerminalInterface(interface_lib.BaseChatInterface):
  """See file comments."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      interface_lib.BaseChatInterface.DEFAULT_PARAMS, {
          'default_username': 'terminal-user',
          'default_channel': '#hypebot',
          'return_text_only': True,
      })

  def Loop(self):
    while True:
      channel = self._params.default_channel
      user = user_pb2.User(
          user_id=self._params.default_username,
          display_name=self._params.default_username)
      message = input('> ')
      overrides = self._ExtractOverrides(message)
      if overrides:
        channel, user, message = overrides
      self._on_message_fn(channel, user, message)

  def _ExtractOverrides(self, raw_message):
    """Returns nothing, or the overrides parsed for a channel, user, and msg."""
    message_regex = re.compile(r'^\[(#?\w+)(?:\|(#?\w+))?\]\s*(.+)')
    match = message_regex.match(raw_message)
    if not match:
      return
    username = self._params.default_username
    channel_name = self._params.default_channel.name
    visibility = channel_pb2.Channel.PUBLIC
    for i in range(1, 3):
      user_or_channel = match.group(i)
      if not user_or_channel:
        break
      if user_or_channel.startswith('#'):
        channel_name = user_or_channel
        if channel_name.startswith('#sys'):
          visibility = channel_pb2.Channel.SYSTEM
      else:
        username = user_or_channel
    if username.lower() == channel_name.strip('#').lower():
      visibility = channel_pb2.Channel.PRIVATE
    message = match.group(3)
    return (channel_pb2.Channel(
        id=channel_name, visibility=visibility, name=channel_name),
            user_pb2.User(
                user_id=username,
                display_name=username,
                bot=username.endswith('bot')), message)

  def Who(self, user):
    self._user_tracker.AddHuman(user)

  def WhoAll(self):
    self._user_tracker.AddHuman(self._params.default_user)

  def SendMessage(self, channel, message):
    if self._params.return_text_only:
      lines = self._TranslateColors(message)
      print('\n'.join(lines))
    else:
      print('%s\n%s' % (channel, message))

  def SendDirectMessage(self, user, message):
    if self._params.return_text_only:
      lines = self._TranslateColors(message)
      print('\n'.join([f'{user.display_name}: {line}' for line in lines]))
    else:
      print('%s\n%s' % (user, message))

  def Notice(self, channel, message):
    print('NOTICE\n%s\n%s' % (channel, message))

  def Topic(self, channel, new_topic):
    print('TOPIC\n%s\n%s' % (channel, new_topic))

  def _TranslateColors(self, message):
    lines = []
    for msg in message.messages:
      for line in msg.text:
        pos = 0
        colored_line = ''
        while True:
          match = _COLOR_PATTERN.search(line, pos=pos)
          if not match:
            break
          colored_line += line[pos:match.start()]
          colored_line += '\033[%sm%s\033[0m' % (
              _IRC_TO_TERM_COLORS[match.group('fg')], match.group('txt'))
          pos = match.end()
        lines.append(colored_line + line[pos:])
    return lines
