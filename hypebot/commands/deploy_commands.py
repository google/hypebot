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
"""Commands for deployment."""

from absl import logging
from hypebot import hypecore
from hypebot.commands import command_lib
from hypebot.core import util_lib
from hypebot.protos.channel_pb2 import Channel


def DeployParser(prefix: str):
  """Wrap CommandRegexParser with CL number and bot name.

  Args:
    prefix: Deploy action word.

  Returns:
    Decorator that adds parser to class.
  """
  return command_lib.CommandRegexParser(r'%s(@[0-9]+)? ?(.+)?' % prefix)


class _BaseDeployCommand(command_lib.BaseCommand):
  """Parent class for deploy related commands."""

  def _DeployActionInProgress(self,
                              channel: Channel,
                              bot_name: str = '') -> None:
    msg = ('%s deploy action already in progress.' % bot_name).capitalize()
    # TODO(someone): Add logging ability to Reply. Commands shouldn't use
    # LogAndOutput, it is intended for HBDS.
    self._core.output_util.LogAndOutput(logging.WARN, channel, msg.strip())

  @command_lib.MainChannelOnly
  @command_lib.HumansOnly()
  def _Handle(self,
              channel: Channel,
              user: str,
              raw_cl: str,
              raw_bot: str) -> hypecore.MessageType:
    """Validate and parse raw CL number and bot name."""
    if raw_cl:
      raw_cl = raw_cl.strip('@')
    cl = util_lib.SafeCast(raw_cl, int, -1)

    if raw_bot is None:
      return 'Please supply a bot name to build!'

    bot_name = raw_bot.lower()
    if self._core.deployment_manager.IsValidBot(bot_name):
      return self._HandleParsed(channel, user, cl, bot_name)
    return 'I don\'t recognize %s, sorry.' % bot_name

  def _HandleParsed(self,
                    channel: Channel,
                    user: str,
                    cl: int,
                    bot_name: str) -> hypecore.MessageType:
    raise NotImplementedError('Must implement _HandleParsed.')


@DeployParser('build')
class BuildCommand(_BaseDeployCommand):
  """Issues a build request, from an optional changelist."""

  def _HandleParsed(self,
                    channel: Channel,
                    user: str,
                    cl: int,
                    bot_name: str) -> hypecore.MessageType:
    if self._core.deployment_manager.RequestBuild(user, cl, bot_name, channel):
      return 'Build started, I\'ll let you know when I finish'
    else:
      self._DeployActionInProgress(channel, bot_name)


@DeployParser('deploy')
class DeployCommand(_BaseDeployCommand):
  """Issues a deploy (test/build/push) request on behalf of user."""

  def _HandleParsed(self,
                    channel: Channel,
                    user: str,
                    cl: int,
                    bot_name: str) -> hypecore.MessageType:
    if self._core.deployment_manager.RequestDeploy(user, cl, bot_name, [],
                                                   channel):
      return 'Deploying %s' % bot_name
    else:
      self._DeployActionInProgress(channel, bot_name)


@DeployParser('push')
class PushCommand(_BaseDeployCommand):
  """Issues a reload command."""

  def _HandleParsed(self,
                    channel: Channel,
                    user: str,
                    cl: int,
                    bot_name: str) -> hypecore.MessageType:
    if bot_name == self._core.nick:
      info_str = 'I\'m going to reload myself. The future is now.'
    else:
      info_str = 'Initiating reload for %s.' % bot_name

    if self._core.deployment_manager.RequestPush(user, cl, bot_name, channel):
      return info_str + ' May you forever embrace the dankest of memes!'
    else:
      self._DeployActionInProgress(channel, bot_name)


@command_lib.CommandRegexParser(r'set-schema(@[0-9]+)? (dev|prod)')
class SetSchemaCommand(_BaseDeployCommand):
  """Updates the storage schema if applicable."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: Channel,
              user: str,
              raw_cl: str,
              env: str) -> hypecore.MessageType:
    if raw_cl:
      raw_cl = raw_cl.strip('@')
    cl = util_lib.SafeCast(raw_cl, int, -1)

    if self._core.deployment_manager.RequestSchemaUpdate(user, cl, env.lower()):
      return 'Setting schema for %s storage' % env
    else:
      self._DeployActionInProgress(channel)


@DeployParser('test')
class TestCommand(_BaseDeployCommand):
  """Runs HypeBot tests, fining the change author if they fail."""

  def _HandleParsed(self,
                    channel: Channel,
                    user: str,
                    cl: int,
                    bot_name: str) -> hypecore.MessageType:
    if self._core.deployment_manager.RequestTest(user, cl, bot_name, channel):
      return 'Running tests, I\'ll let you know when they\'re finished'
    else:
      self._DeployActionInProgress(channel, bot_name)

