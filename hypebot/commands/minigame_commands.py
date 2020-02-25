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
"""Commands that play minigames usually in specific channels."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import functools

from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import params_lib
from hypebot.plugins import hypejack_lib
from hypebot.protos.channel_pb2 import Channel

from typing import Text


@command_lib.PublicParser
class HypeJackCommand(command_lib.BasePublicCommand):
  """Redirects input to the HypeJack game."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          'ratelimit': {
              'enabled': False,
          },
          'main_channel_only': False,
          # Channels where hypejack may be played.
          'channels': [],
      })

  def __init__(self, *args, **kwargs):
    super(HypeJackCommand, self).__init__(*args, **kwargs)
    # Maps channel ids to their games.
    self._games = {}  # type: Dict[Text, hypejack_lib.Game]

    for channel in self._params.channels:
      self._core.interface.Join(channel)
      self._games[channel.id] = hypejack_lib.Game(
          channel, self._core,
          functools.partial(self._Reply, default_channel=channel))

  def _Handle(self, channel: Channel, user: Text,
              message: Text) -> hype_types.CommandResponse:
    if channel.id in self._games:
      self._games[channel.id].HandleMessage(user, message)
