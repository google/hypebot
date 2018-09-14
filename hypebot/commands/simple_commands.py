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
"""Simple commands that can be used anywhere."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from datetime import timedelta
from functools import partial
import random
import time

from absl import logging

from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.plugins import vegas_game_lib
from hypebot.protos.channel_pb2 import Channel


@command_lib.CommandRegexParser(r'8ball (.+)')
class AskFutureCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, unused_user, question):
    if not question:
      return 'You must ask a question.'
    return random.choice(messages.BALL_ANSWERS)


@command_lib.CommandRegexParser(r'disappoint (.+?)')
class DisappointCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, son):
    normalized_son = util_lib.CanonicalizeName(son)
    if normalized_son == 'me':
      son = user
    if normalized_son == self._core.nick:
      return '\x01ACTION feels its shame deeply\x01'
    return '%s, I am disappoint.' % son


@command_lib.CommandRegexParser(r'unlock (.+?)')
class PrideAndAccomplishmentCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, unlockable):
    return ('The intent is to provide players with a sense of pride and '
            'accomplishment for unlocking different %s.') % unlockable


@command_lib.CommandRegexParser(r'energy (.+?)')
class EnergyCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, unused_user, energy_target):
    return '༼ つ ◕_◕ ༽つ %s TAKE MY ENERGY ༼ つ ◕_◕ ༽つ' % energy_target


@command_lib.CommandRegexParser(r'jackpot')
class JackpotCommand(command_lib.BaseCommand):
  """Runs a daily Jackpot."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          # Time to settle lottery [hour, minute, second].
          'lottery_time': [12, 0, 0],
          # Warning times in seconds before lottery_time.
          'warnings': [60, 3600],
      })

  def __init__(self, *args):
    super(JackpotCommand, self).__init__(*args)
    self._game = vegas_game_lib.LotteryGame(self._core.bets)
    self._core.betting_games.append(self._game)

    lotto_time = util_lib.ArrowTime(*self._params.lottery_time,
                                    tz=self._core.timezone)
    self._core.scheduler.DailyCallback(
        lotto_time, self._LotteryCallback, _jitter=10)
    for warning_sec in self._params.warnings:
      warning_offset = timedelta(seconds=warning_sec)
      warning_time = lotto_time - warning_offset
      self._core.scheduler.DailyCallback(
          warning_time, self._LotteryWarningCallback, warning_offset,
          _jitter=0)

  @command_lib.MainChannelOnly
  def _Handle(self, channel, unused_user):
    pool = self._core.bets.LookupBets(self._game.name, resolver=self._core.nick)
    jackpot, item = self._game.ComputeCurrentJackpot(pool)
    responses = ['Current jackpot is %s and a(n) %s' % (
        util_lib.FormatHypecoins(jackpot), item.human_name)]
    for bet_user, user_bets in pool.items():
      for bet in user_bets:
        responses.append('- %s, %s' % (bet_user, self._game.FormatBet(bet)))
    return responses

  def _LotteryCallback(self):
    notifications = self._core.bets.SettleBets(
        self._game, self._core.nick, self._Reply)
    if notifications:
      self._core.SendNotification('lottery', notifications)

  def _LotteryWarningCallback(self, remaining=None):
    logging.info('Running lottery warning callback.')
    warning_str = ''
    if remaining is not None:
      warning_str += 'The lottery winner will be drawn in %s! ' % (
          util_lib.TimeDeltaToHumanDuration(remaining))
    pool = self._core.bets.LookupBets(self._game.name, resolver=self._core.nick)
    coins, item = self._game.ComputeCurrentJackpot(pool)
    warning_str += 'Current jackpot is %s and a(n) %s' % (
        util_lib.FormatHypecoins(coins), item.human_name)
    self._core.SendNotification('lottery', warning_str)


@command_lib.CommandRegexParser(r'mains?')
class MainCommand(command_lib.BaseCommand):

  def _Handle(self, channel, user):
    if (channel.visibility == Channel.PRIVATE or
        command_lib.IsMainChannel(channel, self._core.params.main_channels)):
      if channel.id.strip('#') == self._core.nick:
        return 'Of course I\'m a main, this whole place is named after me'
      else:
        return '%s is a main bot for %s' % (
            self._core.params.name, channel.name)


@command_lib.CommandRegexParser(r'(?:dank)?(?:meme)?(?:\s+v)?')
class MemeCommand(command_lib.TextCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.TextCommand.DEFAULT_PARAMS,
      {
          'choices': ['Cake, and grief counseling, will be available at the '
                      'conclusion of the test.'],
      })

  def _Handle(self, *args, **kwargs):
    return super(MemeCommand, self)._Handle(*args, **kwargs)


@command_lib.CommandRegexParser(r'riot (.+)')
class OrRiotCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, or_riot):
    or_riot = util_lib.StripColor(or_riot).upper()
    normalized_riot = util_lib.CanonicalizeName(or_riot)
    if normalized_riot == 'me':
      self._core.last_command = partial(self._Handle, or_riot=or_riot)
      or_riot = user.upper()
    if normalized_riot == self._core.nick:
      return 'ヽ༼ຈلຈ༽ﾉ %s OR HYPE ヽ༼ຈلຈ༽ﾉ' % self._core.nick.upper()
    else:
      return 'ヽ༼ຈل͜ຈ༽ﾉ %s OR RIOT ヽ༼ຈل͜ຈ༽ﾉ' % or_riot


@command_lib.CommandRegexParser(r'rage')
class RageCommand(command_lib.TextCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.TextCommand.DEFAULT_PARAMS,
      {'choices': messages.RAGE_STRINGS})

  @command_lib.MainChannelOnly
  def _Handle(self, *args, **kwargs):
    return super(RageCommand, self)._Handle(*args, **kwargs)


@command_lib.CommandRegexParser(r'ratelimit')
class RatelimitCommand(command_lib.TextCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.TextCommand.DEFAULT_PARAMS,
      {'choices': messages.RATELIMIT_MEMES})

  @command_lib.PrivateOnly
  def _Handle(self, *args, **kwargs):
    return super(RatelimitCommand, self)._Handle(*args, **kwargs)


@command_lib.CommandRegexParser(r'raise (.+)')
class RaiseCommand(command_lib.BaseCommand):
  """Get hyped."""

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, dongs):
    dongs = util_lib.StripColor(dongs)
    normalized_dongs = util_lib.CanonicalizeName(dongs)
    if normalized_dongs == 'me':
      self._core.last_command = partial(self._Handle, dongs=dongs)
      normalized_dongs = user
    if normalized_dongs == self._core.nick:
      return 'Do not raise me, I am but a simple %s' % self._core.params.name
    elif self._core.zombie_manager.GetCorpseForChannel(
        channel) == normalized_dongs:
      return self._core.zombie_manager.AnimateCorpse(channel)
    else:
      return 'ヽ༼ຈل͜ຈ༽ﾉ raise your %s ヽ༼ຈل͜ຈ༽ﾉ' % dongs


@command_lib.CommandRegexParser(r'reload', reply_to_private=False)
class ReloadCommand(command_lib.BaseCommand):
  """Reload core data."""

  # Reloading is expensive, so set a higher limit and make it global.
  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {'ratelimit': {
          'interval': 30,
          'scope': 'GLOBAL'
      }})

  def _Handle(self, channel=None, unused_user=None):
    if self._core.ReloadData():
      # Do not return to ensure 'Completed reload.' comes afterwards.
      self._Reply(channel, 'Reload started, I\'ll let you know when I finish.')
      self._core.runner.OnCompletion(self._Reply, channel, 'Completed reload.')
    else:
      return 'Currently loading.'


@command_lib.CommandRegexParser(r'rip(?: (.+))?')
class RipCommand(command_lib.BaseCommand):
  """Show respects for the dead."""

  RIP_HUMANS = {
      'qtpie': 'memelord',
  }

  def __init__(self, *args):
    super(RipCommand, self).__init__(*args)
    self._normalized_commands = [util_lib.CanonicalizeName(name) for name in
                                 self._core.params.commands.AsDict().keys()]

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, rip_target):
    normalized_rip_target = None
    rip_string = 'Here lies %s, a once-valued %s %s.'
    if rip_target:
      normalized_rip_target = util_lib.CanonicalizeName(rip_target)
      if normalized_rip_target == 'me':
        self._core.last_command = partial(self._Handle, rip_target=rip_target)
        normalized_rip_target = user
      if normalized_rip_target == self._core.nick:
        self._Spook(user)
        normalized_rip_target = user

      if normalized_rip_target in self.RIP_HUMANS:
        rip_vals = (normalized_rip_target, self._core.nick,
                    self.RIP_HUMANS[normalized_rip_target])
      elif self._core.user_tracker.IsHuman(normalized_rip_target):
        if user == normalized_rip_target:
          rip_mod = 'noober'
        else:
          rip_mod = 'minion'
        rip_vals = (normalized_rip_target, self._core.nick, rip_mod)
      elif normalized_rip_target in self._normalized_commands:
        rip_vals = (rip_target, self._core.nick, 'command')
      else:
        rip_string = 'RIP in pepperonis %s, you will be missed.'
        rip_vals = rip_target
    else:
      rip_target, rip_mod = random.choice(list(self.RIP_HUMANS.items()))
      rip_vals = (rip_target, self._core.nick, rip_mod)

    self._core.zombie_manager.NewCorpse(
        channel, normalized_rip_target or rip_target)
    return rip_string % rip_vals


@command_lib.CommandRegexParser(r'2')
@command_lib.CommandRegexParser(r'same')
class SameCommand(command_lib.BaseCommand):

  # Ratelimits n'at are enforced by the called command.
  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {'ratelimit': {
          'enabled': False,
      }})

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user):
    if self._core.last_command:
      return self._core.last_command(channel=channel, user=user)  # pylint: disable=not-callable
    else:
      return 'How can I do what has not been done?'


@command_lib.CommandRegexParser(r'scrab(?:ble)? (.+?)')
class ScrabbleCommand(command_lib.BaseCommand):
  """Quixotry > your silly word."""

  _CHAR_TO_POINTS = {
      'A': 1,
      'B': 3,
      'C': 3,
      'D': 2,
      'E': 1,
      'F': 4,
      'G': 2,
      'H': 4,
      'I': 1,
      'J': 8,
      'K': 5,
      'L': 1,
      'M': 3,
      'N': 1,
      'O': 1,
      'P': 3,
      'Q': 10,
      'R': 1,
      'S': 1,
      'T': 1,
      'U': 1,
      'V': 4,
      'W': 4,
      'X': 8,
      'Y': 4,
      'Z': 10
  }

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user, msg):
    logging.info('Scrabbling: "%s"', msg)
    scrabble_msg = ''.join(msg.upper().split())
    if not all(c in self._CHAR_TO_POINTS for c in scrabble_msg):
      return 'Silly human, you can\'t play %s in scrabble.' % msg
    scrabble_score = sum(self._CHAR_TO_POINTS[c] for c in scrabble_msg)
    return '%s is worth %s' % (msg, inflect_lib.Plural(scrabble_score, 'point'))


@command_lib.RegexParser(r'¯\\_\(ツ\)_/¯')
@command_lib.CommandRegexParser(r'shrug(?:gie)?')
class ShruggieCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, unused_user):
    return r'¯\ˍ(ツ)ˍ/¯'


@command_lib.CommandRegexParser(r'sticks?')
class SticksCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self, channel, user):
    stick_description = messages.SPECIAL_STICK_USERS.get(user, 'stick')
    action_msg = '%s bangs two %ss together.' % (user, stick_description)
    result_msg = 'It\'s not very effective.'
    if self._core.zombie_manager.ChannelHasActiveCorpse(channel):
      corpse_name = self._core.zombie_manager.GetCorpseForChannel(channel)
      action_msg = '%s knocks zombie %s over the head with a %s.' % (
          user, corpse_name, stick_description)
      result_msg = 'It\'s super effective!'
      self._core.zombie_manager.RemoveCorpse(channel)
    self._Reply(channel, action_msg)
    self._core.scheduler.InSeconds(2, self._Reply, channel, result_msg)


_StoryProgress = namedtuple('_StoryProgress', ('name', 'time', 'line'))


@command_lib.PublicParser
class StoryCommand(command_lib.BasePublicCommand):
  """Story time with Uncle HypeBot."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS,
      {
          # Each story is a series of lines, alternating between hypebot and any
          # user. The user may also say 'tell me more' to advance.
          # This param is left as a dict so overrides can only replace existing
          # stories or add new ones.
          'stories': {
              # The default story tells the creation of hypebot.
              'hypebot': [
                  'In the beginning, the hypebot was created.',
                  'what happened next?',
                  'HypeBot created dank memes.'
              ],
          },
          # Amount of time that user has to respond in order to progress story.
          'timeout_sec': 30,
          # Phrases the user can say in case they don't know their line.
          'continue_msgs': [
              'tell me more',
              '...',
          ],
      })

  def __init__(self, *args):
    super(StoryCommand, self).__init__(*args)
    self._stories = self._params.stories.AsDict()
    self._probs = []
    # Store active story keyed on channel id.
    self._active_stories = {}

  def _Handle(self, channel, user, message):
    message = message.lower()
    t = time.time()
    story = self._active_stories.get(channel.id)
    if story and t - story.time > self._params.timeout_sec:
      del self._active_stories[channel.id]
      story = None
    if story and (message == self._stories[story.name][story.line] or
                  message in self._params.continue_msgs):
      if story.line + 2 < len(self._stories[story.name]):
        self._active_stories[channel.id] = _StoryProgress(
            story.name, t, story.line + 2)
      else:
        del self._active_stories[channel.id]
      return self._stories[story.name][story.line + 1]
    elif not story and message == '%s, tell me a story' % self._core.nick:
      story_name = util_lib.GetWeightedChoice(list(self._stories.keys()),
                                              self._probs)
      self._active_stories[channel.id] = _StoryProgress(story_name, t, 1)
      return self._stories[story_name][0]


@command_lib.CommandRegexParser(r'version')
class VersionCommand(command_lib.BaseCommand):

  def _Handle(self, channel, unused_user):
    return '%s(c) Version %s. #%sVersionHype' % (
        self._core.params.name,
        self._core.params.version,
        self._core.params.name)
