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
"""Tests for util_lib."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import arrow
import mock

from hypebot.core import util_lib


class UtilLibTest(unittest.TestCase):

  def testUnformatHypecoins(self):
    self.assertEqual(420, util_lib.UnformatHypecoins('420'))
    self.assertEqual(1234, util_lib.UnformatHypecoins('1.234k'))
    self.assertEqual(1000000, util_lib.UnformatHypecoins('1M'))
    self.assertEqual(2500000, util_lib.UnformatHypecoins('2.5M'))

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

  def testFuzzyBool(self):
    for truthy_value in ('True', ' true', '1', 'ok', 'any_thing  ', 1, True):
      self.assertTrue(util_lib.FuzzyBool(truthy_value))

    for falsey_value in ('', '  falSe', '0', 'NO  ', 0, False):
      self.assertFalse(util_lib.FuzzyBool(falsey_value))

  def testExtractRegex_ReturnsNoneWhenNoMatch(self):
    self.assertIsNone(util_lib.ExtractRegex(r'.+', ''))

  def testExtractRegex_MultipleMatchesAreExtracted(self):
    # pytype can't seem to figure out that result isn't None (or isn't None
    # after asserting it isn't anyways). So we just use it directly instead of
    # destructuring the tuple.
    result = util_lib.ExtractRegex(r'[a-z]+', 'mone1234mtwo')
    self.assertIsNotNone(result)
    self.assertEqual(2, len(result[0]))
    self.assertIn('mone', result[0])
    self.assertIn('mtwo', result[0])
    self.assertEqual('1234', result[1])

  def testExtractRegex_NestedCapturesStillRemoveFullRegex(self):
    result = util_lib.ExtractRegex(r'g(.+)', 'Captures with groups')
    self.assertIsNotNone(result)
    self.assertEqual(1, len(result[0]))
    self.assertEqual('roups', result[0][0])
    self.assertEqual('Captures with ', result[1])


class WeightedCollectionTest(unittest.TestCase):

  def testEmptyCollection(self):
    c = util_lib.WeightedCollection([])

    i = c.GetItem()

    self.assertIsNone(i)

  def testSingleItem(self):
    c = util_lib.WeightedCollection(['a'])

    i = c.GetItem()

    self.assertEqual(i, 'a')
    self.assertEqual(c._prob_table[i], 1.0)

  def testInitialProbabilities(self):
    c = util_lib.WeightedCollection(['a', 'b', 'c', 'd'])

    self.assertTrue(all(v == 0.25 for v in c._prob_table.values()))

  @mock.patch('random.random', lambda: 0.4)
  def testGetAndDownweightItem_updatesProbabilities(self):
    choices = ['a', 'b', 'c', 'd']
    c = util_lib.WeightedCollection(choices)
    initial_weight = 1 / len(choices)

    r = c.GetAndDownweightItem()

    self.assertEqual(r, 'b')
    self.assertGreater(c._prob_table['a'], initial_weight)
    self.assertLess(c._prob_table['b'], initial_weight)
    self.assertGreater(c._prob_table['c'], initial_weight)
    self.assertGreater(c._prob_table['d'], initial_weight)
    self.assertAlmostEqual(sum(c._prob_table.values()), 1.0)

  def testModifyWeight_usesUpdateFn(self):
    c = util_lib.WeightedCollection(('one', 'two', 'four'))
    expected_weight = 2 / 3

    new_weight = c.ModifyWeight('four', lambda _: expected_weight)

    self.assertAlmostEqual(new_weight, expected_weight)
    self.assertAlmostEqual(sum(c._prob_table.values()), 1.0)

  def testGetItem_doesNotModifyWeights(self):
    c = util_lib.WeightedCollection(str(x) for x in range(5))

    c.GetItem()
    c.GetItem()

    self.assertTrue(all(v == 0.2 for v in c._prob_table.values()))

  def testInitalWeights_areUsed(self):
    choices = ['a', 'b', 'c', 'd']
    weights = [4, 3, 2, 1]
    total_weight = sum(weights)
    expected_weights = [x / total_weight for x in weights]

    c = util_lib.WeightedCollection(choices, weights)

    self.assertCountEqual(c._prob_table.values(), expected_weights)

  def testInitialWeights_omittedWeightsAreSetToOne(self):
    choices = ['a', 'b', 'c']
    weights = (50, 49)
    expected_weights = (0.5, 0.49, 0.01)

    c = util_lib.WeightedCollection(choices, weights)

    self.assertCountEqual(c._prob_table.values(), expected_weights)


if __name__ == '__main__':
  unittest.main()
