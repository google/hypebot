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
"""Commands that control the chat application interface."""

from hypebot.commands import command_lib
from hypebot.protos.channel_pb2 import Channel


@command_lib.CommandRegexParser(r'join (#[^ ]+)')
class JoinCommand(command_lib.BaseCommand):

  @command_lib.PrivateOnly
  def _Handle(self, channel, user, channel_name):
    self._core.interface.Join(
        Channel(id=channel_name, visibility=Channel.PUBLIC, name=channel_name))


@command_lib.CommandRegexParser(r'(?:part|leave) (#[^ ]+)')
class LeaveCommand(command_lib.BaseCommand):

  @command_lib.PrivateOnly
  def _Handle(self, channel, user, channel_name):
    self._core.interface.Leave(
        Channel(id=channel_name, visibility=Channel.PUBLIC, name=channel_name))
