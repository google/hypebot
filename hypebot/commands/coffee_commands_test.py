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
from hypebot.protos import message_pb2
from hypebot.protos import user_pb2


class BaseCoffeeCommandTestCase(hypetest.BaseCommandTestCase):

  def setUp(self):
    super(BaseCoffeeCommandTestCase, self).setUp()
    self.test_user = user_pb2.User(user_id='test-user', display_name='Tester')
    self.test_badge = coffee_pb2.Badge(
        id=0, name='Test Badge', description='This is for being a good tester.')
    self.test_data = coffee_pb2.CoffeeData(
        energy=10,
        beans=[
            coffee_pb2.Bean(variety='Robusta', region='Brazil', rarity='rare'),
            coffee_pb2.Bean(
                variety='Arabica', region='Honduras', rarity='common'),
            coffee_pb2.Bean(
                variety='Liberica', region='Nicaragua', rarity='legendary')
        ],
        badges=[self.test_badge.id])
    self.core.coffee._SetCoffeeData(self.test_user, self.test_data)
    # TODO: Figure out how to load badge textproto in third_party.
    self.core.coffee.badges = {self.test_badge.id: self.test_badge}

  def _GetStats(self, user):
    return self.core.coffee.GetCoffeeData(user).statistics


@hypetest.ForCommand(coffee_commands.CoffeeBadgeCommand)
class BadgeCommandTest(BaseCoffeeCommandTestCase):

  def test_no_badges(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee b')

    self.assertIsInstance(response, message_pb2.Card)
    self.assertEqual(
        response.fields[0].text,
        coffee_commands.NO_BADGES_MESSAGE % hypetest.TEST_USER.display_name)

  def test_badges_visible(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee badges %s' % self.test_user.user_id)

    self.assertIsInstance(response, message_pb2.Card)
    self.assertEqual(response.visible_fields_count, 5)
    self.assertRegex(response.fields[0].text, self.test_badge.name)


@hypetest.ForCommand(coffee_commands.DrinkCoffeeCommand)
class DrinkCommandTest(BaseCoffeeCommandTestCase):

  def test_no_coffee_to_drink(self):
    initial_drink_count = self._GetStats(hypetest.TEST_USER).drink_count

    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee d')

    cur_drink_count = self._GetStats(hypetest.TEST_USER).drink_count
    self.assertEqual(cur_drink_count, initial_drink_count)
    self.assertEqual(response, coffee_commands.OUT_OF_COFFEE_MESSAGE)

  def test_drinking_bad_id_returns_error_msg(self):
    bad_id = 'Potato'
    initial_drink_count = self._GetStats(hypetest.TEST_USER).drink_count
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee d %s' % bad_id)

    self.assertEqual(response, coffee_commands.UNOWNED_BEAN_MESSAGE % bad_id)
    cur_drink_count = self._GetStats(hypetest.TEST_USER).drink_count
    self.assertEqual(cur_drink_count, initial_drink_count)

  def test_drinking_gives_energy(self):
    initial_energy = self.test_data.energy
    initial_drink_count = self._GetStats(self.test_user).drink_count

    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee drink')

    user_data = self.core.coffee.GetCoffeeData(self.test_user)
    cur_energy = user_data.energy
    self.assertGreater(cur_energy, initial_energy)
    self.assertEqual(user_data.statistics.drink_count, initial_drink_count + 1)
    self.assertRegex(response, r'%d' % (cur_energy - initial_energy))

  def test_drinking_prefix_id_matches_and_consumes(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee drink cah')

    self.assertRegex(response, 'energy')
    user_beans = self.core.coffee.GetCoffeeData(self.test_user).beans
    self.assertNotIn('cahonduras', [b.id for b in user_beans])


@hypetest.ForCommand(coffee_commands.FindCoffeeCommand)
class FindCommandTest(BaseCoffeeCommandTestCase):

  def test_out_of_energy(self):
    initial_find_count = self.test_data.statistics.find_count
    self.core.coffee._SetCoffeeData(self.test_user,
                                    coffee_pb2.CoffeeData(energy=0))

    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee f')

    self.assertEqual(response, coffee_commands.OUT_OF_ENERGY_MESSAGE)
    self.assertEqual(
        self._GetStats(hypetest.TEST_USER).find_count, initial_find_count)

  def test_stash_full_on_find(self):
    initial_find_count = self.test_data.statistics.find_count
    self.core.coffee._SetCoffeeData(
        self.test_user,
        coffee_pb2.CoffeeData(energy=10, beans=[coffee_pb2.Bean(id='f')] * 50))

    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee find')

    self.assertEqual(response, coffee_commands.BEAN_STASH_FULL_MESSAGE)
    self.assertEqual(
        self._GetStats(hypetest.TEST_USER).find_count, initial_find_count)

  @mock.patch.object(random, 'random', lambda: 0.9999)
  def test_could_not_find(self):
    initial_find_count = self._GetStats(hypetest.TEST_USER).find_count
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee f')

    self.assertEqual(response, coffee_commands.FOUND_NO_BEANS_MESSAGE)
    self.assertEqual(
        self._GetStats(hypetest.TEST_USER).find_count, initial_find_count)

  @mock.patch.object(random, 'random', lambda: 0.0001)
  def test_find_any_bean(self):
    initial_find_count = self._GetStats(hypetest.TEST_USER).find_count
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee find')

    user_data = self.core.coffee.GetCoffeeData(hypetest.TEST_USER)
    bean = user_data.beans[-1]
    self.assertEqual(user_data.statistics.find_count, initial_find_count + 1)
    self.assertIsInstance(response, message_pb2.Card)
    self.assertRegex(response.fields[0].text, coffee_commands.FormatBean(bean))


@hypetest.ForCommand(coffee_commands.CoffeeStashCommand)
class StashCommandsTest(BaseCoffeeCommandTestCase):

  def test_empty_stash(self):
    expected_energy = 10
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee')

    self.assertIsInstance(response, message_pb2.Card)
    self.assertRegex(response.header.subtitle, r'%s energy' % expected_energy)

  def test_full_stash_list(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, self.test_user,
                                   '!coffee stash me')

    self.assertIsInstance(response, message_pb2.Card)
    self.assertRegex(response.header.title, self.test_user.display_name)
    status_regex = r'.*'.join(
        (str(self.test_data.energy), str(len(self.test_data.beans)),
         str(len(self.test_data.badges))))
    self.assertRegex(response.header.subtitle, status_regex)
    self.assertGreaterEqual(len(response.fields), len(self.test_data.beans))

    response_str = '\n'.join(f.text for f in response.fields)
    for bean in self.test_data.beans:
      self.assertRegex(response_str, r'(?i)%s' % bean.region)
      self.assertRegex(response_str, r'(?i)%s' % bean.variety)
      self.assertRegex(response_str, r'(?i)%s' % bean.rarity)

  def test_listing_other_stash(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, hypetest.TEST_USER,
                                   '!coffee stash %s' % self.test_user.user_id)

    self.assertIsInstance(response, message_pb2.Card)
    self.assertGreaterEqual(len(response.fields), len(self.test_data.beans))

    response_str = '\n'.join(f.text for f in response.fields)
    for bean in self.test_data.beans:
      self.assertRegex(response_str, r'(?i)%s' % bean.region)
      self.assertRegex(response_str, r'(?i)%s' % bean.variety)
      self.assertRegex(response_str, r'(?i)%s' % bean.rarity)


if __name__ == '__main__':
  unittest.main()
