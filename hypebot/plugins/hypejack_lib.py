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
"""Waste your hard earned hypecoins here."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from functools import wraps
import itertools
import random
import re
import threading

from absl import logging
from hypebot.core import schedule_lib
from hypebot.core import util_lib
from hypebot.plugins import playing_cards_lib
from hypebot.plugins import vegas_game_lib
from hypebot.protos import bet_pb2
from hypebot.protos import user_pb2
from typing import Dict, List, Optional, Text

# Double deck to allow people to count cards.
_NUM_DECKS = 2

# Maps card values to all of their potential points.
_CARD_POINTS = {
    playing_cards_lib.ACE: [1, 11],
    2: [2],
    3: [3],
    4: [4],
    5: [5],
    6: [6],
    7: [7],
    8: [8],
    9: [9],
    10: [10],
    playing_cards_lib.JACK: [10],
    playing_cards_lib.QUEEN: [10],
    playing_cards_lib.KING: [10],
}


class Hand(object):
  """Collection of cards with blackjack game state."""

  def __init__(self, bet, *cards):
    self.bet = bet  # type: bet_pb2.Bet
    self.cards = list(cards)  # type: List[playing_cards_lib.Card]
    self.stand = False

  def IsActive(self):
    return not (self.IsBusted() or self.IsHypeJack() or self.stand)

  def IsBusted(self):
    return self.Score() > 21

  def IsHypeJack(self):
    return self.Score() == 21 and len(self.cards) == 2

  def Score(self):
    """Computes the best possible score for the hand."""
    points = _CARD_POINTS[self.cards[0].value]
    for card in self.cards[1:]:
      points = [
          pts[0] + pts[1]
          for pts in itertools.product(points, _CARD_POINTS[card.value])
      ]

    non_bust = [p for p in points if p <= 21]
    if non_bust:
      score = max(non_bust)
      if score == 21:
        self.stand = True
      return score
    return min(points)

  def __unicode__(self):
    status_str = ''
    if self.IsBusted():
      status_str = '✕'
    elif self.IsHypeJack():
      status_str = '✪'
    elif self.stand:
      status_str = '✋'
    return '[%s]%s' % (', '.join(map(unicode, self.cards)), status_str)


def HandFromMatch(fn):
  """Wrapper that calls the function with the correct hand.

  Determines what hand was desired based on the following order:
    1) Hand passed directly as hand kwarg.
    2) Corresponding hand based on number specified in match kwarg.

  Args:
    fn: Function to wrap.

  Returns:
    Wrapped function.
  """

  @wraps(fn)
  def Wrapper(self, user: user_pb2.User, *args, **kwargs):
    """Internal wrapper."""
    # pylint: disable=protected-access
    with self._lock:
      if user.user_id not in self._peeps:
        self._msg_fn(
            None, '%s: You are not playing in this round.' % user.display_name)
        return

      if 'hand' in kwargs:
        return fn(self, user, *args, **kwargs)

      # Default to first hand if none specified.
      try:
        hand_id = int(kwargs['match'].groups()[0])
      except Exception:  # pylint: disable=broad-except
        hand_id = 0

      try:
        hand = self._peeps[user.user_id][hand_id]
      except KeyError:
        self._msg_fn(
            None, '%s: Please specify a valid hand: 0 through %d' %
            (user.display_name, len(self._peeps[user.user_id]) - 1))
        return

      if not hand.IsActive():
        self._msg_fn(
            None,
            '%s: Hand %s is already complete.' % (user.display_name, hand_id))
        return

      kwargs['hand'] = hand
      return fn(self, user, *args, **kwargs)
    # pylint: enable=protected-access

  return Wrapper


class Game(vegas_game_lib.GameBase):
  """Blackjack style game."""

  # Seconds after first bet until round starts
  ROUND_DELAY = 5

  # Seconds that users have to complete their hands before they are auto-stood.
  # Prevents a user from betting and walking away.
  MAX_ROUND_LENGTH = 60

  def __init__(self, channel, core, msg_fn):
    # Used for thread safe access to class data.
    self._lock = threading.RLock()

    # Condition variable used to force end the game after a certain amount of
    # time has passed.
    self._game_ender = threading.Condition(lock=self._lock)

    self.channel = channel
    self._core = core
    self._msg_fn = msg_fn

    self._pending_start = False
    self._active_round = False
    self._scheduler = schedule_lib.HypeScheduler()

    # Maps users to their hands for the active round.
    self._peeps = {}  # type: Dict[Text, List[Hand]]
    self._dealer_hand = None  # type: Hand
    self._shoe = []

  # ============================================================================
  # GameBase abstract signature.
  # ============================================================================
  @property
  def name(self):
    return self.channel.name

  # Do not take any bets from random channels. We directly place bets ourselves.
  def TakeBet(self, bet):
    return False

  def FormatBet(self, bet):
    return u'%s %s %s in %s' % (util_lib.FormatHypecoins(
        bet.amount), bet_pb2.Bet.Direction.Name(
            bet.direction).lower(), bet.target, self.name)

  def SettleBets(self, pool, msg_fn, *args, **kwargs):
    with self._lock:
      winners = defaultdict(int)
      users_by_id = {}
      for user_id, user_bets in pool.items():
        if user_id not in self._peeps:
          # This means the game wasn't finished. Either user timed out or prior
          # crash. Hypebot steals the bet either way.
          continue
        users_by_id[user_id] = user_bets[0].user

        for bet in user_bets:
          hand_id = int(bet.target.split('-')[-1])
          hand = self._peeps[user_id][hand_id]

          result_str = 'lost'
          if hand.IsBusted():
            result_str = 'busted'
          elif hand.IsHypeJack():
            if self._dealer_hand.IsHypeJack():
              result_str = 'pushed'
              winners[user_id] += bet.amount
            else:
              result_str = 'hypejack!'
              winners[user_id] += bet.amount * 5 // 2
          elif (self._dealer_hand.IsBusted() or
                hand.Score() > self._dealer_hand.Score()):
            winners[user_id] += bet.amount * 2
            result_str = 'won'
          elif hand.Score() == self._dealer_hand.Score():
            winners[user_id] += bet.amount
            result_str = 'pushed'
          self._msg_fn(
              None,
              '%s: %s %s' % (bet.user.display_name, unicode(hand), result_str))

      return ({
          users_by_id[user_id]: amount for user_id, amount in winners.items()
      }, {}, [])

  # ============================================================================
  # HypeJack logic.
  # ============================================================================
  def HandleMessage(self, user: user_pb2.User, msg: Text):
    with self._lock:
      hand_regex = r' ?([0-9]*)'

      bet_match = re.match(r'^b(?:et)? ([0-9]+)', msg)
      double_match = re.match(r'^d(?:ouble)?%s' % hand_regex, msg)
      hit_match = re.match(r'^h(?:it)?%s' % hand_regex, msg)
      stand_match = re.match(r'^st(?:and)?%s' % hand_regex, msg)
      split_match = re.match(r'^sp(?:lit)?%s' % hand_regex, msg)
      help_match = re.match(r'^h[ae]lp', msg)

      if bet_match:
        self.Bet(user, bet_match)
      elif help_match:
        # Help before hit since they will both match `help`.
        self.Help(user)
      elif double_match:
        self.Double(user, match=double_match)
      elif hit_match:
        self.Hit(user, match=hit_match)
      elif stand_match:
        self.Stand(user, match=stand_match)
      elif split_match:
        self.Split(user, match=split_match)

      self._PossiblyEndRound()

  # ============================================================================
  # User commands.
  # ============================================================================
  def Bet(self, user: user_pb2.User, match):
    with self._lock:
      if self._active_round:
        self._msg_fn(None, '%s: Round is currently active.' % user.display_name)
        return

      amount = self._core.bank.ParseAmount(user,
                                           match.groups()[0], self._msg_fn)

      bet = bet_pb2.Bet(
          user=user,
          amount=amount,
          resolver=self._core.name.lower(),
          direction=bet_pb2.Bet.FOR,
          target='hand-0')

      if not self._core.bets.PlaceBet(self, bet, self._msg_fn):
        return
      self._msg_fn(None, '%s joined the round.' % user.display_name)

      if not self._pending_start:
        self._pending_start = True
        self._msg_fn(None, 'Round starting soon, type "bet [amount]" to join.')
        self._scheduler.InSeconds(self.ROUND_DELAY, self.PlayRound)

  @HandFromMatch
  def Double(self,
             user: user_pb2.User,
             hand: Optional[Hand] = None,
             match=None):
    if not hand:
      return
    with self._lock:
      logging.info('Prior Bet: %s', hand.bet)
      hand.bet.amount *= 2

      if not self._core.bets.PlaceBet(self, hand.bet, self._msg_fn):
        self._msg_fn(None,
                     '%s: Not enough hypecoins to double.' % user.display_name)
        hand.bet.amount /= 2
        return
      self.Hit(user, hand=hand)
      self.Stand(user, hand=hand)
      self._DisplayUser(user)

  def Help(self, user: user_pb2.User):
    lines = """HypeJack bears a strong resemblence to a popular casino game.
Commands:
* bet [amount]: signal intent to play in the round.
* hit [hand_id]: request a card for hand_id.
* stand [hand_id]: wait for dealer and compare hands.
* split [hand_id]: split a hand of same value cards into two hands.
* double [hand_id]: double your bet, take a single hit, and stand.
    """.split('\n')
    self._msg_fn(user, lines)

  @HandFromMatch
  def Hit(self,
          user: user_pb2.User,
          hand: Optional[Hand] = None,
          match=None):
    if not hand:
      return
    with self._lock:
      hand.cards.append(self._shoe.pop())
      self._DisplayUser(user)

  @HandFromMatch
  def Stand(self,
            user: user_pb2.User,
            hand: Optional[Hand] = None,
            match=None):
    if not hand:
      return
    with self._lock:
      hand.stand = True
      self._DisplayUser(user)

  @HandFromMatch
  def Split(self,
            user: user_pb2.User,
            hand: Optional[Hand] = None,
            match=None):
    if not hand:
      return
    with self._lock:
      if (len(hand.cards) != 2 or _CARD_POINTS[hand.cards[0].value] !=
          _CARD_POINTS[hand.cards[1].value]):
        self._msg_fn(
            None, '%s: Can only split 2 equal value cards.' % user.display_name)
        return
      new_bet = bet_pb2.Bet()
      new_bet.CopyFrom(hand.bet)
      new_bet.target = 'hand-%d' % len(self._peeps[user.user_id])
      if not self._core.bets.PlaceBet(self, new_bet, self._msg_fn):
        self._msg_fn(None,
                     '%s: Not enough hypecoins to split.' % user.display_name)
        return
      new_hand = Hand(new_bet, hand.cards.pop())
      self._peeps[user.user_id].append(new_hand)
      self.Hit(user, hand=hand)
      self.Hit(user, hand=new_hand)
      self._DisplayUser(user)

  # ============================================================================
  # Game logic.
  # ============================================================================
  def PlayRound(self):
    """Plays one round of HypeJack with all active players.

    Should be called in a separate thread since it will sleep until the game
    timeout unless woken by all peeps completing their hands.
    """
    with self._lock:
      if self._active_round:
        logging.error('HypeJack game already active.')
        return
      bets = self._core.bets.LookupBets(
          self.name, resolver=self._core.name.lower())
      if not bets:
        logging.error('Attempted to start HypeJack with no players.')
        return

      self._pending_start = False

      # Shuffle the deck when it gets low. We assume a reasonable number of
      # cards needed per player, but with lots of splits / low cards we may
      # still run out of cards to play the hand.
      if len(self._shoe) < (len(self._peeps) + 1) * 7:
        self._ShuffleCards()

      # Deal cards to plebs.
      for user_id, user_bets in bets.items():
        hand = Hand(user_bets[0], self._shoe.pop(), self._shoe.pop())
        self._peeps[user_id] = [hand]
        self._DisplayUser(user_bets[0].user)

      # Deal cards to hypebot.
      self._dealer_hand = Hand(None, self._shoe.pop(), self._shoe.pop())
      # self._dealer_hand = Hand(playing_cards_lib.Card('Hearts', 8),
      # playing_cards_lib.Card('Spades', 8))
      self._msg_fn(None, 'Dealer: [%s, %s]' % (self._dealer_hand.cards[0], '🂠'))

      self._active_round = True

      # Short-circuit game play if the dealer has a hypejack or if all peeps
      # have hypejacks.
      if not self._dealer_hand.IsHypeJack() and any(
          [self._IsActive(user_id) for user_id in self._peeps.keys()]):
        # Force the round to end after some time if some peep ran away. Waiting
        # on a condition releases the lock while waiting, then reacquires it
        # automatically. Will shortcircuit if notified when all peeps have
        # finished their hands.
        self._game_ender.wait(timeout=self.MAX_ROUND_LENGTH)

      # Complete dealer hand.
      self._msg_fn(None, 'Dealer: %s' % self._dealer_hand)
      while self._dealer_hand.Score() < 17:
        self._dealer_hand.cards.append(self._shoe.pop())
        self._msg_fn(None, 'Dealer: %s' % self._dealer_hand)

      self._core.bets.SettleBets(self, self._core.name.lower(), self._msg_fn)

      # Reset game state.
      self._peeps = {}
      self._active_round = False

  def _ShuffleCards(self):
    with self._lock:
      self._msg_fn(None, 'Shuffling cards.')
      self._shoe = []
      for _ in range(_NUM_DECKS):
        self._shoe.extend(playing_cards_lib.BuildDeck())
      random.shuffle(self._shoe)

  def _DisplayUser(self, user: user_pb2.User):
    with self._lock:
      if user in self._peeps and len(self._peeps[user.user_id]):
        hands = self._peeps[user.user_id]
        self._msg_fn(
            None, '%s: %s' % (user.display_name, ', '.join([
                '%s:%s' % (i, unicode(hand)) for i, hand in enumerate(hands)
            ])))

  def _IsActive(self, user_id: Text):
    """Check if user has any active hands."""
    with self._lock:
      return (user_id in self._peeps and
              any([hand.IsActive() for hand in self._peeps[user_id]]))

  def _PossiblyEndRound(self):
    """End round if no users are active."""
    with self._lock:
      if all([not self._IsActive(user_id) for user_id in self._peeps.keys()]):
        self._game_ender.notify()
