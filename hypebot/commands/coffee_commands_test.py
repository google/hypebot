# Lint as: python3
# Copyright 2020 The Hypebot Authors. All rights reserved.
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
"""Tests for coffee_commands."""

import random
import unittest
from unittest import mock

from hypebot.commands import coffee_commands
from hypebot.commands import hypetest
from hypebot.protos import coffee_pb2
from hypebot.protos import user_pb2


class BaseCoffeeCommandTestCase(hypetest.BaseCommandTestCase):

  def setUp(self):
    super(BaseCoffeeCommandTestCase, self).setUp()
    self.test_user = user_pb2.User(user_id='test-user', display_name='Tester')
    self.test_data = coffee_pb2.CoffeeData(
        energy=10,
        beans=[
            coffee_pb2.Bean(variety='Robusta', region='Brazil', rarity='rare'),
            coffee_pb2.Bean(
                variety='Arabica', region='Honduras', rarity='common'),
            coffee_pb2.Bean(
                variety='Liberica', region='Nicaragua', rarity='legendary')
        ])
    self.core.coffee._SetCoffeeData(self.test_user, self.test_data)


@hypetest.ForCommand(coffee_commands.DrinkCoffeeCommand)
class DrinkCommandTest(BaseCoffeeCommandTestCase):

  def test_no_coffee_to_drink(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee d')

    self.assertEqual(response, coffee_commands.OUT_OF_COFFEE_MESSAGE)

  def test_drinking_gives_energy(self):
    initial_energy = self.test_data.energy
    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee drink')

    cur_energy = self.core.coffee.GetCoffeeData(self.test_user).energy
    self.assertGreater(cur_energy, initial_energy)
    self.assertRegex(response, r'%d' % (cur_energy - initial_energy))


@hypetest.ForCommand(coffee_commands.FindCoffeeCommand)
class FindCommandTest(BaseCoffeeCommandTestCase):

  def test_out_of_energy(self):
    self.core.coffee._SetCoffeeData(self.test_user,
                                    coffee_pb2.CoffeeData(energy=0))

    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee f')

    self.assertEqual(response, coffee_commands.OUT_OF_ENERGY_MESSAGE)

  def test_stash_full_on_find(self):
    self.core.coffee._SetCoffeeData(
        self.test_user,
        coffee_pb2.CoffeeData(energy=10, beans=[coffee_pb2.Bean()] * 50))

    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee find')

    self.assertEqual(response, coffee_commands.BEAN_STASH_FULL_MESSAGE)

  @mock.patch.object(random, 'random', lambda: 0.9999)
  def test_could_not_find(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee f')

    self.assertEqual(response, coffee_commands.FOUND_NO_BEANS_MESSAGE)

  @mock.patch.object(random, 'random', lambda: 0.0001)
  def test_find_any_bean(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee find')

    bean = self.core.coffee.GetCoffeeData(hypetest.TEST_USER).beans[-1]
    self.assertRegex(response, coffee_commands._FormatBean(bean))


@hypetest.ForCommand(coffee_commands.CoffeeStashCommand)
class StashCommandsTest(BaseCoffeeCommandTestCase):

  def test_empty_stash(self):
    expected_energy = 10
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee')

    self.assertEqual(type(response), list)
    self.assertRegex('\n'.join(response), r'%s energy' % expected_energy)

  def test_full_stash_list(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee stash me')

    self.assertEqual(type(response), list)
    self.assertGreater(len(response), len(self.test_data.beans))

    response_str = '\n'.join(response)
    for bean in self.test_data.beans:
      self.assertRegex(response_str, r'(?i)%s' % bean.region)
      self.assertRegex(response_str, r'(?i)%s' % bean.variety)
      self.assertRegex(response_str, r'(?i)%s' % bean.rarity)

  def test_listing_other_stash(self):
    response = self.command.Handle(
        hypetest.TEST_CHANNEL, hypetest.TEST_USER,
        '!coffee stash %s' % self.test_user.user_id)

    self.assertEqual(type(response), list)
    self.assertGreater(len(response), len(self.test_data.beans))

    response_str = '\n'.join(response)
    for bean in self.test_data.beans:
      self.assertRegex(response_str, r'(?i)%s' % bean.region)
      self.assertRegex(response_str, r'(?i)%s' % bean.variety)
      self.assertRegex(response_str, r'(?i)%s' % bean.rarity)


if __name__ == '__main__':
  unittest.main()
