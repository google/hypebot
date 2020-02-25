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

import functools

from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import util_lib
from hypebot.protos.channel_pb2 import Channel
from typing import Text

_STACK_PREFIX = r'(?:hype)?stacks?'


@command_lib.CommandRegexParser(r'%s balance(?: (.+)?)?' % _STACK_PREFIX)
class HypeStackBalanceCommand(command_lib.BaseCommand):
  """Show the number of HypeStacks a given user possesses."""

  def _Handle(self,
              channel: Channel,
              user: Text,
              stack_user: Text) -> hype_types.CommandResponse:
    stack_user = stack_user or 'me'
    normalized_stack_user = util_lib.CanonicalizeName(stack_user)
    if normalized_stack_user == 'me':
      self._core.last_command = functools.partial(
          self._Handle, stack_user=stack_user)
      normalized_stack_user = user
      stack_user = user
    elif normalized_stack_user == self._core.name.lower():
      return '%s IS the stack' % self._core.name
    stack_user = stack_user.strip()
    stacks = self._core.hypestacks.GetHypeStacks(normalized_stack_user)
    stack_msg = '%s isn\'t very hype' % stack_user
    if stacks:
      stack_msg = '%s has %s' % (stack_user,
                                 inflect_lib.Plural(stacks, 'HypeStack'))
    return stack_msg


@command_lib.CommandRegexParser(r'%s buy ([0-9]+)' % _STACK_PREFIX)
class BuyHypeStackCommand(command_lib.BaseCommand):
  """Rewards consumerism with sellout HypeStacks."""

  @command_lib.HumansOnly()
  def _Handle(self,
              channel: Channel,
              user: Text,
              stack_amount: Text) -> hype_types.CommandResponse:
    num_stacks = util_lib.SafeCast(stack_amount, int, 0)
    if not num_stacks:
      self._core.bank.FineUser(user, 1, 'You must buy at least one HypeStack.',
                               self._Reply)
      return
    hypecoin_amount = self._core.hypestacks.PriceForHypeStacks(user, num_stacks)
    if not hypecoin_amount:
      return
    summary = 'purchase of %s for %s' % (
        inflect_lib.Plural(num_stacks, 'HypeStack'),
        util_lib.FormatHypecoins(hypecoin_amount))
    purchase_details = {
        'num_stacks': num_stacks,
        'summary': summary,
        'cost': hypecoin_amount
    }
    self._core.request_tracker.RequestConfirmation(
        user, summary, purchase_details, self._core.hypestacks.PurchaseStacks)
