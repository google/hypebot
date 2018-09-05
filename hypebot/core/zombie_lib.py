# coding=utf-8
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
"""A library of zombie-related things, used by the !rip/!raise commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from threading import Lock
from typing import Dict, Optional, Text

from hypebot.protos.channel_pb2 import Channel

_ZombieRecord = namedtuple('ZombieRecord', ('fragments', 'name', 'is_private'))


class ZombieManager(object):
  """Manages per-channel zombies and their various states of reanimation."""

  _ZOMBIE_VERBS = ('crawls', 'lumbers', 'shambles', 'lurches', 'careens')

  def __init__(self) -> None:
    self._channel_to_corpse = {}
    self._channel_to_corpse_lock = Lock()

  @property
  def channel_to_corpse(self) -> Dict[str, _ZombieRecord]:
    return self._channel_to_corpse

  @channel_to_corpse.setter
  def channel_to_corpse(self, new_value: Dict[str, _ZombieRecord]) -> None:
    with self._channel_to_corpse_lock:
      self._channel_to_corpse = new_value

  def ChannelHasActiveCorpse(self, channel: Channel) -> bool:
    return (channel.id in self.channel_to_corpse and
            self.channel_to_corpse[channel.id].fragments < 5)

  def GetCorpseForChannel(self, channel: Channel) -> Optional[str]:
    default_zombie = _ZombieRecord(0, None, False)
    return self.channel_to_corpse.get(channel.id, default_zombie).name

  def NewCorpse(self, channel, name) -> None:
    self.channel_to_corpse[channel.id] = _ZombieRecord(
        5, name, channel.visibility == Channel.PRIVATE)

  def AnimateCorpse(self, channel: Channel) -> Text:
    """Outputs a message about the new zombie, or exhaustion of the corpse."""
    zombie = self.channel_to_corpse[channel.id]
    if zombie.fragments > 0:
      self.channel_to_corpse[channel.id] = _ZombieRecord(
          zombie.fragments - 1, zombie.name, zombie.is_private)
      zombie_target = channel.name
      # Special case for when a user is the zombie in their DM to HypeBot.
      if channel.name == zombie.name:
        zombie_target = 'a mirror'
      elif zombie.is_private:
        zombie_target = 'you'
      return u'[¬º-°]¬ %s %s towards %s [¬º-°]¬' % (
          zombie.name, self._ZOMBIE_VERBS[zombie.fragments - 1], zombie_target)
    else:
      del self.channel_to_corpse[channel.id]
      return '%s has run out of matter to reanimate.' % zombie.name

  def RemoveCorpse(self, channel):
    if channel.id in self.channel_to_corpse:
      del self.channel_to_corpse[channel.id]
