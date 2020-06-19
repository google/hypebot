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

from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2
from typing import Text


def _IsProtected(pref):
  return pref.startswith('_')


@command_lib.CommandRegexParser(r'pref(?:erence)?s *(?P<target_user>.*?)')
class PreferencesCommand(command_lib.BaseCommand):
  """See preferences for a user."""

  def _Handle(self,
              unused_channel: channel_pb2.Channel,
              user: user_pb2.User,
              target_user: user_pb2.User) -> hype_types.CommandResponse:
    prefs = self._core.user_prefs.GetAll(target_user)
    if all([_IsProtected(pref) for pref in prefs]):
      return '%s is apathetic.' % target_user.display_name
    return ['%s preferences:' % target_user.display_name] + [
        '* %s: %s' % (pref, value) for pref, value in prefs.items()
        if not _IsProtected(pref)]


@command_lib.CommandRegexParser(r'set-pref(?:erence)? (\S+) *(.*)')
class SetPreferenceCommand(command_lib.BaseCommand):
  """Set preference."""

  def _Handle(self,
              unused_channel: channel_pb2.Channel,
              user: user_pb2.User,
              pref: Text,
              value: Text) -> hype_types.CommandResponse:
    if _IsProtected(pref) or not self._core.user_prefs.IsValid(pref):
      return 'Unrecognized preference.'
    self._core.user_prefs.Set(user, pref, value)
    if not value:
      return 'Removed %s preference' % pref
    return 'Set %s to %s' % (pref, value)
