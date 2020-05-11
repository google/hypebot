# Lint as: python3
# coding=utf-8
# Copyright 2020 The Hypebot Authors. All rights reserved.
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
"""Manage your caffeine game with this simple plugin."""

import math
import random
from typing import Any, Dict, List, Optional, Text, Union

from absl import logging
from grpc import StatusCode

from hypebot.core import params_lib
from hypebot.core import schedule_lib
from hypebot.core import util_lib
from hypebot.protos import coffee_pb2
from hypebot.protos import user_pb2
from hypebot.storage import storage_lib

# pylint: disable=line-too-long
# pylint: enable=line-too-long
from google.protobuf import json_format


# TODO: Consider returning StatusCodes to differentiate between not
#   found and multiple prefix matches.
def GetBean(bean_id: Text,
            beans: List[coffee_pb2.Bean],
            remove_bean: bool = False) -> Optional[coffee_pb2.Bean]:
  """Given a bean_id, returns the first matching bean from beans, or None.

  Also supports passing a prefix of a bean_id. If the prefix can uniquely match
  a single bean_id in beans, the first such match will be returned, otherwise
  None will be returned.

  Args:
    bean_id: The ID of the bean to find.
    beans: A list of beans to search through.
    remove_bean: If True, will also remove the bean from the passed list. Note
      since this is a free function the caller is responsible for persisting any
      changes to the beans list.

  Returns:
    The first bean with bean_id, or None if a match could not be found.
  """
  prefix_match_id = None
  idx = None
  bean_id = bean_id.lower()
  for i, b in enumerate(beans):
    # We lower-case the IDs here as a sneaky migration step.
    b.id = b.id.lower()
    # If we find an exact match, just return that
    if b.id == bean_id:
      idx = i
      break
    if b.id.startswith(bean_id):
      # Otherwise, set the prefix match and continue.
      if not prefix_match_id:
        prefix_match_id = b.id
        idx = i
      if b.id != prefix_match_id:
        # Multiple distinct bean_ids match this prefix, so return None.
        return None

  if idx is None:
    return None
  if remove_bean:
    return beans.pop(idx)
  return beans[idx]


def _GetBeanId(bean: coffee_pb2.Bean) -> Text:
  if not all([bean.rarity, bean.variety, bean.region]):
    raise ValueError('Bean is missing required field, can\'t generate ID:\n%s' %
                     bean)
  return (bean.rarity[0] + bean.variety[0] + bean.region).lower()


class CoffeeLib:
  """Handles the management of coffee for plebs."""

  _SUBKEY = 'coffee'

  # For new users, we initialize their CoffeeData to a copy of this value.
  _DEFAULT_COFFEE_DATA = coffee_pb2.CoffeeData(energy=10)

  DEFAULT_PARAMS = params_lib.HypeParams({
      # Chance of finding a bean when searching with no other modifiers. [0,1)
      'bean_chance': 0.5,
      # Number of beans that can be stored before a user runs out of room.
      'bean_storage_limit': 10,
      # Weights used to calculate drop rates for bean regions. Data is actual
      # coffee production by country/region in 1000's of 60kg bags.
      #
      # Global data source:
      # http://www.ico.org/historical/1990%20onwards/PDF/1a-total-production.pdf
      # Hawaii data source:
      # https://www.nass.usda.gov/Statistics_by_State/Hawaii/Publications/Fruits_and_Nuts/201807FinalCoffee.pdf
      #
      # Retrieved 2020/04/07, regions with less than 0.1% of global production
      # have been removed.
      'region_weights': {
          'Brazil': 62925,
          'Colombia': 13858,
          'Cote d\'Ivoire': 2294,
          'Ethiopia': 7776,
          'Guatemala': 4007,
          'Honduras': 7328,
          'India': 5302,
          'Indonesia': 9418,
          'Mexico': 4351,
          'Nicaragua': 2510,
          'Peru': 4263,
          'Uganda': 4704,
          'Vietnam': 31174,
      },
      # Weights used to calculate drop rates for bean varities.
      'variety_weights': {
          'Arabica': 6,
          'Robusta': 3,
          'Liberica': 1,
      },
      # Weights used to calculate drop rates for bean rarities.
      'rarity_weights': {
          'common': 50,
          'uncommon': 28,
          'rare': 14,
          'precious': 7,
          'legendary': 1,
      }
  })

  def __init__(self, scheduler: schedule_lib.HypeScheduler,
               store: storage_lib.HypeStore, bot_name: Text):
    self._scheduler = scheduler
    self._store = store
    self._bot_name = bot_name
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Lock()

    self._InitWeights()
    self._scheduler.DailyCallback(util_lib.ArrowTime(6), self._RestoreEnergy)

  def _InitWeights(self):
    """Initializes WeightedCollections for use in generating new beans."""
    # Actual production data ends up being a bit too skewed towards the largest
    # regions for gameplay purposes, so we smooth the distribution out by moving
    # all weights towards the median.
    region_weights = self._params.region_weights.AsDict()
    regions_by_weight = sorted(region_weights.items(), key=lambda x: x[1])
    region_value_median = regions_by_weight[len(region_weights) // 2][1]
    smoothed_region_weights = {
        k: v + (region_value_median - v) * 0.5
        for k, v in region_weights.items()
    }
    scale_factor = sum(region_weights.values()) / sum(
        smoothed_region_weights.values())
    smoothed_region_weights = {
        k: scale_factor * v for k, v in smoothed_region_weights.items()
    }

    self._weighted_regions = util_lib.WeightedCollection(
        smoothed_region_weights.keys(), smoothed_region_weights.values())
    self._weighted_rarities = util_lib.WeightedCollection(
        self._params.rarity_weights.AsDict().keys(),
        self._params.rarity_weights.AsDict().values())
    self._weighted_varieties = util_lib.WeightedCollection(
        self._params.variety_weights.AsDict().keys(),
        self._params.variety_weights.AsDict().values())

    self._weighted_regions.Freeze()
    self._weighted_rarities.Freeze()
    self._weighted_varieties.Freeze()

  def _RestoreEnergy(self) -> None:
    # No transaction for the whole function because we don't want to hold a tx
    # while we update every single user. This way gets us a snapshot of all
    # users, then updates each one atomically.
    user_list = self._store.GetSubkey(self._SUBKEY)
    c = 0
    for username, data in user_list:
      if data:
        c += 1
        self._store.RunInTransaction(self._RestoreUserEnergy, username)
    logging.info('Restored energy to %d pleb(s)', c)

  def _RestoreUserEnergy(
      self,
      username: Text,
      tx: Optional[storage_lib.HypeTransaction] = None) -> None:
    if not tx:
      return self._store.RunInTransaction(self._RestoreUserEnergy, username)
    user = user_pb2.User(user_id=username)
    user_data = self.GetCoffeeData(user, tx)
    # Min is set such that there is a ~1% chance that a user with no beans ends
    # up at 0 energy without finding at least one bean.
    min_energy = int(math.ceil(math.log(0.01, self._params.bean_chance)))
    max_energy = min_energy * 4
    # We allow users to go over the "max" energy, but they will stop
    # regenerating energy until they fall back below the max.
    if user_data.energy < max_energy:
      user_data.energy = max(min_energy, user_data.energy + 3)
      # Ensure we don't regen over the max.
      user_data.energy = min(max_energy, user_data.energy)
    self._SetCoffeeData(user, user_data, tx)

  def DrinkCoffee(
      self,
      user: user_pb2.User,
      bean_id: Optional[Text] = None,
      tx: Optional[storage_lib.HypeTransaction] = None
  ) -> Union[Dict[Text, Any], StatusCode]:
    """Lets user drink some of their nice coffee."""
    if not tx:
      return self._store.RunInTransaction(self.DrinkCoffee, user, bean_id)
    user_data = self.GetCoffeeData(user, tx)
    if not user_data.beans:
      return StatusCode.NOT_FOUND

    bean = None
    if bean_id:
      bean = GetBean(bean_id, user_data.beans, remove_bean=True)
      if not bean:
        return StatusCode.NOT_FOUND
    else:
      bean = user_data.beans.pop(random.randint(0, len(user_data.beans) - 1))
    energy = random.randint(1, 6)
    user_data.energy += energy
    user_data.statistics.drink_count += 1
    self._SetCoffeeData(user, user_data, tx)
    return {'energy': energy, 'bean': bean}

  def FindBeans(
      self,
      user: user_pb2.User,
      tx: Optional[storage_lib.HypeTransaction] = None
  ) -> Union[StatusCode, coffee_pb2.CoffeeData]:
    """Tries to scrounge up some beans for user."""
    if not tx:
      return self._store.RunInTransaction(self.FindBeans, user)
    user_data = self.GetCoffeeData(user, tx)
    if user_data.energy <= 0:
      return StatusCode.RESOURCE_EXHAUSTED
    if len(user_data.beans) > self._params.bean_storage_limit:
      return StatusCode.OUT_OF_RANGE

    user_data.energy -= 1
    bean = None
    r = random.random()
    if r < self._params.bean_chance:
      region = self._weighted_regions.GetItem()
      bean = coffee_pb2.Bean(
          region=region,
          variety=self._weighted_varieties.GetItem(),
          rarity=self._weighted_rarities.GetItem(),
      )
      user_data.beans.append(bean)
      user_data.statistics.find_count += 1
    self._SetCoffeeData(user, user_data, tx)
    return bean or StatusCode.NOT_FOUND

  def GetOccurrenceChance(self, bean: coffee_pb2.Bean) -> float:
    """Returns the probability of finding bean in the wild."""
    region_weight = self._weighted_regions.GetWeight(bean.region)
    variety_weight = self._weighted_varieties.GetWeight(bean.variety)
    rarity_weight = self._weighted_rarities.GetWeight(bean.rarity)
    return region_weight * variety_weight * rarity_weight

  def GetCoffeeData(
      self,
      user: user_pb2.User,
      tx: Optional[storage_lib.HypeTransaction] = None
  ) -> coffee_pb2.CoffeeData:
    """Returns user_data for user, or the default data if user is not found."""
    serialized_data = self._store.GetJsonValue(user.user_id, self._SUBKEY, tx)
    if serialized_data:
      return json_format.Parse(serialized_data, coffee_pb2.CoffeeData())
    coffee_data = coffee_pb2.CoffeeData()
    coffee_data.CopyFrom(self._DEFAULT_COFFEE_DATA)
    return coffee_data

  def _SetCoffeeData(self,
                     user: user_pb2.User,
                     coffee_data: coffee_pb2.CoffeeData,
                     tx: Optional[storage_lib.HypeTransaction] = None):
    # We first generate bean_ids for any beans missing one.
    for b in [b for b in coffee_data.beans if not b.id]:
      b.id = _GetBeanId(b)
    serialized_data = json_format.MessageToJson(coffee_data)
    self._store.SetJsonValue(user.user_id, self._SUBKEY, serialized_data, tx)

  def TransferBeans(
      self,
      owner: user_pb2.User,
      target: user_pb2.User,
      bean_id: Text,
      tx: Optional[storage_lib.HypeTransaction] = None) -> StatusCode:
    """Transfers bean_id from owner_id to target_id."""
    if not tx:
      return self._store.RunInTransaction(self.TransferBeans, owner, target,
                                          bean_id)
    owner_beans = self.GetCoffeeData(owner)
    bean = GetBean(bean_id, owner_beans.beans)
    if not bean:
      return StatusCode.NOT_FOUND

    target_beans = self.GetCoffeeData(target, tx)
    if len(target_beans.beans) >= self._params.bean_storage_limit:
      return StatusCode.OUT_OF_RANGE

    owner_beans.beans.remove(bean)
    owner_beans.statistics.sell_count += 1
    target_beans.beans.append(bean)
    target_beans.statistics.buy_count += 1
    self._SetCoffeeData(owner, owner_beans, tx)
    self._SetCoffeeData(target, target_beans, tx)
    return StatusCode.OK
