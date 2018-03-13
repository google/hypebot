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
"""HypeCoin sinks to flaunt your wealth."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.commands import command_lib
from hypebot.core import util_lib
from hypebot.plugins import coin_lib


@command_lib.CommandRegexParser(r'greet(?:ing)? ?(.*?)')
class GreetingPurchaseCommand(command_lib.BaseCommand):
  """Let you buy some welcome bling."""

  @command_lib.MainChannelOnly
  @command_lib.HumansOnly()
  def _Handle(self, channel, user, subcommand):
    greetings = self._UserGreetings(user)

    subcommand = subcommand.lower()
    str_range = (str(x) for x in range(len(greetings)))
    if subcommand == 'list':
      return self._HandleList(channel, user, greetings)
    elif subcommand not in str_range:
      return ('Please try again with your selection or try %sgreet list'
              % self.command_prefix)
    else:
      selection = int(subcommand)
      greeting_cost = greetings[selection][0]
      if self._core.bank.ProcessPayment(
          user, coin_lib.FEE_ACCOUNT, greeting_cost,
          'Purchased greeting #%s' % selection, self._Reply):
        self._core.cached_store.SetValue(
            user, 'greetings', greetings[selection][1])
        # This is equiv to deleting the row so they get welcomed with their new
        # greeting
        self._core.cached_store.SetValue(user, 'lastseen', '0')

  def _UserGreetings(self, user):
    """Build list of potential greetings for the user."""
    return [
        (1000, 'Hiya, {user}!'),
        (5000, 'Who\'s afraid of the big bad wolf? Certainly not {user}!'),
        (10000, 'All hail {user}!'),
        (25000, 'Make way for the mighty {user}!'),
        (100000,
         u'Wow {user}, you have {bal}, you must be fulfilled as a person!'),
    ]

  @command_lib.LimitPublicLines(max_lines=0)
  def _HandleList(self, channel, user, all_greetings):
    msgs = [
        'You can purchase one of the following upgraded greetings from '
        '%s' % self._core.params.name
    ]
    for i, greeting in enumerate(all_greetings):
      msgs.append('  %sgreet %d [%s] - \'%s\'' %
                  (self.command_prefix, i,
                   util_lib.FormatHypecoins(greeting[0]), greeting[1]))
    return msgs
