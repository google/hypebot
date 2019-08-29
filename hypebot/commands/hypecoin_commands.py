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

from absl import logging
import arrow
import six

# pylint: disable=g-bad-import-order
from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.plugins import coin_lib
from hypebot.protos.bet_pb2 import Bet
from hypebot.protos.channel_pb2 import Channel
# pylint: enable=g-bad-import-order

_HC_PREFIX = r'(?:h(?:ype)?c(?:oins?)?|₡)(?:\:(\w+))?'


def _GetUserAccount(user, account):
  """Returns nick:account, stripping previous sub-accounts if they exist."""
  if account:
    return '%s:%s' % (user.split(':')[0], account)
  return user


@command_lib.CommandRegexParser(r'%s balance ?(.+)?' % _HC_PREFIX)
@command_lib.RegexParser(r'()(\S+)\?\?(?:[\s,.!?]|$)')
class HCBalanceCommand(command_lib.BaseCommand):

  def _Handle(self, channel, user, account, balance_user):
    balance_user = balance_user or user
    if balance_user == 'me':
      self._core.last_command = partial(
          self._Handle, account=account, balance_user=balance_user)
      balance_user = user
    balance_user = _GetUserAccount(balance_user, account)

    balance = self._core.bank.GetBalance(balance_user)
    return '%s has %s' % (balance_user, util_lib.FormatHypecoins(balance))


@command_lib.CommandRegexParser(
    r'(?:%s )?bet (.+?)( more)? (on|for|against) (.+?)' % _HC_PREFIX)
class HCBetCommand(command_lib.BaseCommand):

  # Open Q:
  #   How to handle the fact that some bet_target (e.g. ROX) could be valid for
  #   multiple games? Probably have basebot privmsg the user?
  #   Could also have a sytem where different targets will use their own
  #   hypecoins to bid on which one gets to handle the bet.
  #   User could also specify by name, e.g., 'lol', 'stock'.
  @command_lib.HumansOnly()
  def _Handle(self, channel, user, account, amount_str, more_str, direction,
              bet_target):
    if account or coin_lib.IsSubAccount(user):
      return 'Must bet from your main account.'
    if user == self._core.name.lower():
      return '%s doesn\'t meddle in human affairs' % user
    user = _GetUserAccount(user, account)
    msg_fn = partial(self._Reply, default_channel=channel)

    amount = self._core.bank.ParseAmount(user, amount_str, msg_fn)
    if amount is None:
      return

    more = more_str == ' more' or amount_str in messages.GAMBLE_STRINGS
    if direction == 'on':
      direction = 'for'

    bet = Bet(
        user=user,
        amount=amount,
        resolver=self._core.name.lower(),
        direction=Bet.Direction.Value(direction.upper()),
        target=bet_target.lower())
    for game in self._core.betting_games:
      taken = game.TakeBet(bet)
      if taken:
        if isinstance(taken, six.string_types):
          details = '%s Please do not waste my time.' % taken
          self._core.bets.FineUser(user, 1, details, msg_fn)
          return
        if not self._core.bets.PlaceBet(game, bet, msg_fn, more):
          logging.error('Placing bet failed: %s => %s', user, bet)
          return
        return
    details = 'Unknown target for betting. Please do not waste my time.'
    self._core.bets.FineUser(user, 1, details, msg_fn)


@command_lib.CommandRegexParser(r'%s (my)?bets ?(.+)?' % _HC_PREFIX)
class HCBetsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'num_bets': 5})

  def _Handle(self, channel, user, account, me, users_or_games):
    game_names = {g.name.lower(): g for g in self._core.betting_games}
    desired_games = set()
    users = set()
    if me:
      users.add(_GetUserAccount(user, account))
    for user_or_game in (users_or_games or '').split():
      if user_or_game in game_names:
        desired_games.add(game_names[user_or_game])
      elif user_or_game == 'me':
        users.add(_GetUserAccount(user, account))
      else:
        users.add(_GetUserAccount(user_or_game, account))
    query_name = '%s%s%s' % (', '.join(users), ' - '
                             if users and desired_games else '', ', '.join(
                                 [g.name for g in desired_games]))

    # Default behaviors if not specified.
    if not users:
      users = set([None])  # This will allow all users in a LookupBets.
    if not desired_games:
      desired_games = self._core.betting_games

    bets = []
    bet_total = 0
    for game in desired_games:
      for bet_user in users:
        bets_by_user = self._core.bets.LookupBets(game.name, bet_user)
        for u, user_bets in bets_by_user.items():
          if account and not coin_lib.IsSubAccount(u, account):
            continue
          for bet in user_bets:
            if len(users) > 1 or users == set([None]):
              bets.append((bet.amount, '- %s, %s' % (u, game.FormatBet(bet))))
            else:
              bets.append((bet.amount, '- %s' % game.FormatBet(bet)))
            bet_total += bet.amount
    bets.sort(key=lambda bet: bet[0], reverse=True)
    bets = [betstring for _, betstring in bets]

    if not bets:
      query_str = '%s has n' % query_name if query_name else 'N'
      return '%so current bets. Risk aversion is unbecoming' % query_str

    responses = [
        '%s current bets [%s, %s]' % (query_name or 'All',
                                      inflect_lib.Plural(len(bets), 'bet'),
                                      util_lib.FormatHypecoins(bet_total))
    ]
    if (len(bets) > self._params.num_bets and
        channel.visibility == Channel.PUBLIC):
      responses.append(
          'Only showing %d bets, addiction is no joke.' % self._params.num_bets)
      bets = bets[:self._params.num_bets]

    responses.extend(bets)
    return responses


@command_lib.CommandRegexParser(r'%s circ(?:ulation)?' % _HC_PREFIX)
class HCCirculationCommand(command_lib.BaseCommand):

  def _Handle(self, channel, unused_user, account):
    num_users, coins_in_circulation = self._core.bank.GetBankStats(
        plebs_only=True, account=account)
    return ('There is %s circulating among %s.' %
            (util_lib.FormatHypecoins(coins_in_circulation),
             inflect_lib.Plural(num_users, 'pleb')))


@command_lib.CommandRegexParser(r'%s forbes(?: (.+))?' % _HC_PREFIX)
class HCForbesCommand(command_lib.BaseCommand):
  """Display net worth of a single user or the wealthiest peeps."""

  @command_lib.LimitPublicLines()
  def _Handle(self, channel, user, account, forbes_user):
    if forbes_user:
      if forbes_user == 'me':
        self._core.last_command = partial(
            self._Handle, account=account, forbes_user=forbes_user)
        forbes_user = user
      forbes_user = _GetUserAccount(forbes_user, account)
      balance = self._core.bank.GetBalance(forbes_user)
      for game in self._core.betting_games:
        game_bets = self._core.bets.LookupBets(game.name, forbes_user)
        for bet in game_bets.get(forbes_user, []):
          balance += bet.amount
      return ('%s has a net worth of %s' %
              (forbes_user, util_lib.FormatHypecoins(balance, abbreviate=True)))

    # Top 4 plebs by net worth.
    pleb_balances = defaultdict(int)
    pleb_balances.update(
        self._core.bank.GetUserBalances(plebs_only=True, account=account))
    for game in self._core.betting_games:
      game_bets = self._core.bets.LookupBets(game.name)
      for pleb, pleb_bets in game_bets.items():
        if account and not coin_lib.IsSubAccount(pleb, account):
          continue
        for bet in pleb_bets:
          pleb_balances[pleb] += bet.amount
    pleb_balances = sorted(
        [(pleb, balance) for pleb, balance in pleb_balances.items()],
        key=lambda x: x[1],
        reverse=True)

    responses = ['Forbes 4:']
    position = 1
    prev_balance = -1
    for i, (pleb, balance) in enumerate(pleb_balances[:4]):
      if balance != prev_balance:
        position = i + 1
        prev_balance = balance
      responses.append('#{}: {:>6} - {}'.format(
          position, util_lib.FormatHypecoins(balance, abbreviate=True), pleb))
    return responses


NICK_RE = r'()([a-zA-Z_]\w*)'


# TODO: Make .*++ not handle on dev.
@command_lib.CommandRegexParser(
    r'(?:%s )?(?:gift|give) (.+?) (.+?)' % _HC_PREFIX)
@command_lib.RegexParser(r'%s(?:\+\+|\s+rocks)(?:[\s,.!?]|$)' % NICK_RE)
@command_lib.RegexParser(r'(?i)gg <3 %s' % NICK_RE)
class HCGiftCommand(command_lib.BaseCommand):

  # Normalized recipients that cannot receive gifts accidentally. E.g., c++
  # should not trigger a gift. Can still give them when specified through the
  # CommandRegex (e.g., !hc gift c 1).
  # TODO: The second part of this comment is currently a lie. You can
  # never gift these recipients.
  _UNGIFTABLE = frozenset(['c'])

  @command_lib.HumansOnly('%s does not believe in charity.')
  def _Handle(self, channel, user, account, recipient, amount_str='1'):
    if (account or coin_lib.IsSubAccount(user) or
        coin_lib.IsSubAccount(recipient)):
      return 'You cannot gift to/from sub-accounts.'
    self._core.last_command = partial(
        self._Handle,
        account=account,
        recipient=recipient,
        amount_str=amount_str)

    if user in coin_lib.HYPECENTS:
      return '%s is not a candy machine.' % user

    msg_fn = partial(self._Reply, default_channel=channel)
    amount = self._core.bank.ParseAmount(user, amount_str, msg_fn)
    if amount is None:
      return
    if amount <= 0:
      return 'Wow, much gift, so big!'

    normalized_recipient = recipient.lower()

    if normalized_recipient == self._core.name.lower():
      self._Reply(channel, messages.OH_STRING)

    if normalized_recipient in self._UNGIFTABLE:
      return

    if self._core.bank.ProcessPayment(user, recipient, amount, 'Gift', msg_fn):
      return '%s gave %s %s' % (user, recipient,
                                util_lib.FormatHypecoins(amount))
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
  def _Handle(self, channel, user, account):
    if account or coin_lib.IsSubAccount(user):
      return 'You cannot reset sub-accounts.'

    cur_balance = self._core.bank.GetBalance(user)
    if cur_balance > self._params.bailout_amount:
      return ('Surprisingly, I don\'t like to steal hypecoins. '
              'Your balance remains %s') % util_lib.FormatHypecoins(cur_balance)

    bet_potential = 0
    for game in self._core.betting_games:
      game_bets = self._core.bets.LookupBets(game.name, user)
      for bet in game_bets.get(user, []):
        bet_potential += bet.amount * 2
    if cur_balance + bet_potential > self._params.bailout_amount:
      return 'You have great potential with your current bets.'

    if cur_balance <= 0:
      self._Reply(channel,
                  '%s has been foolish and unwise with their HypeCoins.' % user)
    bailout_amount = self._params.bailout_amount - (cur_balance + bet_potential)
    if not self._core.bank.ProcessPayment(
        coin_lib.MINT_ACCOUNT, user, bailout_amount, 'Bailout', self._Reply):
      return messages.HYPECOIN_MINT_EXHAUSTION_STR


@command_lib.CommandRegexParser(r'(?:%s )?(?:rob) (.+?) (.+?)' % _HC_PREFIX)
@command_lib.RegexParser(r'%s(?:--|\s+sucks)(?:[\s,.!?]|$)' % NICK_RE)
class HCRobCommand(command_lib.BaseCommand):

  def __init__(self, *args):
    super(HCRobCommand, self).__init__(*args)
    self._robbin_hood = coin_lib.Thievery(self._core.store, self._core.bank,
                                          self._core.name.lower(),
                                          self._core.timezone)

  @command_lib.HumansOnly('%s is not a crook.')
  def _Handle(self, channel, user, account, victim, amount_str='1'):
    if account or coin_lib.IsSubAccount(user) or coin_lib.IsSubAccount(victim):
      return 'You cannot rob from/to sub-accounts.'
    self._core.last_command = partial(
        self._Handle, account=account, victim=victim, amount_str=amount_str)

    thief = user

    if victim in (thief, 'me'):
      return messages.OH_STRING

    msg_fn = partial(self._Reply, default_channel=channel)
    amount = self._core.bank.ParseAmount(victim, amount_str, msg_fn)
    if amount is None:
      return

    self._robbin_hood.Rob(thief, victim, amount, msg_fn)


@command_lib.CommandRegexParser(r'%s t[x|ransaction(?:s)?] ?(.+)?' % _HC_PREFIX)
class HCTransactionsCommand(command_lib.BaseCommand):

  def _Handle(self, channel, user, account, tx_user):
    tx_user = tx_user or user
    if tx_user == 'me':
      tx_user = user
    tx_user = _GetUserAccount(tx_user, account)
    now = arrow.utcnow()
    recent_transactions = self._core.bank.GetTransactions(tx_user)
    if not recent_transactions:
      return '%s doesn\'t believe in the HypeCoin economy.' % tx_user

    responses = ['Recent HypeCoin Transactions for %s' % tx_user]
    for tx in recent_transactions[:5]:
      if tx_user == tx.get('source'):
        base_tx_description = ' {} to {} %s ago [%s]'.format(
            util_lib.Colorize('-%s', 'red'), tx.get('destination', 'unknown'))
      else:
        base_tx_description = ' {} from {} %s ago [%s]'.format(
            util_lib.Colorize('+%s', 'green'), tx.get('source', 'unknown'))

      time_delta = now - arrow.get(tx.get('ts', now.timestamp))
      time_str = util_lib.TimeDeltaToHumanDuration(
          time_delta) if time_delta else '??'

      tx_description = base_tx_description % (util_lib.FormatHypecoins(
          tx['amount']), time_str, tx.get('details', 'Unknown'))
      responses.append(tx_description)
    return responses
