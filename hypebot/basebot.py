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
"""A basic IRC bot."""

# In general, we want to catch all exceptions, so ignore lint errors for e.g.
# catching Exception
# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from absl import app
from absl import flags
from absl import logging

from hypebot import hypecore
from hypebot.commands import command_factory
from hypebot.core import params_lib
from hypebot.interfaces import interface_factory
from hypebot.plugins import alias_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2
from typing import Text

FLAGS = flags.FLAGS
flags.DEFINE_string('params', None, 'Bot parameter overrides.')


class BaseBot(object):
  """Class for shitposting in IRC."""

  DEFAULT_PARAMS = params_lib.HypeParams({
      # Human readable name to call bot. Will be normalized before most uses.
      'name': 'BaseBot',
      # Chat application interface.
      'interface': {
          'type': 'DiscordInterface'
      },
      # The default channel for announcements and discussion.
      'default_channel': {
          'id': '418098011445395462',
          'name': '#dev'
      },
      # Default time zone for display.
      'time_zone': 'America/Los_Angeles',
      'news': {
          'type': 'NYTimesNews',
      },
      'coffee': {
          'badge_data_path': 'hypebot/data/coffee_badges.textproto',
      },
      'proxy': {
          'type': 'RequestsProxy'
      },
      'storage': {
          'type': 'RedisStore',
          'cached_type': 'ReadCacheRedisStore'
      },
      'stocks': {
          'type': 'IEXStock'
      },
      'weather': {
          'geocode_key': None,
          'darksky_key': None,
          'airnow_key': None,
      },
      'execution_mode': {
          # If this bot is being run for development. Points to non-prod data
          # and changes the command prefix.
          'dev': True,
          # If the bot is running on deployed architecture.
          'deployed': False,
      },
      # List of commands for the bot to create.
      'commands': {
          'AliasAddCommand': {},
          'AliasCloneCommand': {},
          'AliasListCommand': {},
          'AliasRemoveCommand': {},
          'AskFutureCommand': {},
          'AutoReplySnarkCommand': {},
          'BuyHypeStackCommand': {},
          'CoinFlipCommand': {},
          'CookieJarCommand': {},
          'DebugCommand': {},
          'DisappointCommand': {},
          'EchoCommand': {},
          'EnergyCommand': {},
          'GreetingPurchaseCommand': {},
          'GreetingsCommand': {},
          'GrepCommand': {},
          'HypeCommand': {},
          'HypeJackCommand': {},
          'HypeStackBalanceCommand': {},
          'InventoryList': {},
          'InventoryUse': {},
          'JackpotCommand': {},
          'KittiesSalesCommand': {},
          'MemeCommand': {},
          'MissingPingCommand': {},
          'NewsCommand': {},
          'OrRiotCommand': {},
          'PopulationCommand': {},
          'PreferencesCommand': {},
          'PrideAndAccomplishmentCommand': {},
          'RageCommand': {},
          'RatelimitCommand': {},
          'RaiseCommand': {},
          'ReloadCommand': {},
          'RipCommand': {},
          'SameCommand': {},
          'SayCommand': {},
          'ScrabbleCommand': {},
          'SetPreferenceCommand': {},
          'ShruggieCommand': {},
          'SticksCommand': {},
          'StocksCommand': {},
          'StoryCommand': {},
          'SubCommand': {},
          'VersionCommand': {},
          'VirusCommand': {},
          'WebsiteDevelopmentCommand': {},
          'WordCountCommand': {},
          # Hypecoins
          'HCBalanceCommand': {},
          'HCBetCommand': {},
          'HCBetsCommand': {},
          'HCCirculationCommand': {},
          'HCForbesCommand': {},
          'HCGiftCommand': {},
          'HCResetCommand': {},
          'HCRobCommand': {},
          'HCTransactionsCommand': {},
          # HypeCoffee
          'DrinkCoffeeCommand': {},
          'FindCoffeeCommand': {},
          'CoffeeBadgeCommand': {},
          'CoffeeStashCommand': {},
          # Deployment
          'BuildCommand': {},
          'DeployCommand': {},
          'PushCommand': {},
          'SetSchemaCommand': {},
          'TestCommand': {},
          # Interface
          'JoinCommand': {},
          'LeaveCommand': {},
      },
      'subscriptions': {
          'lottery': [{
              'id': '418098011445395462',
              'name': '#dev'
          }],
          'stocks': [{
              'id': '418098011445395462',
              'name': '#dev'
          }],
      },
      'version': '4.20.0',
  })

  def __init__(self, params):
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    if self._params.interface:
      self._params.interface.Override({'name': self._params.name.lower()})
    self._params.Lock()

    # self.interface always maintains the connected interface that is listening
    # for messages. self._core.interface holds the interface desired for
    # outgoing communication. It may be swapped out on the fly, e.g., to handle
    # nested callbacks.
    self.interface = interface_factory.CreateFromParams(self._params.interface)
    self._InitCore()
    self.interface.RegisterHandlers(self.HandleMessage, self._core.user_tracker,
                                    self._core.user_prefs)

    # TODO: Factory built code change listener.

    self._commands = [
        command_factory.Create(name, params, self._core)
        for name, params in self._params.commands.AsDict().items()
        if params not in (None, False)
    ]

  def _InitCore(self):
    """Initialize hypecore.

    Broken out from __init__ so that subclasses can ensure the core is
    initialized before dependent things (e.g., commands) are constructed.

    We define initialization as the instantiation of all objects attached to
    core. However, the objects don't need to be fully loaded.
    """
    self._core = hypecore.Core(self._params, self.interface)

  def HandleMessage(self, channel: channel_pb2.Channel, user: user_pb2.User,
                    msg: Text):
    """Handle an incoming message from the interface."""
    self._core.user_tracker.AddUser(user)
    msg = self._ProcessAliases(channel, user, msg)
    msg = self._ProcessNestedCalls(channel, user, msg)

    if channel.visibility == channel_pb2.Channel.PRIVATE:
      # See if someone is confirming/denying a pending request. This must happen
      # before command parsing so that we don't try to resolve a request created
      # in this message (e.g. !stack buy 1)
      if self._core.request_tracker.HasPendingRequest(user):
        self._core.request_tracker.ResolveRequest(user, msg)

    for command in self._commands:
      try:
        sync_reply = command.Handle(channel, user, msg)
        # Note that this does not track commands that result in only:
        #   * async replies
        #   * direct messages to users
        #   * rate limits
        #   * exceptions
        # TODO: Figure out how to do proper activity tracking.
        if sync_reply:
          self._core.activity_tracker.RecordActivity(channel, user,
                                                     command.__class__.__name__)
        self._core.Reply(channel, sync_reply)
      except Exception:
        self._core.Reply(
            user,
            'Exception handling: %s' % msg,
            log=True,
            log_level=logging.ERROR)

    # This must come after message processing for paychecks to work properly.
    self._core.user_tracker.RecordActivity(user, channel)

  def _ProcessAliases(self, unused_channel, user: user_pb2.User, msg: Text):
    return alias_lib.ExpandAliases(self._core.cached_store, user, msg)

  NESTED_PATTERN = re.compile(
      r'\$\(([^\(\)]+'
      # TODO: Actually tokenize input
      # instead of relying on cheap hacks
      r'(?:[^\(\)]*".*?"[^\(\)]*)*)\)')

  def _ProcessNestedCalls(self, channel, user, msg):
    """Evaluate nested commands within $(...)."""
    m = self.NESTED_PATTERN.search(msg)
    while m:
      backup_interface = self._core.interface
      self._core.interface = interface_factory.Create('CaptureInterface', {})

      # Pretend it's Private to avoid ratelimit.
      nested_channel = channel_pb2.Channel(
          id=channel.id,
          visibility=channel_pb2.Channel.PRIVATE,
          name=channel.name)
      self.HandleMessage(nested_channel, user, m.group(1))
      response = self._core.interface.MessageLog()

      msg = msg[:m.start()] + response + msg[m.end():]
      self._core.interface = backup_interface
      m = self.NESTED_PATTERN.search(msg)
    return msg


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')
  bot = BaseBot(FLAGS.params)
  bot.interface.Loop()


if __name__ == '__main__':
  app.run(main)
