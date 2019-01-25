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
"""items_lib fetches item data from the Riot API.

usage:
  # setup
  import items_lib
  s = items_lib.ItemsLib(api_key)

  # all return an array of strings
  s.GetItemDescription(item_name)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from hypebot.core import name_complete_lib


class ItemsLib(object):
  """Class for fetching item data from Riot API."""

  _ITEM_ALIAS_MAP = {
      'bc': 'theblackcleaver',
      'blackcleaver': 'theblackcleaver',
      'bloothirster': 'essencereaver',
      'bootsoflucidity': 'ionianbootsoflucidity',
      'bork': 'bladeoftheruinedking',
      'botrk': 'bladeoftheruinedking',
      'bt': 'thebloodthirster',
      'cdrboots': 'ionianbootsoflucidity',
      'dcap': 'rabadonsdeathcap',
      'fh': 'frozenheart',
      'fotm': 'faceofthemountain',
      'frozenfist': 'iceborngauntlet',
      'ibg': 'iceborngauntlet',
      'ie': 'infinityedge',
      'lucidityboots': 'ionianbootsoflucidity',
      'lw': 'lastwhisper',
      'mogs': 'warmogsarmor',
      'pd': 'phantomdancer',
      'qss': 'quicksilversash',
      'rabadabadoodle': 'rabadonsdeathcap',
      'runicechoes': 'enchantmentrunicechoes',
      'sv': 'spiritvisage',
      'swifties': 'bootsofswiftness',
      'triforce': 'trinityforce',
      }

  def __init__(self, rito):
    self._rito = rito
    self._name_to_item = {}
    self.ReloadData()

  def ReloadData(self):
    """Reload LoL items-related data into memory from the Rito API."""
    r = self._rito.ListItems()
    if not r:
      return
    item_data = r.data

    for item in item_data.values():
      name = self._GetItemName(item.name)
      self._name_to_item[name] = item

    self._name_complete = name_complete_lib.NameComplete(
        self._ITEM_ALIAS_MAP,
        self._name_to_item, (i.name for i in item_data.values()),
        dankify=True)

  def _GetItemName(self, item_name):
    """Gets Item name without non-alphanumeric chars and all lowercase."""
    return ''.join(list(filter(str.isalnum, str(item_name)))).lower()

  def GetItemDescription(self, item_name):
    """Returns Item Description."""
    # First Get Item
    item = self._name_complete.GuessThing(item_name)
    # Then Get Item Description
    if item:
      line = '{} ({} gold):'.format(item.name, item.gold.total)
      response = self._CleanItemWrap(self._Sanitize(item.description))
      response[0] = line + ' ' + response[0]
      return response
    else:
      return ['Item "{}" not found.'.format(item_name)]

  @staticmethod
  def _CleanItemWrap(description):
    """Cleanly separates item descriptions."""
    result = []
    index = 0
    slice_state = 0
    last_slice = 0
    # Separates each Active/Passive/Aura
    while index < len(description):
      if slice_state == 0 and (description[index:].startswith('UNIQUE ') or
                               description[index:].startswith('Active ') or
                               description[index:].startswith('Passive ')):
        result.append(description[last_slice:index -1])
        slice_state = 1
        last_slice = index
      elif slice_state == 1 and description[index] == ':':
        slice_state = 0
      index += 1
    description = description[last_slice:]
    # Removes all the hints at the end. Example:
    # (Unique Passives with the same name don't stack.)
    while description[-1] == ')'and description.rfind('(') != -1:
      description = description[:description.rfind('(')].strip()
    result.append(description)
    return result

  def _Sanitize(self, raw: Text) -> Text:
    return re.sub(r'<.*?>', '', raw)
