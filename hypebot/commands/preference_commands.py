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
"""Commands for setting and viewing user-specific preferences."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial

from hypebot import hypecore
from hypebot import types
from hypebot.commands import command_lib

from typing import Text


def _IsProtected(pref):
  return pref.startswith('_')


@command_lib.CommandRegexParser(r'pref(?:erence)?s *(.*?)')
class PreferencesCommand(command_lib.BaseCommand):
  """See preferences for a user."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              unused_channel: types.Channel,
              user: Text,
              target_user: Text) -> hypecore.MessageType:
    target_user = target_user or user
    if target_user == 'me':
      self._core.last_command = partial(self._Handle, target_user=target_user)
      target_user = user
    prefs = self._core.user_prefs.GetAll(target_user)
    if all([_IsProtected(pref) for pref in prefs]):
      return '%s is apathetic.' % target_user
    return ['%s preferences:' % target_user] + [
        '* %s: %s' % (pref, value) for pref, value in prefs.items()
        if not _IsProtected(pref)]


@command_lib.CommandRegexParser(r'set-pref(?:erence)? (\S+) *(.*)')
class SetPreferenceCommand(command_lib.BaseCommand):
  """Set preference."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              unused_channel: types.Channel,
              user: Text,
              pref: Text,
              value: Text) -> hypecore.MessageType:
    if _IsProtected(pref) or not self._core.user_prefs.IsValid(pref):
      return 'Unrecognized preference.'
    self._core.user_prefs.Set(user, pref, value)
    if not value:
      return 'Removed %s preference' % pref
    return 'Set %s to %s' % (pref, value)

