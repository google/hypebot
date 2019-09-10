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
"""Library for playing cards."""

from __future__ import unicode_literals

import random

HEARTS = 'Hearts'
DIAMONDS = 'Diamonds'
CLUBS = 'Clubs'
SPADES = 'Spades'

RED = 'red'
BLACK = 'black'

_SUIT_COLORS = {
    SPADES: BLACK,
    CLUBS: BLACK,
    HEARTS: RED,
    DIAMONDS: RED,
}

SUITS = _SUIT_COLORS.keys()

ACE = 1
JACK = 11
QUEEN = 12
KING = 13

VALUES = range(1, 14)


class Card(object):
  """A representation of a playing card."""

  VALUE_STRS = {
      ACE: 'A',
      JACK: 'J',
      QUEEN: 'Q',
      KING: 'K',
  }

  SUIT_STRS = {
      HEARTS: '♡',
      DIAMONDS: '♢',
      CLUBS: '♣',
      SPADES: '♠',
  }

  def __init__(self, suit, value):
    self.suit = suit
    self.value = value
    self.color = _SUIT_COLORS[suit]

  def __unicode__(self):
    return '%s%s' % (self.VALUE_STRS.get(self.value, self.value),
                     self.SUIT_STRS[self.suit])

  def IsFacecard(self):
    """Returns true if the card is a jack, queen, or king."""
    return self.value > 10


def BuildDeck():
  """Builds a single deck of 52 cards in random order."""
  cards = []
  for suit in SUITS:
    for value in VALUES:
      cards.append(Card(suit, value))
  random.shuffle(cards)
  return cards
