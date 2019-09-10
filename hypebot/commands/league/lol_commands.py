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
"""League of Legends commands."""

from absl import logging

from hypebot.commands import command_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data.league import messages


@command_lib.CommandRegexParser(r'freelo')
class FreeloCommand(command_lib.TextCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.TextCommand.DEFAULT_PARAMS, {
          'choices': messages.FREELO,
          'main_channel_only': False
      })


@command_lib.CommandRegexParser(r'item (.+)')
class ItemCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, item_name):
    return list(map(util_lib.Dankify,
                    self._core.items.GetItemDescription(item_name)))


@command_lib.CommandRegexParser(r'lore (.+)', reply_to_public=False)
class LoreCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, champ_name):
    return self._core.game.GetChampionLore(champ_name)


@command_lib.CommandRegexParser(r'patch(?:notes)? ?([0-9.]*?)')
class PatchNotesCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, patch):
    base_link = ('http://na.leagueoflegends.com/en/news/game-updates/patch/'
                 'patch-%s-notes')
    if not patch:
      patch = self._core.game.version
    patch = ''.join(patch.split('.'))
    return base_link % patch


@command_lib.CommandRegexParser(r'rune (.+)')
class ReforgedRuneCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, rune_name):
    return self._core.game.GetReforgedRuneMessage(rune_name)


@command_lib.CommandRegexParser(r'set-api-key ([\w]+)', reply_to_public=False)
class SetApiKeyCommand(command_lib.BaseCommand):
  """Set rito api key."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, api_key):
    logging.info('Setting API key to %s', api_key)
    self._core.rito.api_key = api_key
    self._core.store.SetValue('api_key', 'key', self._core.rito.api_key)
    self._core.ReloadData()


@command_lib.CommandRegexParser(r'(?:skill )?([qwerpk]|ult|passive) (.+)')
class SkillCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, skill_name, champ_name):
    skill_name = skill_name.lower()

    if skill_name in ['p', 'passive']:
      return self._core.game.GetChampPassiveMessage(champ_name)
    else:
      if skill_name == 'ult':
        skill_name = 'r'

      return self._core.game.GetChampSkillMessage(champ_name, skill_name)


@command_lib.CommandRegexParser(r'stats (.+)')
class StatsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, champ_name):
    return self._core.game.GetChampStatsText(champ_name)


@command_lib.CommandRegexParser(r'statsat (-?[0-9]+) +(.+)')
class StatsAtCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, level, champ_name):
    level = util_lib.SafeCast(level, int, 0)
    return self._core.game.GetChampStatsAtLevelText(champ_name, level)
