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
"""Utilities for testing commands.

This file will be a dependency of all tests within hypebot, but will not be
included in the main binary.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from hypebot import basebot
from hypebot import hypecore
from hypebot.core import params_lib
from hypebot.interfaces import interface_factory
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2

TEST_CHANNEL = channel_pb2.Channel(
    id='#test', name='Test', visibility=channel_pb2.Channel.PUBLIC)
TEST_USER = user_pb2.User(user_id='_test', display_name='user')


def ForCommand(command_cls):
  """Decorator to enable setting the command for each test class."""

  def _Internal(test_cls):
    test_cls._command_cls = command_cls
    return test_cls

  return _Internal


class BaseCommandTestCase(unittest.TestCase):

  # Set the default bot params (used by core) to something sane for testing.
  BOT_PARAMS = params_lib.MergeParams(basebot.BaseBot.DEFAULT_PARAMS, {
      'interface': {
          'type': 'CaptureInterface',
      },
      'proxy': {
          # Tests are often run in an environment with no external access, so we
          # provide a fake Proxy.
          'type': 'EmptyProxy',
      },
      'storage': {
          'type': 'MemStore',
          'cached_type': 'MemStore',
      },
      'execution_mode': {
          # This currently sets the command prefix to `!`. We should figure out
          # a better long-term solution for the command prefix though since this
          # can in theory change other behavior within core, but currently
          # should have no other impacts.
          'dev': False,
      },
      'commands': {},
      'subscriptions': {},
  })

  @classmethod
  def setUpClass(cls):
    super(BaseCommandTestCase, cls).setUpClass()
    if not hasattr(cls, '_command_cls'):
      raise AttributeError(
          ('%s is missing command initializer. All BaseCommandTestCases must'
           ' be decorated with @ForCommand and given the command they are'
           ' testing. For example:\n\n@ForCommand(simple_commands.HelpCommand'
           ')\nclass HelpCommandTest(BaseCommandTestCase):\n  ...') %
          cls.__name__)

  def setUp(self):
    super(BaseCommandTestCase, self).setUp()
    self.interface = interface_factory.CreateFromParams(
        self.BOT_PARAMS.interface)
    self.core = hypecore.Core(self.BOT_PARAMS, self.interface)
    # We disable ratelimiting for tests.
    self.command = self._command_cls(
        {
            'ratelimit': {
                'enabled': False
            },
            'target_any': True
        }, self.core)
