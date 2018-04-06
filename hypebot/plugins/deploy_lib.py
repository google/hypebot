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
"""Allow bots to build and deploy themselves. So like Rapid in ~300 lines."""

# In general, we want to catch all exceptions, so ignore lint errors for e.g.
# catching Exception
# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from concurrent import futures
from typing import Any, List

from hypebot.core import async_lib
from hypebot.plugins import coin_lib


class DeploymentManager(object):
  """Monitors for changes to hypebot, and automatically deploys them to prod."""

  # Maps *bot* names to their deploy configs. This allows for easier addition
  # and makes it clear which bots we know how to act on.
  _BOT_CONFIGS = {
  }

  def __init__(self,
               bot_name: str,
               bookie: coin_lib.Bookie,
               # This dep creates a cycle in the build graph, so just Any it.
               output_util: Any,  # hypecore.OutputUtil
               executor: futures.Executor) -> None:
    self._bot_name = bot_name
    self._bookie = bookie
    self._output_util = output_util
    self._runner = async_lib.AsyncRunner(executor)

  def IsValidBot(self, bot_name: str) -> bool:
    """Returns if bot_name is a bot DeploymentManager can act upon."""
    return bot_name in self._BOT_CONFIGS

  def RequestBuild(self, user: str, cl: int, bot_name: str,
                   channel: str) -> bool:
    """Requests a build of bot_name on behalf of user."""
    self._output_util.Output(channel or user, 'No deploy integration.')
    return True

  def RequestDeploy(self,
                    user: str,
                    cl: int,
                    bot_name: str,
                    schema_list: List[str],
                    channel: str) -> bool:
    """Requests a deploy (test, build, push) of bot_name on behalf of user."""
    self._output_util.Output(channel or user, 'No deploy integration.')
    return True

  def RequestPush(self,
                  user: str,
                  cl: int,
                  bot_name: str,
                  channel: str) -> bool:
    """Requests a push of bot_name on behalf of user."""
    self._output_util.Output(channel or user, 'No deploy integration.')
    return True

  def RequestSchemaUpdate(self, user: str, cl: int, schema_env: str) -> bool:
    """Requests a schema update on behalf of user."""
    self._output_util.Output(channel or user, 'No deploy integration.')
    return True

  def RequestTest(self,
                  user: str,
                  cl: int,
                  bot_name: str,
                  channel: str) -> bool:
    """Requests to run bot_name tests on behalf of user."""
    self._output_util.Output(channel or user, 'No deploy integration.')
    return True

