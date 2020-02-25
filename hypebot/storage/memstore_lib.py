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
"""In-memory HypeStore implementation.

This is intended as a stopgap solution in the case that the real storage
instance goes down again. It will allow HypeBot to perform basic functions.

It lacks many of the basic features of a proper store, including actual
transactions, permanent storage of values, and even historical values.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.core import cache_lib
from hypebot.hype_types import JsonType
from hypebot.storage import storage_lib

from typing import AnyStr, List, Optional, Tuple, Union


class MemTransaction(storage_lib.HypeTransaction):
  """This is a farce."""

  def Commit(self):
    return True


class MemStore(storage_lib.HypeStore):
  """Short term memory."""

  def __init__(self, params, *args, **kwargs):
    self._memory = cache_lib.LRUCache(2048)
    # Seed the bank with a little bit of money so the temporary economy can
    # function.
    self._memory.Put('hypebank:bank:balance', '1337000000')
    super(MemStore, self).__init__(params, *args, **kwargs)

  @property
  def engine(self):
    return 'memstore'

  def GetValue(self,
               key: AnyStr,
               subkey: AnyStr,
               tx: Optional[MemTransaction] = None) -> Optional[AnyStr]:
    return self._memory.Get('%s:%s' % (key, subkey))

  def SetValue(self,
               key: AnyStr,
               subkey: AnyStr,
               value: Union[int, AnyStr],
               tx: Optional[MemTransaction] = None) -> None:
    self._memory.Put('%s:%s' % (key, subkey), value)

  def DeleteKey(self, key: AnyStr, tx: Optional[MemTransaction] = None) -> None:
    self._memory.Del(key)

  def GetSubkey(self, subkey: AnyStr,
                tx: Optional[MemTransaction] = None) -> List[Tuple]:
    items = []
    for cache_key, value in self._memory.Iterate():
      parts = cache_key.split(':')
      if len(parts) > 2 and ':'.join(parts[1:]) == subkey:
        items.append((parts[0], value))
    return items

  def GetHistoricalValues(self,
                          key: AnyStr,
                          subkey: AnyStr,
                          num_past_values: int,
                          tx: Optional[MemTransaction] = None):
    value = self.GetJsonValue(key, subkey, tx)
    if value is not None:
      return [value]
    return []

  def PrependValue(self,
                   key: AnyStr,
                   subkey: AnyStr,
                   new_value: JsonType,
                   max_length: Optional[int] = None,
                   tx: Optional[MemTransaction] = None) -> None:
    self.SetJsonValue(key, subkey, new_value, tx)

  def NewTransaction(self, tx_name: AnyStr) -> MemTransaction:
    return MemTransaction(tx_name)
