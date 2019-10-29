# coding=utf-8
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
"""game_lib fetches in-game champion data from the Riot API.

usage:
  # setup
  import game_lib
  s = game_lib.GameLib(api_key)

  # returns a string
  s.GetChampDisplayName(champ_name)

  # all return an array of strings
  s.GetChampStatsText(champ_name)
  s.GetChampStatsAtLevelText(champ_name, level)
  s.GetChampSkillMessage(champ_name, skill_name) # skill_name is Q, W, E, or R
  s.GetChampPassiveMessage(champ_name)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random
import re
from threading import Lock
from typing import List, Text

from hypebot.core import name_complete_lib
from hypebot.core import util_lib
from hypebot.data.league import client_vars
from hypebot.data.league import nicknames
from hypebot.protos import message_pb2


BASE_DDRAGON_CDN_URL = 'http://ddragon.leagueoflegends.com/cdn/'


class GameLib(object):
  """Class for fetching in-game data from the Riot API."""

  # regex for {{ attr }}
  _FILLIN_PATTERN = re.compile(r'(\{\{[\w ]*\}\})')

  _SCALING_MAP = {
      'spelldamage': 'AP',
      'armor': 'armor',
      'health': 'max health',
      'bonushealth': 'bonus health',
      'attackdamage': 'total AD',
      'bonusattackdamage': 'bonus AD',
  }

  _MISSING_VARS_MEMES = [
      'just a few',
      'more than enough',
      '420',
      'π',
      'four tens',
  ]

  _champion_id_to_name = {}
  _champion_id_to_name_lock = Lock()

  def __init__(self, rito):
    self._rito = rito
    self._champ_name_complete = None
    self._champ_name_to_champ_map = {}
    self._canonical_champ_names = []
    self._reforged_runes_name_complete = None
    self._reforged_rune_slot = {}
    self.ReloadData()

  @property
  def champion_id_to_name(self):
    return self._champion_id_to_name

  @champion_id_to_name.setter
  def champion_id_to_name(self, value):
    with self._champion_id_to_name_lock:
      self._champion_id_to_name = value

  def ReloadData(self):
    """Reload LoL game-related data into memory from the Rito API."""
    self._LoadChampions()
    self._LoadReforgedRunes()

  def _LoadChampions(self):
    """Logic for loading champions. Stored in-memory."""
    champions_response = self._rito.ListChampions()
    if not champions_response:
      return
    champ_data = champions_response.data
    new_champion_id_to_name = {}

    for _, champ in champ_data.items():
      champ_name = util_lib.CanonicalizeName(champ.key)
      # wtf rito please
      if champ_name == 'monkeyking':
        champ_name = 'wukong'

      self._champ_name_to_champ_map[champ_name] = champ
      self._canonical_champ_names.append(champ_name)
      new_champion_id_to_name[str(champ.id)] = champ.name

    self._canonical_champ_names.sort()
    self._champ_name_complete = name_complete_lib.NameComplete(
        nicknames.CHAMP_NICKNAME_MAP,
        self._champ_name_to_champ_map, (c.name for c in champ_data.values()),
        dankify=True)
    self.champion_id_to_name = new_champion_id_to_name
    self._version = champions_response.version
    self.version = '.'.join(self._version.rsplit('.', 1)[0])

  def _LoadReforgedRunes(self):
    """Logic for loading reforged runes. Stored in-memory."""

    runes_response = self._rito.ListReforgedRunePaths()
    if not runes_response:
      return

    canonical_name_map = {}
    new_reforged_rune_slot = {}
    for path in runes_response.paths:
      for i, slot in enumerate(path.slots):
        for rune in slot.runes:
          rune.rune_path_name = path.name
          canonical_name = util_lib.CanonicalizeName(rune.key)
          canonical_name_map[canonical_name] = rune
          new_reforged_rune_slot[rune.key] = i

    self._reforged_runes_name_complete = name_complete_lib.NameComplete(
        {},
        canonical_name_map,
        [rune.name for _, rune in canonical_name_map.items()],
        dankify=True)
    self._reforged_rune_slot = new_reforged_rune_slot

  def GetAllChampNames(self):
    """Returns a list of all champ names."""
    return list(self._canonical_champ_names)

  def GetChampDisplayName(self, champ_name):
    """Gets the champ display name from an unsanitized version of the name."""
    champ = self._ProcessChampRegexs(champ_name)
    if champ:
      return champ.name
    return None

  def ChampFromName(self, champ_name):
    """Put back in because too lazy to refactor trivia_lib."""
    return self._ProcessChampRegexs(champ_name)

  def GetChampId(self, champ_name):
    """Given a champ name, finds the ID of that champion. None if not found."""
    champ = self._ProcessChampRegexs(champ_name)
    if champ:
      return champ.id
    return None

  def GetChampNameFromId(self, champ_id):
    """Given a champ_id, finds the name of that champ. None if not found."""
    for champ, data in self._champ_name_to_champ_map.items():
      if data.id == champ_id:
        return self.GetChampDisplayName(champ)
    return

  def GetChampStatsText(self, champ_name):
    """Gets stats for a given champion."""
    champ = self._ProcessChampRegexs(champ_name)
    if champ:
      return self._ComputeChampStatsText(champ)
    else:
      return ['Champ "{}" not found.'.format(champ_name)]

  def _ComputeChampStatsText(self, champ):
    """Computes stats for a given champion."""
    stats = champ.stats
    stats_strs = [champ.name]

    stats_strs.append('HP: {stats.hp} (+{stats.hpperlevel})'
                      .format(stats=stats))

    stats_strs.append('HP Regen: {stats.hpregen} (+{stats.hpregenperlevel})'
                      .format(stats=stats))

    if stats.mp > 0:
      stats_strs.append('Mana: {stats.mp} (+{stats.mpperlevel})'
                        .format(stats=stats))

    if stats.mpregen > 0:
      stats_strs.append(
          'Mana Regen: {stats.mpregen} (+{stats.mpregenperlevel})'
          .format(stats=stats))

    stats_strs.append('Attack Range: {}'.format(int(stats.attackrange)))

    stats_strs.append(
        'AD: {stats.attackdamage} (+{stats.attackdamageperlevel})'
        .format(stats=stats))

    stats_strs.append('AS: {:.3f} (+{:.2f}%)'.format(
        self._BaseAttackSpeedFromOffset(stats.attackspeedoffset),
        stats.attackspeedperlevel))

    stats_strs.append('Armor: {stats.armor} (+{stats.armorperlevel})'
                      .format(stats=stats))

    stats_strs.append('MR: {stats.spellblock} (+{stats.spellblockperlevel})'
                      .format(stats=stats))

    stats_strs.append('MS: {}'.format(int(stats.movespeed)))

    return ['; '.join(stats_strs)]

  def GetChampStatsAtLevelText(self, champ_name, level):
    """Gets stats for a given champion at a given level."""
    champ = self._ProcessChampRegexs(champ_name)
    if champ:
      return self._ComputeChampStatsAtLevelText(champ, level)
    else:
      return ['Champ "{}" not found.'.format(champ_name)]

  def _ComputeChampStatsAtLevelText(self, champ, level):
    """Computes stats for a given champion at a given level."""
    stats = champ.stats
    stats_strs = ['{} @ L{}'.format(champ.name, level)]

    stats_strs.append('HP: {}'.format(
        self._GetStatAtLevel(stats.hp, stats.hpperlevel, level)))

    stats_strs.append('HP Regen: {}'.format(
        self._GetStatAtLevel(stats.hpregen, stats.hpregenperlevel, level)))

    if stats.mp > 0:
      stats_strs.append('Mana: {}'.format(
          self._GetStatAtLevel(stats.mp, stats.mpperlevel, level)))

    if stats.mpregen > 0:
      stats_strs.append('Mana Regen: {}'.format(
          self._GetStatAtLevel(stats.mpregen, stats.mpregenperlevel, level)))

    stats_strs.append('Attack Range: {}'.format(int(stats.attackrange)))

    stats_strs.append('AD: {}'.format(
        self._GetStatAtLevel(stats.attackdamage, stats.attackdamageperlevel,
                             level)))

    # AS is really weird...
    base_as = self._BaseAttackSpeedFromOffset(stats.attackspeedoffset)
    curr_as = base_as * (1 + level * stats.attackspeedperlevel / 100.0)
    stats_strs.append('AS: ~{:.3f}'.format(curr_as))

    stats_strs.append('Armor: {}'.format(
        self._GetStatAtLevel(stats.armor, stats.armorperlevel, level)))

    stats_strs.append('MR: {}'.format(
        self._GetStatAtLevel(stats.spellblock, stats.spellblockperlevel,
                             level)))

    stats_strs.append('MS: {}'.format(int(stats.movespeed)))

    return ['; '.join(stats_strs)]

  def _GetStatAtLevel(self, base, growth, level):
    """Computes a given stat at a given level based on growth."""
    return base + growth * (7 * (level * level - 1) + 267 * (level - 1)) / 400.0

  def _BaseAttackSpeedFromOffset(self, offset):
    """Computes attack speed given an offset."""
    return 0.625 / (1 + offset)

  def GetChampPassiveMessage(self, champ_name):
    """Gets the passive for the given champion."""
    champ = self._ProcessChampRegexs(champ_name)

    if champ:
      return self._ComputeChampPassiveCard(champ)
    else:
      return 'Champ "{}" not found.'.format(champ_name)

  def _ComputeChampPassiveCard(self, champ):
    passive = champ.passive

    # Make passives more dank.
    tooltip = util_lib.Dankify(self._Sanitize(passive.description))

    return message_pb2.Card(
        header={
            'title': util_lib.Dankify(passive.name),
            'subtitle': '{} Passive'.format(champ.name),
            'image': {
                'url': self.GetImageUrl('passive', passive.image.full),
            },
        },
        fields=[{
            'text': tooltip
        }])

  def GetChampSkillMessage(self, champ_name, skill_name):
    """Gets the given skill for a given champion.

    skill_name should be one of 'q', 'w', 'e', 'r', 'k'.
    """
    champ = self._ProcessChampRegexs(champ_name)

    skill_name = skill_name.upper()

    # !k gp shall output the same as !w gp
    if skill_name == 'K' and champ.name.lower() == 'gangplank':
      skill_name = 'W'

    if champ:
      return self._ComputeChampSkillCard(champ, skill_name)
    else:
      return 'Champ "{}" not found.'.format(champ_name)

  def GetChampSkill(self, champ, skill_name):
    """Returns the corresponding champ skill object."""
    skill_name = skill_name.upper()

    SKILL_MAP = {'Q': 0, 'W': 1, 'E': 2, 'R': 3}
    skill_idx = SKILL_MAP.get(skill_name)

    if skill_idx is None:
      return None

    skill = champ.spells[skill_idx]
    return skill

  def _ComputeChampSkillCard(self, champ, skill_button):
    """Computes given skill for a given champion."""
    skill_button = skill_button.upper()

    skill = self.GetChampSkill(champ, skill_button)
    if skill is None:
      return 'Invalid skill name.'

    # Make skills more dank.
    skill_name = util_lib.Dankify(skill.name)
    tooltip = util_lib.Dankify(self._Sanitize(skill.tooltip))

    skill_title = '{} {}: {}'.format(champ.name, skill_button, skill_name)
    card = message_pb2.Card(
        header={
            'title': skill_title,
            'image': {
                'url': self.GetImageUrl('spell', skill.image.full),
            },
        })
    skill_strs = []
    skill_strs.append(skill_title)

    skill_range = skill.range_burn
    if skill_range != 'self':
      skill_strs.append('Range: {}'.format(skill_range))
      card.fields.add(title='Range', text='{}'.format(skill_range))

    resource = skill.resource
    if resource:
      cost = self._FillinSkillDescription(resource, skill)
      skill_strs.append('Cost: {}'.format(cost))
      card.fields.add(title='Cost', text=cost)

    skill_strs.append('CD: {}'.format(skill.cooldown_burn))
    card.fields.add(title='Cooldown', text='{}'.format(skill.cooldown_burn))

    skill_text = self._FillinSkillDescription(tooltip, skill)
    card.fields.add(text=skill_text)

    skill_info = [u'; '.join(skill_strs)]
    # this description is sometimes too long.
    # split it into multiple lines if necessary.
    skill_info += self._CleanChampionWrap(skill_text)
    return message_pb2.Message(text=skill_info, card=card)

  def _FillinSkillDescription(self, desc, skill):
    """Fills in {{ attr }} parts of the given description."""

    # tokens alternates plaintext, {{}}, plaintext, {{}}, etc.
    tokens = self._FILLIN_PATTERN.split(desc)

    # put all vars in a map
    vars_map = {}
    for v in skill.vars:
      key = v.key
      vars_map[key] = v

    # replace {{ }} tokens (odd indices) in place
    for i in range(1, len(tokens), 2):
      try:
        fillin = self._ParseFillin(tokens[i])
        # {{ cost }} filled in by costBurn
        if fillin == 'cost':
          tokens[i] = skill.cost_burn
        # {{ e<num> }} filled in by effectBurn (e.g. {{ e4 }})
        elif fillin[0] == 'e':
          tokens[i] = skill.effect_burn[int(fillin[1:])]
        # TODO: check we've gotten all scaling types
        elif fillin[0] in ['a', 'f']:
          if fillin not in vars_map:
            tokens[i] = random.choice(self._MISSING_VARS_MEMES)
            continue
          v = vars_map[fillin]
          scaling_amounts = map(self._CoeffToPercentString, v.coeff)
          scaling_amount_str = '/'.join(scaling_amounts)
          scaling_type = v.link
          if scaling_type in self._SCALING_MAP:
            scaling_type = self._SCALING_MAP[scaling_type]
          tokens[i] = scaling_amount_str + ' ' + scaling_type
      except KeyError:
        # If a KeyError occurs (likely Rito's fault), proceed without
        # substituting this tag.
        pass

    return ''.join(tokens)

  def _ParseFillin(self, fillin):
    """Converts {{ attr }} to attr."""
    # TODO: less brittle code
    return fillin[3:-3]

  def _CoeffToPercentString(self, coeff):
    """Converts the given float to a percentage string."""
    percent = 100 * coeff
    # avoid decimal point if exact integer
    if percent == int(percent):
      percent = int(percent)
    return str(percent) + '%'

  def GetChampionLore(self, champ_name):
    """Returns the champion's lore.

    Args:
      champ_name: Chamption's name.

    Returns:
      Array of messages representing the champions' lore.
      Example:
        ['Sion, The Undead Juggernaut:', 'bla bla bla', ' ', bla bla bla bla']
    """
    champ = self._ProcessChampRegexs(champ_name)

    if not champ:
      return ['Champ "{}" not found.'.format(champ_name)]

    lore_strs = []
    lore_strs.append('{}, {}:'.format(champ.name, champ.title))

    # Champ's lores are not fully sanitized, there are several html breaklines.
    for sentence in champ.lore.split('<br>'):
      if sentence:
        lore_strs += self._CleanChampionWrap(sentence)
      else:
        # Simulate breaklines in hypebot's output.
        lore_strs.append(' ')
    return lore_strs

  def _ProcessChampRegexs(self, champ_name):
    champ = champ_name
    if re.match('dra+ven', champ_name, flags=re.IGNORECASE):
      champ = 'draven'
    elif re.match('nu+nu+', champ_name, flags=re.IGNORECASE):
      champ = 'nunu'
    return self._champ_name_complete.GuessThing(champ)

  def GetImageUrl(self, collection_name, filename):
    return BASE_DDRAGON_CDN_URL + '%s/img/%s/%s' % (self._version,
                                                    collection_name, filename)

  def GetSpellImageUrl(self, champ_name, skill_name):
    champ = self._ProcessChampRegexs(champ_name)
    if not champ:
      return None
    skill = self.GetChampSkill(champ, skill_name)
    if not skill:
      return None
    return self.GetImageUrl('spell', skill.image.full)

  def GetChampionImageUrl(self, champ_name):
    champ = self._ProcessChampRegexs(champ_name)
    if not champ:
      return None
    return self.GetImageUrl('champion', champ.image.full)

  def GetReforgedRuneMessage(self, rune_name):
    """Gets the reforged rune."""
    if self._reforged_runes_name_complete:
      rune = self._reforged_runes_name_complete.GuessThing(rune_name)
      if rune:
        return self._ComputeReforgedRuneCard(rune)

    return 'Reforged rune "{}" not found.'.format(rune_name)

  def _ComputeReforgedRuneCard(self, rune):
    # Make runes more dank.
    rune_name = util_lib.Dankify(rune.name)
    tooltip = util_lib.Dankify(rune.long_desc)
    var_table = client_vars.REFORGED_RUNE_VARS.get(rune.key, {})
    tooltip = re.sub(
        r'@.+?@',
        lambda match: var_table.get(match.group(0), r'¯\_(ツ)_/¯'), tooltip)
    slot = self._reforged_rune_slot[rune.key]
    path_description = '{} {}'.format(
        rune.rune_path_name, 'Keystone'
        if slot == 0 else 'Tier {}'.format(slot))

    rune_strs = []

    rune_strs.append('{}: {}'.format(rune_name, path_description))

    tooltip_strs = []
    for line in tooltip.split('<br>'):
      if line:
        line = re.sub(r'<.+?>', '', line)
        tooltip_strs += self._CleanChampionWrap(line)
    rune_strs += tooltip_strs

    return rune_strs

  @staticmethod
  def _CleanChampionWrap(description: Text) -> List[Text]:
    """Cleanly separates champion skill/lore descriptions."""
    result = []
    index = len(description) - 1
    last_cut = len(description)
    slice_state = 1
    counter = 0
    # Splits when a sentence contains a ':' within the first 20 characters.
    while index >= 0:
      if slice_state == 1 and description[index] == ':':
        slice_state = 2
        counter = 20
      elif slice_state == 2 and description[index] == '.':
        result = [description[index + 2:last_cut]] + result
        slice_state = 1
        last_cut = index + 1
      if counter < 0:
        slice_state = 1
      index -= 1
      counter -= 1
    result = [description[index + 1:last_cut]] + result
    # Splits excessively long descriptions (see heimer r).
    while True:
      split_index = len(result[-1])
      while len(result[-1][:split_index]) > 400:
        split_index = result[-1].rfind('.', 0, split_index)
      if split_index == len(result[-1]):
        break
      extras = result[-1][split_index + 1:]
      result[-1] = result[-1][:split_index + 1]
      result.append(extras)
    return result

  def _Sanitize(self, raw: Text) -> Text:
    return re.sub(r'<.*?>', '', raw)
