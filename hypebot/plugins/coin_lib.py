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
"""Provides bank-like features and other functions for HypeCoins."""

# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import math
import numbers
import random
import re
import threading

from absl import logging
from hypebot.core import schedule_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.protos import bank_pb2
from hypebot.protos import bet_pb2
from hypebot.protos import user_pb2
import six

# pylint: disable=line-too-long
# pylint: enable=line-too-long
from google.protobuf import json_format

# "Accounts" where various transactions end up
BOOKIE_ACCOUNT = user_pb2.User(user_id='_hypebank', display_name='HypeBank')
FEE_ACCOUNT = BOOKIE_ACCOUNT
MINT_ACCOUNT = BOOKIE_ACCOUNT
SCHOLARSHIP_ACCOUNT = user_pb2.User(
    user_id='_hypescholarship', display_name='HypeScholarship')
SUBSCRIPTION_ACCOUNT = BOOKIE_ACCOUNT

# pyformat: disable
HYPECENTS = frozenset([
    BOOKIE_ACCOUNT.user_id,
    FEE_ACCOUNT.user_id,
    MINT_ACCOUNT.user_id,
    SCHOLARSHIP_ACCOUNT.user_id,
    SUBSCRIPTION_ACCOUNT.user_id,
])
# pyformat: enable


class Thievery(object):
  """Allows nefarious behavior.

  The more you steal, the more you get caught. The more you are a victim, the
  more you catch peeps.

  We keep a score which is an exponential decay of the sum of past successful
  theft amounts for victims and thiefs. Your percent of the total score impacts
  future theft chances. Hypebot has a fixed large number in each pool to prevent
  solitary thefts from overloading the system. Periodically, all scores are
  reduced except hypebot's.
  """

  # Rate to decay scores. I.e., score_t+1 = score_t * DECAY_RATE
  _DECAY_RATE = 0.75
  # Arrow object specifying when decay should occur.
  _DECAY_TIME = util_lib.ArrowTime(2)
  # Baseline percentage of victim balance that can be stolen half of the time.
  _BASE_BALANCE_PERCENT = 0.02
  # Fixed thief / victim score for hypebot.
  _HYPEBOT_SCORE = 1000

  def __init__(self, store, bank, bot_name, timezone):
    self._store = store
    self._bank = bank
    self._bot_name = bot_name
    self._protected_peeps = [self._bot_name] + list(HYPECENTS)

    self._scheduler = schedule_lib.HypeScheduler(timezone)
    self._scheduler.DailyCallback(
        # Ensures we schedule this event at 2am local time instead of UTC.
        self._DECAY_TIME.to(timezone),
        self._store.RunInTransaction,
        self._DecayAllScores)

  def Rob(self, thief, victim, amount, msg_fn):
    """Attempt a robbery."""
    if amount < 0:
      msg_fn(None, 'Did you mean !hc gift?')
      return

    if victim.user_id in self._protected_peeps:
      msg_fn(None, 'The Godfather protects his family.')
      self._bank.ProcessPayment(
          thief,
          user_pb2.User(user_id=self._bot_name, display_name=self._bot_name),
          500, 'In Soviet Russia, %s steals from you.' % self._bot_name, msg_fn)
      return

    victim_balance = self._bank.GetBalance(victim)
    if victim_balance <= 0:
      msg_fn(None, 'You cannot milk a dead cow.')
      return

    thief_alert = self._GetPDF('thief')[thief]
    victim_alert = self._GetPDF('victim')[victim]
    offset = self._BASE_BALANCE_PERCENT * (1 - thief_alert - victim_alert)
    failure_chance = self._Sigmoid(amount / victim_balance, offset)

    rob_attempt_score = random.random()

    logging.info('(%s: %0.2f, %s: %0.2f) %s of %s attempt %0.2f >? %0.2f',
                 thief, thief_alert, victim, victim_alert, amount,
                 victim_balance, rob_attempt_score, failure_chance)

    if rob_attempt_score < failure_chance:
      self._bank.ProcessPayment(thief, SCHOLARSHIP_ACCOUNT,
                                min(self._bank.GetBalance(thief), amount),
                                'Victim scholarship fund', msg_fn)
      self._DistributeToPastVictims(msg_fn)
      if (rob_attempt_score < failure_chance * thief_alert /
          (thief_alert + victim_alert + 1e-6)):
        msg_fn(None, '%s is a known thief and was caught.' % thief)
      else:
        msg_fn(None, '%s is on high alert and caught %s.' % (victim, thief))
      return

    # TODO: Fold ProcessPayment into the UpdateScores tx.
    # We don't worry about the victim having insufficient funds since there is a
    # 0% chance of stealing 100% of someone's money.
    if self._bank.ProcessPayment(victim, thief, amount, 'Highway robbery',
                                 msg_fn):
      self._store.RunInTransaction(self._UpdateScores, thief, victim, amount)
      formatted_amount = util_lib.FormatHypecoins(amount)
      msg_fn(None, '%s stole %s from %s' % (thief, formatted_amount, victim))
      # We privmsg the victim to make sure they know who stole their hypecoins.
      msg_fn(victim,
             'You\'ve been robbed! %s stole %s' % (thief, formatted_amount))

  def _Sigmoid(self, value, offset, scale=200.0):
    return 1 / (1 + math.exp(-scale * (value - offset)))

  def _GetScores(self, collection, tx=None):
    """Gets scores for collection.

    Args:
      collection: {string} which set of scores to get.
      tx: {storage_lib.HypeTransaction} an optional transaction to pass along to
        GetJsonValue.

    Returns:
      {dict<string, float>} scores keyed by name.
    """
    scores = self._store.GetJsonValue(self._bot_name, 'scores:%s' % collection,
                                      tx)
    return collections.defaultdict(
        int, scores or {self._bot_name: self._HYPEBOT_SCORE})

  def _GetPDF(self, collection):
    """Gets probability density function of scores for collection."""
    scores = self._GetScores(collection)
    total_score = sum(scores.values())
    pdf = {peep: score / total_score for peep, score in scores.items()}
    return collections.defaultdict(float, pdf)

  def _AddToScore(self, collection, name, amount, tx=None):
    """Add {amount} to {names}'s score in {collection}."""
    scores = self._GetScores(collection, tx)
    scores[name] += amount
    logging.info('Updating %s scores: %s', collection, scores)
    self._store.SetJsonValue(self._bot_name, 'scores:%s' % collection, scores,
                             tx)

  def _UpdateScores(self, thief, victim, amount, tx=None):
    self._AddToScore('thief', thief, amount, tx)
    self._AddToScore('victim', victim, amount, tx)
    return True

  def _DecayAllScores(self, tx=None):
    self._DecayScores('thief', tx)
    self._DecayScores('victim', tx)
    return True

  def _DecayScores(self, collection, tx=None):
    """Decay scores for {collection}."""
    scores = {
        peep: int(score * self._DECAY_RATE)
        for peep, score in self._GetScores(collection, tx).items()
        if score > 0
    }
    scores[self._bot_name] = self._HYPEBOT_SCORE
    logging.info('Updating %s scores: %s', collection, scores)
    self._store.SetJsonValue(self._bot_name, 'scores:%s' % collection, scores,
                             tx)

  def _DistributeToPastVictims(self, msg_fn):
    """Distribute funds in scholarship account to past victims."""
    victim_scores = self._GetPDF('victim')
    scholarship_balance = self._bank.GetBalance(SCHOLARSHIP_ACCOUNT)
    self._bank.ProcessPayment(
        SCHOLARSHIP_ACCOUNT,
        victim_scores.keys(),
        scholarship_balance,
        'Victim scholarship fund',
        msg_fn,
        merchant_weights=victim_scores.values())


class Bookie(object):
  """Class for managing a betting ledger.

  The data-model used by Bookie is rows mapping to dicts serialized as strings.
  """

  _BET_SUBKEY = 'bets'

  _ledger_lock = threading.RLock()

  def __init__(self, store, bank, inventory):
    self._store = store
    self._bank = bank
    self._inventory = inventory

  def LookupBets(self, game, user: user_pb2.User = None, resolver=None):
    """Returns bets for game, optionally filtered by user or resolver."""
    with self._ledger_lock:
      bets = self._GetBets(game)

    # Filtering is done slightly strangely, but it ensures that the same
    # structure is kept regardless of filtering and that if a filter was given
    # but the game has no matches for that filter, we return an empty dict
    if user:
      user_id = user.user_id
      bets = {user_id: bets[user_id]} if user_id in bets else {}
    if resolver:
      bets = {
          user_id: [bet for bet in user_bets if bet.resolver == resolver
                   ] for user_id, user_bets in bets.items()
      }
      bets = collections.defaultdict(list, bets)

    return bets

  # TODO: PlaceBet needs to be fixed to throw on error.
  def PlaceBet(self, game, bet, msg_fn, more=False):
    """Places a bet for game on behalf of user.

    PlaceBet will withdraw funds from the bank to fund the bet.

    Args:
      game: The game this bet is for.
      bet: Bet proto describing what bet to place.
      msg_fn: {callable(channel, msg)} function to send messages.
      more: A boolean that decides if the bet amount should be added to any
        current bets.

    Returns:
      {boolean} whether bet placing was successful or not.
    """
    return self._store.RunInTransaction(self._PlaceBet, game, bet, more, msg_fn)

  def _PlaceBet(self, game, bet, more, msg_fn, *unused_args, **kwargs):
    """Internal version of PlaceBet to be run with a transaction."""
    bet.game = game.name
    with self._ledger_lock:
      tx = kwargs.get('tx')
      if not tx:
        logging.error('_PlaceBet can only be called with a transaction.')
        return
      bets = self._GetBets(game.name, tx=tx)
      prior_bet = None
      for b in bets[bet.user.user_id]:
        if bet.target == b.target:
          prior_bet = b
          logging.info('%s has a prior_bet for %s:%s => %s', bet.user,
                       game.name, bet.target, prior_bet)
          break

      if more and prior_bet:
        bet.amount += prior_bet.amount
        # Special handling to ensure we don't go overboard for lottery.
        if game.name == 'lottery':
          bet.amount = game.CapBet(bet.user, bet.amount, bet.resolver)

      net_amount = bet.amount - (prior_bet.amount if prior_bet else 0)
      if net_amount < 0:
        msg_fn(bet.user,
               'Money on the table is not yours. Try a higher amount.')
        return False
      if prior_bet:
        details = 'Bet updated. Replaced %s with %s' % (
            game.FormatBet(prior_bet), game.FormatBet(bet))
      else:
        details = 'Bet placed. %s' % game.FormatBet(bet)

      if not self._bank.ProcessPayment(bet.user, BOOKIE_ACCOUNT, net_amount,
                                       details, msg_fn):
        return False
      # We do this after the payment processing so that we don't delete bets if
      # we can't correctly update them
      if prior_bet:
        bets[bet.user.user_id].remove(prior_bet)
      bets[bet.user.user_id].append(bet)
      self._SetBets(game.name, bets, tx=tx)
    return True

  def SettleBets(self, game, resolver, msg_fn, *args, **kwargs):
    """Settles all bets for game, clearing the ledger and paying out winnings.

    Args:
      game: The game to settle bets for.
      resolver: The bot trying to settle bets. Used to filter out bets placed by
        other bots which this bot shouldn't resolve.
      msg_fn: {callable(channel, msg)} function to send user messages.
      *args: Additional positional arguments to pass to settlement_fn.
      **kwargs: Additional keyword arguments to pass to settlement_fn.

    Returns:
      List of messages to send as notifications of settling bets.
    """
    return self._store.RunInTransaction(self._SettleBets, game, resolver,
                                        msg_fn, *args, **kwargs)

  def _SettleBets(self, game, resolver, msg_fn, *args, **kwargs):
    """Internal version of SettleBets to be run with a transaction."""
    with self._ledger_lock:
      tx = kwargs.get('tx')
      if not tx:
        logging.error('_SettleBets can only be called with a transaction.')
        return []
      bets = self._GetBets(game.name, tx)
      if not bets:
        logging.warning('Tried to settle bets for %s, but no bets were found',
                        game.name)
        return []
      # Filter out bets with 'resolver' set and != the current bot
      unresolved_bets = collections.defaultdict(list)
      filtered_bets = collections.defaultdict(list)
      for user_id, user_bets in bets.items():
        for bet in user_bets:
          if not bet.resolver or bet.resolver == resolver:
            filtered_bets[user_id].append(bet)
          else:
            unresolved_bets[user_id].append(bet)

      if not filtered_bets:
        logging.info('No bets found for resolver %s', resolver)
        return []

      winner_info, unused_bets, notifications = game.SettleBets(
          filtered_bets, msg_fn, *args, **kwargs)
      # Merge bets that were filtered out of the pool with bets unused by the
      # game itself. We can't use a raw update here since we need to merge the
      # lists of bets for users with bets in both dicts.
      for user_id, user_bets in unresolved_bets.items():
        if user_id in unused_bets:
          unused_bets[user_id] += user_bets
        else:
          unused_bets[user_id] = user_bets
      self._SetBets(game.name, unused_bets, tx=tx)

    for winner, winnings in winner_info:
      if isinstance(winnings, numbers.Number):
        if not self._bank.ProcessPayment(BOOKIE_ACCOUNT, winner, winnings,
                                         'Gambling payout', msg_fn):
          logging.error('Couldn\'t pay %s %s for winning %s', winner, winnings,
                        game.name)
      else:
        self._inventory.AddItem(winner, winnings)
    return notifications

  def _GetBets(self, row, tx=None):
    json_bets = self._store.GetJsonValue(row, self._BET_SUBKEY, tx) or {}
    bets = {
        u: [json_format.ParseDict(b, bet_pb2.Bet()) for b in user_bets
           ] for u, user_bets in json_bets.items()
    }
    return collections.defaultdict(list, bets)

  def _SetBets(self, row, bets, tx=None):
    json_bets = {
        u: [json_format.MessageToDict(b) for b in user_bets
           ] for u, user_bets in bets.items()
    }
    return self._store.SetJsonValue(row, self._BET_SUBKEY, json_bets, tx=tx)


# TODO: Allow holds on accounts to ensure coins will exist for a
# ProcessPayment in the near future.
class Bank(object):
  """Class for managing user balances of hypecoins in the HypeBank."""

  _BALANCE_SUBKEY = 'bank:balance'
  _TRANSACTION_SUBKEY = 'bank:transaction'

  _MIN_OVERDRAFT_FEE = 5
  _MAX_OVERDRAFT_FEE_PERCENT = 0.05

  # Bank class also might want a way to determine if a user has a balance or not

  def __init__(self, store, bot_name):
    self._store = store
    self._bot_name = bot_name
    self._withdraw_lock = threading.RLock()

  def GetBalance(self, user):
    balance = self._store.GetValue(user.user_id, self._BALANCE_SUBKEY)
    if not balance:
      return 0
    return util_lib.SafeCast(balance, int, 0)

  def GetUserBalances(self, plebs_only=False):
    """Returns dict of user_ids mapping to their balance for all users."""
    user_balances = self._store.GetSubkey(self._BALANCE_SUBKEY)
    # pylint: disable=g-complex-comprehension
    return {
        user_id: util_lib.SafeCast(balance, int, 0)
        for user_id, balance in user_balances
        if (not plebs_only or user_id not in HYPECENTS) and
        not user_id.startswith('http')
    }
    # pylint: enable=g-complex-comprehension

  def GetTransactions(self, user):
    json_entries = self._store.GetHistoricalValues(user.user_id,
                                                   self._TRANSACTION_SUBKEY, 5)
    return [
        json_format.ParseDict(entry, bank_pb2.LedgerEntry())
        for entry in json_entries
    ]

  def GetBankStats(self, plebs_only=False):
    """Returns the total number of accounts and the sum of all balances."""
    user_balances = self.GetUserBalances(plebs_only=plebs_only)
    balance_sum = sum(user_balances.values())
    return len(user_balances), balance_sum

  def MintNewHypeCoins(self):
    """Creates new HypeCoins if MINT_ACCOUNT is running low.

    Specifically, if the MINT_ACCOUNT has less than 25% of the total HypeCoin
    market size, this method will mint new coins scaling linearly with the
    number of users, and logarithmically with the total market size.
    """
    mint_balance = self.GetBalance(MINT_ACCOUNT)
    num_users, coins_in_circulation = self.GetBankStats()
    if mint_balance >= coins_in_circulation // 4:
      logging.info(
          'Mint balance (%s) >= 25%% of market (%s), not minting new coins',
          util_lib.FormatHypecoins(mint_balance),
          util_lib.FormatHypecoins(coins_in_circulation))
      return

    num_coins_to_mint = max(
        5000, int(math.log(coins_in_circulation, 2) * num_users * 1000))
    logging.info('Minting %s', util_lib.FormatHypecoins(num_coins_to_mint))
    entry = bank_pb2.LedgerEntry(
        counterparty={
            'user_id': '_ether',
            'display_name': 'Ether'
        },
        amount=num_coins_to_mint,
        details='Minting')
    entry.create_time.GetCurrentTime()
    if not self._Deposit(MINT_ACCOUNT, num_coins_to_mint, entry, None):
      logging.error('Minting %s failed',
                    util_lib.FormatHypecoins(num_coins_to_mint))

  def ParseAmount(self, user, amount_str, msg_fn):
    """Read user's minds.

    Convert a string into an amount of hypecoins.

    Args:
      user: {string} user name.
      amount_str: {string} amount as string.
      msg_fn: {callable(channel, msg)} function to send messages.

    Returns:
      {Optional[int]} Amount as int or None if it can't be parsed.
    """

    # Parser handlers.
    # Can return either an int value or a string. Strings will be replied to the
    # user and replaced with a None value.
    def _IntAmount(match, unused_balance):
      return int(match.groups()[0])

    def _HumanIntAmount(match, unused_balance):
      try:
        return int(util_lib.UnformatHypecoins(match.groups()[0]))
      except ValueError:
        return None

    def _HexAmount(match, unused_balance):
      return int(match.groups()[0], 16)

    def _RandomBalance(unused_match, balance):
      return random.randint(1, balance)

    def _MemeTeam(unused_match, unused_balance):
      # TODO: Determine a way to trigger commands at will.
      # self.Meme(channel, None, None)
      return 'ayyy'

    # List of [regex, parser handler].
    parsers = (
        (r'%s$' % self._bot_name,
         lambda x, y: 'You can\'t put a price on this bot.'),
        (r'(dank)? ?memes?$', _MemeTeam),
        (r'(-?[0-9]+)$', _IntAmount),
        (r'(?:0x)?([0-9,a-f]+)$', _HexAmount),
        (r'(a )?positive int$', _RandomBalance),
        (r'(-?[0-9.]+ ?[A-Za-z]+)$', _HumanIntAmount),
    )

    balance = self.GetBalance(user)
    amount_str = amount_str.lower().strip()

    if amount_str in messages.GAMBLE_STRINGS:
      return balance

    amount = None
    for parser in parsers:
      match = re.match(parser[0], amount_str)
      if match:
        amount = parser[1](match, balance)
        break

    if amount is None:
      amount = 'Unrecognized amount.'

    if isinstance(amount, six.string_types):
      msg_fn(None, amount)
      amount = None

    return amount

  def FineUser(self, user, amount, details, msg_fn):
    return self.ProcessPayment(
        user,
        BOOKIE_ACCOUNT,
        amount,
        'Fine: %s' % details,
        msg_fn,
        can_overdraft=True)

  def ProcessPayment(self,
                     customer,
                     merchants,
                     num_coins,
                     details,
                     msg_fn,
                     can_overdraft=False,
                     merchant_weights=None):
    """Process payment from customer to merchant.

    The merchant will only be paid if the customer has the funds.

    Args:
      customer: {User} name of account to withdraw money.
      merchants: {User or list<User>} name(s) of account(s) to deposit money.
      num_coins: {int} number of hypecoins to transfer.
      details: {string} details of transaction.
      msg_fn: {callable(channel, msg)} function to send messages.
      can_overdraft: {boolean} whether it is possible to overdraft the account.
        If True, the account balance can go negative and no fees will be
        charged. If False, the transaction will fail and an overdraft fee will
        be assessed if there are insufficient funds for the transaction.
      merchant_weights: {list<float>} Weight of num_coins that each merchant
        will receive. Defaults to all 1's.

    Returns:
      {boolean} whether payment was successful.
    """
    if num_coins < 0:
      logging.error('ProcessPayment called with negative value: %s, %s -> %s',
                    num_coins, customer, merchants)
      return False
    if isinstance(merchants, user_pb2.User):
      merchants = [merchants]
    if merchant_weights is None:
      merchant_weights = [1] * len(merchants)
    total_weight = sum(merchant_weights)
    merchant_weights = [w / total_weight for w in merchant_weights]

    amount_paid = 0
    success = True
    for i, (merchant, weight) in enumerate(zip(merchants, merchant_weights)):
      # Ensure we don't overpay due to rounding.
      merchant_amount = min(
          int(round(num_coins * weight)), num_coins - amount_paid)
      # Give the last person the extra coin to compensate for them losing a coin
      # sometimes.
      if i == len(merchants) - 1:
        merchant_amount = num_coins - amount_paid
      if merchant_amount > 0:
        withdrawl_entry = bank_pb2.LedgerEntry(
            details=details, counterparty=merchant)
        withdrawl_entry.create_time.GetCurrentTime()
        deposit_entry = bank_pb2.LedgerEntry(
            details=details,
            counterparty=customer,
            create_time=withdrawl_entry.create_time)
        if (self._Withdraw(customer, merchant_amount, withdrawl_entry, msg_fn,
                           can_overdraft) and
            self._Deposit(merchant, merchant_amount, deposit_entry, msg_fn)):
          amount_paid += merchant_amount
        else:
          success = False
    return success

  def _Deposit(self, user: user_pb2.User, num_coins: int,
               entry: bank_pb2.LedgerEntry, msg_fn) -> bool:
    """Adds num_coins to user's balance.

    Args:
      user: User of account into which to deposit.
      num_coins: Number of hype coins to deposit.
      entry: Details of transaction.
      msg_fn: {callable(channel, msg)} function to send messages.

    Returns:
      Whether deposit was successful.
    """
    if num_coins < 0:
      logging.error('Deposit called with negative value: %s, %s', user,
                    num_coins)
      return False

    entry.amount = num_coins
    tx_name = 'CREDIT %s %s' % (num_coins, user.user_id)
    self._store.RunInTransaction(
        self._BankTransaction, user, num_coins, entry, tx_name=tx_name)
    if msg_fn:
      msg_fn(
          user, '%s deposited into your account. (%s)' %
          (util_lib.FormatHypecoins(num_coins), entry.details))
    # TODO: Maybe fix returns now that RunInTransaction can throw.
    return True

  def _Withdraw(self,
                user: user_pb2.User,
                num_coins: int,
                entry: bank_pb2.LedgerEntry,
                msg_fn,
                can_overdraft: bool = False) -> bool:
    """Subtracts num_coins from user's balance.

    Args:
      user: User of account from which to withdraw.
      num_coins: Number of hype coins to withdraw.
      entry: Details of transaction.
      msg_fn: {callable(channel, msg)} function to send messages.
      can_overdraft: Whether it is possible to overdraft the account. If True,
        the account balance can go negative and no fees will be charged. If
        False, the transaction will fail and an overdraft fee will be assessed
        if there are insufficient funds for the transaction.

    Returns:
      Whether withdrawal was successful.
    """
    if num_coins < 0:
      logging.error('Withdraw called with negative value: %s, %s', user,
                    num_coins)
      return False
    # TODO: This should really be a transaction.
    with self._withdraw_lock:
      balance = self.GetBalance(user)
      if balance < num_coins and not can_overdraft:
        logging.info('Overdraft: %s, %d > %d', user, num_coins, balance)
        overdraft_fee = max(self._MIN_OVERDRAFT_FEE,
                            int(balance * self._MAX_OVERDRAFT_FEE_PERCENT))
        self.ProcessPayment(
            user,
            FEE_ACCOUNT,
            overdraft_fee,
            'Overdraft fee',
            msg_fn,
            can_overdraft=True)
        return False

      entry.amount = -num_coins
      tx_name = 'DEBIT %s %s' % (num_coins, user.user_id)
      self._store.RunInTransaction(
          self._BankTransaction, user, -num_coins, entry, tx_name=tx_name)
      if msg_fn:
        msg_fn(
            user, '%s withdrawn from your account. (%s)' %
            (util_lib.FormatHypecoins(num_coins), entry.details))
    # TODO: Maybe fix returns now that RunInTransaction can throw.
    return True

  def _BankTransaction(self,
                       user: user_pb2.User,
                       delta: int,
                       entry: bank_pb2.LedgerEntry,
                       tx=None):
    """Executes a hypecoin balance update, storing details in a log."""
    try:
      self._store.UpdateValue(user.user_id, self._BALANCE_SUBKEY, delta, tx)
      self._store.PrependValue(
          user.user_id,
          self._TRANSACTION_SUBKEY,
          json_format.MessageToDict(entry),
          max_length=20,
          tx=tx)
    except Exception as e:
      logging.error('BankTransaction failed: %s', entry)
      raise e
