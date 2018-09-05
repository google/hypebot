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
"""HypeStacks are fun."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random
from typing import Mapping

from absl import logging

from hypebot.core import util_lib
from hypebot.plugins import coin_lib
from hypebot.storage import storage_lib


class HypeStacks(object):
  """Manages the awarding and purchasing of HypeStacks.

  HypeStacks are an asset that users can either earn through meritorious
  behaviors or purchase with hypecoins. Some of the rules around them include:
   * HypeStacks become progressivly more expensive the more you try to buy.
   * HypeStacks holdings decay once a day, and their price scaling resets.
  """

  _STACK_COUNT_SUBKEY = 'stacks:count'
  _RECENT_STACKS_SUBKEY = 'stacks:recent'

  def __init__(self, store, bank, msg_fn) -> None:
    self._store = store
    self._bank = bank
    self._msg_fn = msg_fn

  def AwardStack(self, user: str) -> None:
    """Awards a new HypeStack for model behavior."""
    self._store.UpdateValue(user, self._STACK_COUNT_SUBKEY, 1)

  def DecayHypeStacks(self) -> None:
    """Callback to decay all users' HypeStacks.

    Each user loses 10-50% of their current stacks. Amount is random per user.
    """
    logging.info('Decaying all hypestacks')
    for user, stacks in self._store.GetSubkey(self._STACK_COUNT_SUBKEY):
      retention_factor = random.uniform(0.5, 0.9)
      new_value = int(int(stacks) * retention_factor)
      logging.info('\t%s: %s => %s (%.2f%% retention)', user, stacks, new_value,
                   100 * retention_factor)
      self._store.SetValue(user, self._STACK_COUNT_SUBKEY, str(new_value))
      # Recent stack count is reset each day.
      self._store.SetValue(user, self._RECENT_STACKS_SUBKEY, '0')

  def GetHypeStacks(self, user: str) -> int:
    """Returns the number of HypeStacks user currently has accumulated."""
    stacks = self._store.GetValue(user, self._STACK_COUNT_SUBKEY)
    return util_lib.SafeCast(stacks, int, 0)

  def PriceForHypeStacks(self, user: str, num_stacks: int) -> int:
    """Returns the price for user to purchase num_stacks.

    Hypestacks cost 1k each, plus 20% of the cost of the previous stack. The
    formula for the cost of the nth hypestack is y = 1000*1.2**(n-1), which
    leads to the formula for the total cost of the mth to nth hypestacks as
    sum(f(i) for i in range(m, n+1)). Solving for the closed form gives us the
    formula in TotalHypeStackPrice, plus truncation since hypecoins only come in
    integer values.

    Args:
      user: The user to fetch the price for.
      num_stacks: How many new stacks the user is looking to purchase.
    Returns:
      The total cost in hypecoins for user to purcase num_stacks.
    """
    def TotalHypeStackPrice(num_stacks: int) -> int:
      return int(6000 * 1.2**(num_stacks - 1) - 5000)

    recent_stacks = util_lib.SafeCast(
        self._store.GetValue(user, self._RECENT_STACKS_SUBKEY), int, 0)
    num_stacks += recent_stacks
    return TotalHypeStackPrice(num_stacks) - TotalHypeStackPrice(recent_stacks)

  def PurchaseStacks(self, user: str, purchase_details: Mapping) -> None:
    """Purchases new HypeStacks for user based on info in purchase_details."""
    details = purchase_details['summary'].capitalize()
    num_stacks = purchase_details['num_stacks']
    # TODO: This should actually be in the same transaction as the call
    #   to _UpdateAllStacks if the storage engine can support that, e.g., Redis.
    if not self._bank.ProcessPayment(user, coin_lib.FEE_ACCOUNT,
                                     purchase_details['cost'], details,
                                     self._msg_fn):
      logging.error('Purchase of %s hypestack(s) failed!', num_stacks)
      return
    tx_name = 'HypeStacks: %s += %s' % (user, num_stacks)
    self._store.RunInTransaction(self._UpdateAllStacks, user, num_stacks,
                                 tx_name=tx_name)

  def _UpdateAllStacks(self, user: str, num_stacks: int,
                       tx: storage_lib.HypeTransaction) -> None:
    """Updates the total stack count and recent count of user atomically."""
    self._store.UpdateValue(user, self._STACK_COUNT_SUBKEY, num_stacks, tx)
    self._store.UpdateValue(user, self._RECENT_STACKS_SUBKEY, num_stacks, tx)
