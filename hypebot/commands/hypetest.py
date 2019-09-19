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

TEST_CHANNEL = channel_pb2.Channel(
    id='#test', name='Test', visibility=channel_pb2.Channel.PUBLIC)


class BaseCommandTestCase(unittest.TestCase):

  # Set the default bot params (used by core) to something sane for testing.
  BOT_PARAMS = params_lib.MergeParams(basebot.BaseBot.DEFAULT_PARAMS, {
      'interface': {
          'type': 'CaptureInterface',
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

  def setUp(self):
    super(BaseCommandTestCase, self).setUp()
    self.interface = interface_factory.CreateFromParams(
        self.BOT_PARAMS.interface)
    self.core = hypecore.Core(self.BOT_PARAMS, self.interface)

