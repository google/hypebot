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
"""Library for managing an "inventory" specific to each chat user.

An inventory consists of discrete items, each of which may have a function which
is accessible using the !use command. Each category of inventory item is
responsible for implementing its own !use functionality, and should be
registered via the Registrar class.

Inventory items are stored as a pickled dictionary, since each item can itself
be associated with data.

TODO: !use [item] on [pleb]

Currently convention of register requires that you register with the same name
as the class. Unless we need to create from params, we should probably spin a
simpler factory and force the convention instead of hoping people follow it.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
from collections import namedtuple
import random
from typing import Text

from six import with_metaclass

from hypebot import hype_types
from hypebot.core import factory_lib
from hypebot.plugins import coin_lib
from hypebot.storage import storage_lib


class BaseItem(with_metaclass(abc.ABCMeta)):
  """Base class for an item usable by a pleb."""

  human_name = 'Base Item'
  value = 0

  def __init__(self, core, user, params):
    self._core = core
    self._user = user
    self._params = params

  @property
  def name(self):
    return self.__class__.__name__

  @abc.abstractmethod
  def Use(self):
    """Called when the item is used by a user.

    Returns:
      A (message, boolean) pair. The message should be printed as a result of
      the item's use, and the boolean is whether the item should be marked for
      deletion.
    """
    pass


PurseDef = namedtuple('PurseDef', 'base inc_amount inc_chance')


class CoinPurse(BaseItem):
  """You feeling lucky kid?"""

  human_name = 'Coin purse'
  # Approximate median value of purse.
  value = 250

  COIN_PURSE_AMOUNTS = {
      'small': PurseDef(15, 3, 0.90),
      'medium': PurseDef(50, 5, 0.70),
      'large': PurseDef(100, 100, 0.5)
  }
  ROLLS_PER_PURSE = 3
  HAT_TOKEN_CHANCE = 0.02

  def Use(self):
    text = ['%s opens the coin purse...' % self._user]
    total_coin_amt = 0
    for _ in range(self.ROLLS_PER_PURSE):
      purse = random.choice(list(self.COIN_PURSE_AMOUNTS.values()))
      coin_amt = purse.base
      while random.random() < purse.inc_chance:
        coin_amt += purse.inc_amount
      text += ['%s found a roll of %d HypeCoins!' % (self._user, coin_amt)]
      total_coin_amt += coin_amt
    payment_succeeded = self._core.bank.ProcessPayment(
        coin_lib.MINT_ACCOUNT, self._user, total_coin_amt, 'Coin purse reward',
        self._core.Reply)
    if random.random() < self.HAT_TOKEN_CHANCE:
      self._core.inventory.AddItem(
          self._user, Create('HatToken', self._core, self._user, self._params))
      text.append(
          'While looking in the bottom of the bag, %s found a Hat Token!' %
          self._user)
    return (text, payment_succeeded)


class HatToken(BaseItem):
  """This is a TODO, it's as good as a real bug."""

  _GHOST_CHANCE = 0.25
  human_name = 'Hat token'
  # Approximate median value of hat token.
  value = 50000

  def Use(self):
    text = ['%s tries to turn their token into a hat.' % self._user]
    see_a_ghost = random.random() < self._GHOST_CHANCE
    if see_a_ghost:
      text += ('The ghost of tech debt past passes by, whispering',
               '👻 Refactor inventory_lib if you want to use your tokenssss 👻')
    text.append('Nothing %shappens' % ('else ' if see_a_ghost else ''))
    return (text, False)


class HypeEgg(BaseItem):
  """Find them if you can."""

  human_name = 'HypeEgg'
  value = 1000

  def Use(self):
    return ('What a pretty HypeEgg, it would be a shame to break it.', False)


_factory = factory_lib.Factory(BaseItem)
Create = _factory.Create  # pylint: disable=invalid-name


class InventoryManager(object):
  """Class that manages an inventory."""

  INVENTORY_SUBKEY = 'inventory'

  def __init__(self, store: storage_lib.HypeStore):
    self._store = store

  def GetUserInventory(self, user: Text) -> hype_types.JsonType:
    return self._store.GetJsonValue(user, self.INVENTORY_SUBKEY) or {}

  def AddItem(self, user: Text, item: BaseItem) -> bool:
    """Returns if user already had one or more copies of item."""
    return self._store.UpdateJson(user, self.INVENTORY_SUBKEY,
                                  lambda a: self._AddStack(a, item.name),
                                  lambda a: item.name in a)

  def _AddStack(self, inventory, item_name: Text):
    if item_name not in inventory:
      inventory[item_name] = {'number': 1}
      return
    if 'number' not in inventory[item_name]:
      inventory[item_name]['number'] = 1
    inventory[item_name]['number'] += 1

  def RemoveItem(self, user: Text, item: BaseItem) -> bool:
    """Returns if item was actually removed from users' inventory."""
    return self._store.UpdateJson(user, self.INVENTORY_SUBKEY,
                                  lambda a: self._RemoveStack(a, item.name),
                                  lambda a: item.name in a)

  def _RemoveStack(self, inventory, item_name: Text):
    if item_name not in inventory:
      return
    if inventory[item_name]['number'] == 1:
      inventory.pop(item_name)
      return
    inventory[item_name]['number'] -= 1
