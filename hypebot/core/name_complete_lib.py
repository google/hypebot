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
"""name_complete handles name completion and alias matching.

usage:
  # setup
  import name_complete_lib
  n = name_complete_lib.NameComplete(alias_map, name_map)

  # returns corresponding item or champion or None if none found.
  n.GuessThing(name)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import bisect
import collections

from hypebot.core import util_lib


class NameComplete(object):
  """Class for completing names of things."""

  def __init__(self, alias_map, name_map, display_names=None, dankify=False):
    """NameComplete constructor.

    Args:
      alias_map: Map String->String of alias (nickname) to canonical name.
      name_map: Map String->Thing of canonical name to thing.
      display_names: (optional) Iterable of Strings. A list of display names.
        Every word of a display name will be used to map to the canonical name,
        as long as the word is unique among the list.
      dankify: Whether to make all things dank.
    """
    self._alias_to_name = alias_map.copy()
    self._name_to_thing = name_map
    aliases_from_display_names = self._GetAliasesFromDisplayNames(display_names)
    for alias, name in aliases_from_display_names.items():
      self._alias_to_name[alias] = name
    if dankify:
      for alias, name in list(self._alias_to_name.items()):
        dank_alias = util_lib.Dankify(alias)
        if alias != dank_alias:
          self._alias_to_name[dank_alias] = name
    self._possible_things = sorted(list(self._alias_to_name.keys()) +
                                   list(name_map.keys()))

  def _GetAliasesFromDisplayNames(self, display_names):
    """Creates a map of unique words from display_names to canonical names."""
    if not display_names:
      return {}
    # map of word (string) -> set of canonical names (set)
    word_to_names = collections.defaultdict(set)
    for name in display_names:
      # split name into words that are canonicalized
      words = map(util_lib.CanonicalizeName, name.split())
      canonical_name = util_lib.CanonicalizeName(name)
      # map each of the words to the canonical name
      for word in words:
        word_to_names[word].add(canonical_name)

    # return a map of only words that are unique
    aliases_map = {}
    for word, names_set in word_to_names.items():
      if len(names_set) == 1:
        name = names_set.pop()
        # if the name was just one word, don't use itself as an alias
        if word != name:
          aliases_map[word] = name
    return aliases_map

  def GuessThing(self, name):
    """Guesses the object from alias or name and autocompletes."""
    name = util_lib.CanonicalizeName(name)
    if name in self._name_to_thing:
      return self._name_to_thing[name]
    if name in self._alias_to_name:
      try:
        return self._name_to_thing[self._alias_to_name[name]]
      except KeyError:
        return None

    # look for prefix in sorted array of names
    # left_idx is first location at least as large as nickname
    left_idx = bisect.bisect_left(self._possible_things, name)
    # right_idx is first location after all things that start with nickname
    right_idx = bisect.bisect_right(self._possible_things,
                                    name + 'zzz')

    # only return if there's only one possible champ with that prefix
    total_names = set()
    for i in range(left_idx, right_idx):
      possible_name = self._possible_things[i]
      if possible_name in self._alias_to_name:
        total_names.add(self._alias_to_name[possible_name])
      if possible_name in self._name_to_thing:
        total_names.add(possible_name)
    if len(total_names) == 1:
      return self._name_to_thing[total_names.pop()]
    return None
