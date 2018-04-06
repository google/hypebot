"""Tests for util_lib."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import arrow
import mock

import util_lib


class UtilLibTest(unittest.TestCase):

  def testArrowTime(self):
    midnight_in_utc = util_lib.ArrowTime()
    raw_arrow_time = arrow.utcnow().replace(hour=0, minute=0, second=0,
                                            microsecond=0)
    self.assertEqual(raw_arrow_time, midnight_in_utc)

    est = 'US/Eastern'
    noon_in_est = util_lib.ArrowTime(12, 0, 0, est)
    raw_arrow_time = arrow.now(est).replace(hour=12, minute=0, second=0,
                                            microsecond=0)
    self.assertEqual(raw_arrow_time, noon_in_est)

    afternoon_in_local = util_lib.ArrowTime(16, tz='local')
    raw_arrow_time = arrow.now().replace(hour=16, minute=0, second=0,
                                         microsecond=0)
    self.assertEqual(raw_arrow_time, afternoon_in_local)

    morning_in_local = util_lib.ArrowTime(8, tz='local')
    morning_tomorrow = arrow.now().shift(days=1)
    morning_tomorrow = morning_tomorrow.replace(hour=8, minute=0, second=0,
                                                microsecond=0)
    self.assertNotEqual(morning_tomorrow, morning_in_local)

  @mock.patch('random.random')
  def testGetWeightedChoice(self, random_call):
    random_call.return_value = 0.25
    memes = ['ayyy', 'lmao', 'rito pls', 'who needs a test?']
    prob_table = []

    meme = util_lib.GetWeightedChoice(memes, prob_table)

    expected = [0.3125, 0.0625, 0.3125, 0.3125]

    self.assertEqual(expected, prob_table)
    self.assertEqual('lmao', meme)

    meme = util_lib.GetWeightedChoice(memes, prob_table)

    expected = [0.078125, 0.140625, 0.390625, 0.390625]

    self.assertEqual(expected, prob_table)
    self.assertEqual('ayyy', meme)

  def testFuzzyBool(self):
    for truthy_value in ('True', ' true', '1', 'ok', 'any_thing  ', 1, True):
      self.assertTrue(util_lib.FuzzyBool(truthy_value))

    for falsey_value in ('', '  falSe', '0', 'NO  ', 0, False):
      self.assertFalse(util_lib.FuzzyBool(falsey_value))


if __name__ == '__main__':
  unittest.main()
