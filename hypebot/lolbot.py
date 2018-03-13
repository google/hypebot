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
"""League of Legends-specific extensions to BaseBot."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial

from absl import app
from absl import flags
from absl import logging

from hypebot import basebot
from hypebot.commands import command_lib
from hypebot.core import params_lib
from hypebot.data.league import messages
from hypebot.plugins import vegas_game_lib
from hypebot.plugins.league import esports_lib
from hypebot.plugins.league import game_lib
from hypebot.plugins.league import items_lib
from hypebot.plugins.league import rito_lib
from hypebot.plugins.league import summoner_lib
from hypebot.plugins.league import trivia_lib
from hypebot.protos.channel_pb2 import Channel

FLAGS = flags.FLAGS


class HypeBot(basebot.BaseBot):
  """Class for increasing hype in a chat application."""

  DEFAULT_PARAMS = params_lib.MergeParams(basebot.BaseBot.DEFAULT_PARAMS, {
      'name': 'HypeBot',
      'riot': {
          'api_address': 'localhost:50051',
          'api_key': '',
      },
      # Channel to announce betting results.
      'lcs_channel': {
          'name': '#lcs',
          'id': '421671076385521664',
      },
      # Where to play trivia.
      'trivia_channels': [
          {'name': '#trivia', 'id': '421675055878242305'}
      ],
      'commands': {
          'StoryCommand': {'stories': {'wtf_poem': messages.POEM}},
          'MemeCommand': {'choices': messages.ALL_MEMES},
          # Summoner commands.
          'ChampCommand': {},
          'ChampsCommand': {},
          'ChimpsCommand': {},
          'WhoCommand': {},
          # eSports commands.
          'BodyCommand': {},
          'LCSLivestreamLinkCommand': {},
          'LCSMatchNotificationCommand': {},
          'LCSPickBanRatesCommand': {},
          'LCSPlayerStatsCommand': {},
          'LCSScheduleCommand': {},
          'LCSStandingsCommand': {},
          'LCSResultsCommand': {},
          'LCSRosterCommand': {},
          'LCSRoosterCommand': {},
          # LoL commands.
          'FreeloCommand': {},
          'ItemCommand': {},
          'LoreCommand': {},
          'PatchNotesCommand': {},
          'SetApiKeyCommand': {},
          'SkillCommand': {},
          'StatsCommand': {},
          'StatsAtCommand': {},
          # Trivia commands.
          'TriviaAddCommand': {},
          'TriviaAnswerCommand': {},
      },
  })

  def __init__(self, params):
    super(HypeBot, self).__init__(params)
    api_key = (self._params.riot.api_key or
               self._core.store.GetValue('api_key', 'key'))
    if not api_key:
      logging.fatal('api_key failed to load')

    self._core.rito = rito_lib.RitoLib(self._core.proxy,
                                       self._params.riot.api_address)
    self._core.rito.api_key = api_key
    self._core.game = game_lib.GameLib(self._core.rito)
    self._core.summoner = summoner_lib.SummonerLib(self._core.rito,
                                                   self._core.game)
    self._core.summoner_tracker = summoner_lib.SummonerTracker(
        self._core.rito)
    self._core.esports = esports_lib.EsportsLib(
        self._core.proxy, self._core.executor, self._core.game,
        self._core.timezone)
    self._core.items = items_lib.ItemsLib(self._core.rito)

    # Trivia can probably be self contained once multiple parsers exist.
    self._core.trivia = trivia_lib.TriviaMaster(self._core.game,
                                                self._OnNewTriviaQuestion,
                                                self._OnTriviaQuestionDone,
                                                self._OnTriviaLeaderboard)
    for chan in self._params.trivia_channels:
      channel = Channel(visibility=Channel.PUBLIC, **chan)
      self._core.trivia.MakeNewChannel(channel)

    self._core.lcs_channel = Channel(visibility=Channel.PUBLIC,
                                     **self._params.lcs_channel.AsDict())
    # Place LCS gambling first, so it beats Stock to taking the game.
    self._lcs_game = vegas_game_lib.LCSGame(self._core.esports)
    self._core.betting_games.insert(0, self._lcs_game)
    # Give _esports a chance at loading before trying to resolve LCS bets
    self._core.scheduler.FixedRate(5 * 60, 30 * 60, self._LCSGameCallback)

  ########################
  ### Trivia callbacks ###
  ########################

  def _OnNewTriviaQuestion(self, channel, question):
    self._core.Reply(channel, question.GetQuestionText())

  def _OnTriviaQuestionDone(self, channel, user, question):
    if user:
      self._core.Reply(channel, '%s got it! Answer was: %s' %
                       (user, question.GetAnswer()))
    else:
      self._core.Reply(channel,
                       'Time\'s up! Answer was: %s' % question.GetAnswer())

  def _OnTriviaLeaderboard(self, channel, leaderboard):
    self._core.Reply(channel, leaderboard.Results())

  ##############################
  ### Private helper methods ###
  ##############################

  @command_lib.RequireReady('_core.esports')
  def _LCSGameCallback(self):
    self._core.esports.UpdateEsportsMatches()
    msg_fn = partial(self._core.Reply, default_channel=self._core.lcs_channel)
    self._core.bets.SettleBets(self._lcs_game, self._core.nick, msg_fn)


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')
  hypebot = HypeBot(FLAGS.params)
  hypebot.interface.Loop()


if __name__ == '__main__':
  app.run(main)

