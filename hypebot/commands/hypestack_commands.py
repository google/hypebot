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
"""Commands for HypeStacks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import util_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2
from typing import Text

_STACK_PREFIX = r'(?:hype)?stacks?'


@command_lib.CommandRegexParser(r'%s balance ?(?P<target_user>.*)' %
                                _STACK_PREFIX)
class HypeStackBalanceCommand(command_lib.BaseCommand):
  """Show the number of HypeStacks a given user possesses."""

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              target_user: user_pb2.User) -> hype_types.CommandResponse:
    if target_user.display_name.lower() == self._core.name.lower():
      return '%s IS the stack' % self._core.name
    stacks = self._core.hypestacks.GetHypeStacks(target_user)
    if stacks:
      return '%s has %s' % (target_user.display_name,
                            inflect_lib.Plural(stacks, 'HypeStack'))
    else:
      return '%s isn\'t very hype' % target_user.display_name


@command_lib.CommandRegexParser(r'%s buy ([0-9]+)' % _STACK_PREFIX)
class BuyHypeStackCommand(command_lib.BaseCommand):
  """Rewards consumerism with sellout HypeStacks."""

  @command_lib.HumansOnly()
  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              stack_amount: Text) -> hype_types.CommandResponse:
    num_stacks = util_lib.SafeCast(stack_amount, int, 0)
    if not num_stacks:
      self._core.bank.FineUser(user, 1, 'You must buy at least one HypeStack.',
                               self._Reply)
      return
    hypecoin_amount = self._core.hypestacks.PriceForHypeStacks(user, num_stacks)
    if not hypecoin_amount:
      return
    summary = 'purchase of %s for %s' % (inflect_lib.Plural(
        num_stacks, 'HypeStack'), util_lib.FormatHypecoins(hypecoin_amount))
    purchase_details = {
        'num_stacks': num_stacks,
        'summary': summary,
        'cost': hypecoin_amount
    }
    self._core.request_tracker.RequestConfirmation(
        user, summary, purchase_details, self._core.hypestacks.PurchaseStacks)
