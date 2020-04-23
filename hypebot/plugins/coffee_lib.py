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

import random
from typing import Any, Dict, Optional, Text, Union

from grpc import StatusCode

from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.protos import coffee_pb2
from hypebot.protos import user_pb2
from hypebot.storage import storage_lib

# pylint: disable=line-too-long
# pylint: enable=line-too-long
from google.protobuf import json_format


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

  def __init__(self, store: storage_lib.HypeStore, bot_name: Text):
    self._store = store
    self._bot_name = bot_name
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Lock()

    self._InitWeights()

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

  def DrinkCoffee(
      self,
      user: user_pb2.User,
      tx: Optional[storage_lib.HypeTransaction] = None
  ) -> Union[Dict[Text, Any], StatusCode]:
    """Lets user drink some of their nice coffee."""
    if not tx:
      return self._store.RunInTransaction(self.DrinkCoffee, user)
    user_data = self.GetCoffeeData(user, tx)
    if user_data == StatusCode.NOT_FOUND or not user_data.beans:
      return StatusCode.NOT_FOUND

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
    if user_data == StatusCode.NOT_FOUND:
      user_data = coffee_pb2.CoffeeData()
      user_data.CopyFrom(self._DEFAULT_COFFEE_DATA)
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
      bean.id = self._GetBeanId(bean)
      user_data.beans.append(bean)
      user_data.statistics.find_count += 1
    self._SetCoffeeData(user, user_data, tx)
    return bean or StatusCode.NOT_FOUND

  def _GetBeanId(self, bean: coffee_pb2.Bean) -> Text:
    return bean.rarity[0] + bean.variety[0] + bean.region.lower()

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
  ) -> Union[StatusCode, coffee_pb2.CoffeeData]:
    """Returns user_data for user."""
    serialized_data = self._store.GetJsonValue(user.user_id, self._SUBKEY, tx)
    if not serialized_data:
      return StatusCode.NOT_FOUND
    return json_format.Parse(serialized_data, coffee_pb2.CoffeeData())

  def _SetCoffeeData(self,
                     user: user_pb2.User,
                     coffee_data: coffee_pb2.CoffeeData,
                     tx: Optional[storage_lib.HypeTransaction] = None):
    serialized_data = json_format.MessageToJson(coffee_data)
    self._store.SetJsonValue(user.user_id, self._SUBKEY, serialized_data, tx)
