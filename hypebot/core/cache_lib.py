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
"""Cache money, I just got paid."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections

import arrow
from typing import Any, AnyStr, Generator, Tuple


class _TimedCacheElement(object):
  """Struct to store an element in the cache."""

  def __init__(self, key: Any, value: Any):
    self.key = key
    self.value = value
    self.timestamp = arrow.now()


class LRUCache(object):
  """LRU cache."""

  def __init__(self, max_items: int, max_age_secs: int = None):
    if not isinstance(max_items, int) or max_items < 1:
      raise ValueError('The cache max_items must be >=1')
    self._max_age_secs = max_age_secs
    self._max_items = max_items
    self._dict = collections.OrderedDict()

  def __str__(self) -> AnyStr:
    return '%s [%s/%s items, %ss TTL]' % (
        self.__class__.__name__,
        len(self._dict),
        self._max_items,
        self._max_age_secs)

  def Get(self, key: Any) -> Any:
    self._RemoveStaleElements()
    if key in self._dict:
      element = self._dict.pop(key)
      element.timestamp = arrow.now()
      self._dict[key] = element
      return element.value
    return None

  def Put(self, key: Any, value: Any) -> Any:
    if key in self._dict:
      del self._dict[key]
    elif len(self._dict) >= self._max_items:
      self._dict.popitem(last=False)
    self._dict[key] = _TimedCacheElement(key, value)

  def Del(self, key: Any) -> None:
    if key in self._dict:
      del self._dict[key]

  def Iterate(self) -> Generator[Tuple[Any, Any], None, None]:
    """Iterating does not reset the timestamps of any objects."""
    self._RemoveStaleElements()
    for key, element in self._dict.items():
      yield (key, element.value)

  def Flush(self):
    self._dict.clear()

  def _RemoveStaleElements(self):
    if not self._max_age_secs:
      return
    evict_time = arrow.now().shift(seconds=0 - self._max_age_secs)
    while self._dict:
      last_element = next(iter(self._dict.values()))
      if last_element.timestamp < evict_time:
        del self._dict[last_element.key]
      else:
        return
