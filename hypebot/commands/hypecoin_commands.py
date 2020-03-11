# Lint as: python3
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
"""Commands that touch money."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from functools import partial
from typing import Optional, Text

from absl import logging
import arrow
from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.plugins import coin_lib
from hypebot.protos import bet_pb2
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2
import six

_HC_PREFIX = r'(?:h(?:ype)?c(?:oins?)?|₡)'


@command_lib.CommandRegexParser(r'%s balance ?(?P<target_user>.*)' % _HC_PREFIX)
@command_lib.RegexParser(r'()(\S+)\?\?(?:[\s,.!?]|$)')
class HCBalanceCommand(command_lib.BaseCommand):
  """How much cash does a user have?"""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'target_any': True})

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              target_user: user_pb2.User) -> hype_types.CommandResponse:
    balance = self._core.bank.GetBalance(target_user)
    return '%s has %s' % (target_user.display_name,
                          util_lib.FormatHypecoins(balance))


@command_lib.CommandRegexParser(
    r'(?:%s )?bet (.+?)( more)? (on|for|against) (.+?)' % _HC_PREFIX)
class HCBetCommand(command_lib.BaseCommand):
  """When people put their money where their mouth is."""

  # Open Q:
  #   How to handle the fact that some bet_target (e.g. ROX) could be valid for
  #   multiple games? Probably have basebot privmsg the user?
  #   Could also have a sytem where different targets will use their own
  #   hypecoins to bid on which one gets to handle the bet.
  #   User could also specify by name, e.g., 'lol', 'stock'.
  @command_lib.HumansOnly()
  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              amount_str: Text, more_str: Text, direction: Text,
              bet_target: Text) -> hype_types.CommandResponse:
    if user.bot:
      return '%s doesn\'t meddle in human affairs' % user.display_name
    msg_fn = partial(self._Reply, default_channel=channel)

    amount = self._core.bank.ParseAmount(user, amount_str, msg_fn)
    if amount is None:
      return
    elif amount <= 0:
      return 'Try being positive for a change.'

    more = more_str == ' more' or amount_str in messages.GAMBLE_STRINGS
    if direction == 'on':
      direction = 'for'

    bet = bet_pb2.Bet(
        user=user,
        amount=amount,
        resolver=self._core.name.lower(),
        direction=bet_pb2.Bet.Direction.Value(direction.upper()),
        target=bet_target.lower())
    for game in self._core.betting_games:
      taken = game.TakeBet(bet)
      if taken:
        if isinstance(taken, six.string_types):
          details = '%s Please do not waste my time.' % taken
          self._core.bank.FineUser(user, 1, details, msg_fn)
          return
        if not self._core.bets.PlaceBet(game, bet, msg_fn, more):
          logging.error('Placing bet failed: %s => %s', user, bet)
          return
        return
    details = 'Unknown target for betting. Please do not waste my time.'
    self._core.bank.FineUser(user, 1, details, msg_fn)


@command_lib.CommandRegexParser(r'%s (my)?bets ?(.+)?' % _HC_PREFIX)
class HCBetsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'num_bets': 5})

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User, me: Text,
              users_or_games: Text) -> hype_types.CommandResponse:
    game_names = {g.name.lower(): g for g in self._core.betting_games}
    desired_games = set()
    users = {}
    if me:
      users[user.user_id] = user
    for user_or_game in (users_or_games or '').split():
      if user_or_game in game_names:
        desired_games.add(game_names[user_or_game])
      elif user_or_game == 'me':
        users[user.user_id] = user
      else:
        maybe_user = self._core.interface.FindUser(user_or_game)
        if maybe_user:
          users[maybe_user.user_id] = maybe_user
    query_name = '%s%s%s' % (', '.join([u.display_name for u in users.values()
                                       ]), ' - ' if users and desired_games else
                             '', ', '.join([g.name for g in desired_games]))

    # Default behaviors if not specified.
    if not users:
      users = {None: None}  # This will allow all users in a LookupBets.
    if not desired_games:
      desired_games = self._core.betting_games

    bets = []
    bet_total = 0
    for game in desired_games:
      for bet_user in users.values():
        bets_by_user = self._core.bets.LookupBets(game.name, bet_user)
        for _, user_bets in bets_by_user.items():
          for bet in user_bets:
            if len(users) > 1 or users == {None: None}:
              bets.append(
                  (bet.amount,
                   '- %s, %s' % (bet.user.display_name, game.FormatBet(bet))))
            else:
              bets.append((bet.amount, '- %s' % game.FormatBet(bet)))
            bet_total += bet.amount
    bets.sort(key=lambda bet: bet[0], reverse=True)
    bets = [betstring for _, betstring in bets]

    if not bets:
      query_str = '%s has n' % query_name if query_name else 'N'
      return '%so current bets. Risk aversion is unbecoming' % query_str

    responses = [
        '%s current bets [%s, %s]' %
        (query_name or 'All', inflect_lib.Plural(
            len(bets), 'bet'), util_lib.FormatHypecoins(bet_total))
    ]
    if (len(bets) > self._params.num_bets and
        channel.visibility == channel_pb2.Channel.PUBLIC):
      responses.append('Only showing %d bets, addiction is no joke.' %
                       self._params.num_bets)
      bets = bets[:self._params.num_bets]

    responses.extend(bets)
    return responses


@command_lib.CommandRegexParser(r'%s circ(?:ulation)?' % _HC_PREFIX)
class HCCirculationCommand(command_lib.BaseCommand):

  def _Handle(self, channel: channel_pb2.Channel,
              user: user_pb2.User) -> hype_types.CommandResponse:
    num_users, coins_in_circulation = self._core.bank.GetBankStats(
        plebs_only=True)
    return ('There is %s circulating among %s.' %
            (util_lib.FormatHypecoins(coins_in_circulation),
             inflect_lib.Plural(num_users, 'pleb')))


@command_lib.CommandRegexParser(r'%s forbes(?: (?P<target_user>.+))?' %
                                _HC_PREFIX)
class HCForbesCommand(command_lib.BaseCommand):
  """Display net worth of a single user or the wealthiest peeps."""

  @command_lib.LimitPublicLines()
  def _Handle(
      self, channel: channel_pb2.Channel, user: user_pb2.User,
      target_user: Optional[user_pb2.User]) -> hype_types.CommandResponse:
    if target_user:
      balance = self._core.bank.GetBalance(target_user)
      for game in self._core.betting_games:
        game_bets = self._core.bets.LookupBets(game.name, target_user)
        for bet in game_bets.get(target_user.user_id, []):
          balance += bet.amount
      return ('%s has a net worth of %s' %
              (target_user.display_name,
               util_lib.FormatHypecoins(balance, abbreviate=True)))

    # Top 4 plebs by net worth.
    pleb_balances = defaultdict(int)  # user_id -> worth
    pleb_balances.update(self._core.bank.GetUserBalances(plebs_only=True))
    for game in self._core.betting_games:
      game_bets = self._core.bets.LookupBets(game.name)
      for pleb, pleb_bets in game_bets.items():
        for bet in pleb_bets:
          pleb_balances[pleb] += bet.amount
    pleb_balances = sorted(
        [(pleb, balance) for pleb, balance in pleb_balances.items()],
        key=lambda x: x[1],
        reverse=True)

    responses = ['Forbes 4:']
    position = 1
    prev_balance = -1
    for i, (user_id, balance) in enumerate(pleb_balances[:4]):
      user = self._core.interface.FindUser(user_id)
      if balance != prev_balance:
        position = i + 1
        prev_balance = balance
      responses.append('#{}: {:>6} - {}'.format(
          position, util_lib.FormatHypecoins(balance, abbreviate=True),
          user.display_name if user else user_id))
    return responses


NICK_RE = r'(?P<target_user>[a-zA-Z_]\w*)'


# TODO: Make .*++ not handle on dev.
@command_lib.CommandRegexParser(
    r'(?:%s )?(?:gift|give) (?P<target_user>.+) (?P<amount_str>.+?)' %
    _HC_PREFIX)
@command_lib.RegexParser(r'%s(?:\+\+|\s+rocks)(?:[\s,.!?]|$)' % NICK_RE)
@command_lib.RegexParser(r'(?i)gg <3 %s' % NICK_RE)
class HCGiftCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'target_any': True})

  # Normalized recipients that cannot receive gifts accidentally. E.g., c++
  # should not trigger a gift. Can still give them when specified through the
  # CommandRegex (e.g., !hc gift c 1).
  # TODO: The second part of this comment is currently a lie. You can
  # never gift these recipients.
  _UNGIFTABLE = frozenset(['c'])

  @command_lib.HumansOnly('%s does not believe in charity.')
  def _Handle(self,
              channel: channel_pb2.Channel,
              user: user_pb2.User,
              target_user: user_pb2.User = None,
              amount_str: Text = '1') -> hype_types.CommandResponse:
    self._core.last_command = partial(
        self._Handle, target_user=target_user, amount_str=amount_str)

    if user.user_id in coin_lib.HYPECENTS:
      return '%s is not a candy machine.' % user.display_name

    msg_fn = partial(self._Reply, default_channel=channel)
    amount = self._core.bank.ParseAmount(user, amount_str, msg_fn)
    if amount is None:
      return
    if amount <= 0:
      return 'Wow, much gift, so big!'

    normalized_name = target_user.display_name.lower()

    if normalized_name == self._core.name.lower():
      self._Reply(channel, messages.OH_STRING)

    if normalized_name in self._UNGIFTABLE:
      return

    if self._core.bank.ProcessPayment(user, target_user, amount, 'Gift',
                                      msg_fn):
      return (f'{user.display_name} gave {target_user.display_name} '
              f'{util_lib.FormatHypecoins(amount)}')
    else:
      return 'Gift failed. Are you actually scrooge?'


@command_lib.CommandRegexParser(r'%s reset' % _HC_PREFIX)
class HCResetCommand(command_lib.BaseCommand):

  # We ratelimit this to 20h per user to prevent unwise fiscal policies.
  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'ratelimit': {
              'interval': 60 * 60 * 20
          },
          'bailout_amount': 5500
      })

  @command_lib.HumansOnly()
  def _Handle(self, channel: channel_pb2.Channel,
              user: user_pb2.User) -> hype_types.CommandResponse:
    cur_balance = self._core.bank.GetBalance(user)
    if cur_balance > self._params.bailout_amount:
      return ('Surprisingly, I don\'t like to steal hypecoins. '
              'Your balance remains %s') % util_lib.FormatHypecoins(cur_balance)

    bet_potential = 0
    for game in self._core.betting_games:
      game_bets = self._core.bets.LookupBets(game.name, user)
      for bet in game_bets.get(user.user_id, []):
        bet_potential += bet.amount * 2
    if cur_balance + bet_potential > self._params.bailout_amount:
      return 'You have great potential with your current bets.'

    if cur_balance <= 0:
      self._Reply(
          channel,
          f'{user.display_name} has been foolish and unwise with their '
          'HypeCoins.')
    bailout_amount = self._params.bailout_amount - (cur_balance + bet_potential)
    if not self._core.bank.ProcessPayment(
        coin_lib.MINT_ACCOUNT, user, bailout_amount, 'Bailout', self._Reply):
      return messages.HYPECOIN_MINT_EXHAUSTION_STR


@command_lib.CommandRegexParser(
    r'(?:%s )?(?:rob) (?P<target_user>.+) (?P<amount_str>.+?)' % _HC_PREFIX)
@command_lib.RegexParser(r'%s(?:--|\s+sucks)(?:[\s,.!?]|$)' % NICK_RE)
class HCRobCommand(command_lib.BaseCommand):
  """Like taking candy from a baby."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'target_any': True})

  def __init__(self, *args):
    super(HCRobCommand, self).__init__(*args)
    self._robbin_hood = coin_lib.Thievery(self._core.store, self._core.bank,
                                          self._core.name.lower(),
                                          self._core.timezone)

  @command_lib.HumansOnly('%s is not a crook.')
  def _Handle(self,
              channel: channel_pb2.Channel,
              user: user_pb2.User,
              target_user: user_pb2.User = None,
              amount_str: Text = '1') -> hype_types.CommandResponse:
    self._core.last_command = partial(
        self._Handle, target_user=target_user, amount_str=amount_str)

    thief = user
    victim = target_user

    if victim == thief:
      return messages.OH_STRING

    msg_fn = partial(self._Reply, default_channel=channel)
    amount = self._core.bank.ParseAmount(victim, amount_str, msg_fn)
    if amount is None:
      return

    self._robbin_hood.Rob(thief, victim, amount, msg_fn)


@command_lib.CommandRegexParser(
    r'%s t[x|ransaction(?:s)?] ?(?P<target_user>.*)' % _HC_PREFIX)
class HCTransactionsCommand(command_lib.BaseCommand):
  """See the past movement of money."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'target_any': True})

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              target_user: user_pb2.User) -> hype_types.CommandResponse:
    now = arrow.utcnow()
    recent_transactions = self._core.bank.GetTransactions(target_user)
    if not recent_transactions:
      return '%s doesn\'t believe in the HypeCoin economy.' % target_user.display_name

    responses = [
        'Recent HypeCoin Transactions for %s' % target_user.display_name
    ]
    for tx in recent_transactions[:5]:
      amount = util_lib.FormatHypecoins(tx.amount)
      if tx.amount < 0:
        amount = util_lib.Colorize(f'-{amount}', 'red')
        direction = 'to'
      elif tx.amount > 0:
        amount = util_lib.Colorize(f'+{amount}', 'green')
        direction = 'from'
      else:
        amount = amount
        direction = 'with'

      ago = util_lib.TimeDeltaToHumanDuration(
          now - arrow.get(tx.create_time.ToSeconds()))
      responses.append(f'{amount} {direction} {tx.counterparty.display_name} '
                       f'{ago} ago [{tx.details}]')
    return responses
