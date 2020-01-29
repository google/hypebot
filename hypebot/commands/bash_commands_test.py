# Copyright 2019 The Hypebot Authors. All rights reserved.
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
"""Tests for bash_commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from hypebot.commands import bash_commands
from hypebot.commands import hypetest


@hypetest.ForCommand(bash_commands.AliasAddCommand)
class AliasCommandsTest(hypetest.BaseCommandTestCase):

  def testAddAlias(self):
    response = self.command.Handle(hypetest.TEST_CHANNEL, 'user',
                                   '!alias add new original')
    self.assertEqual('Added alias new.', response)

    response = self.command.Handle(hypetest.TEST_CHANNEL, 'user',
                                   '!alias add new old')
    self.assertEqual('Updated alias new.', response)


@hypetest.ForCommand(bash_commands.EchoCommand)
class EchoCommandTest(hypetest.BaseCommandTestCase):

  def testRepeatsWhatItsTold(self):
    message = 'Pete and repeat were in a boat, Pete fell out who was left?'
    response = self.command.Handle(hypetest.TEST_CHANNEL, 'testuser',
                                   '!echo %s' % message)

    self.assertEqual([message], response)


if __name__ == '__main__':
  unittest.main()
