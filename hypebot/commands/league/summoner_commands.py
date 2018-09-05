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
"""User/summoner related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial
from typing import List, Text

import arrow

from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import util_lib
from hypebot.data.league import messages
from hypebot.plugins.league import summoner_lib


SUMMONER_REGEX = r'(all)?(?:-(\w+))? (.+)'


class _BaseSummonerCommand(command_lib.BaseCommand):
  """Base class for commands that want to access summoners."""

  _hypebot_message = 'I deserve challenjour!'

  def _MaybeLoadHypebotMessage(self):
    pass

  def _HandleSummoners(self, summoners):
    raise NotImplementedError(
        'Summoner commands must implement _HandleSummoners')

  def _Handle(self, channel, user, smurfs, region, name, *args, **kwargs):
    self._MaybeLoadHypebotMessage()
    name = summoner_lib.NormalizeSummoner(name)
    if name == 'me':
      self._core.last_command = partial(
          self._Handle,
          smurfs=smurfs,
          region=region,
          name=name,
          *args,
          **kwargs)

    if name == 'dave':
      return 'I\'m sorry Dave. I\'m afraid I can\'t do that.'
    elif name == 'hypebot' or name == u'¯\_(ツ)_/¯':  # pylint: disable=anomalous-backslash-in-string
      return self._hypebot_message

    summoners = self._core.summoner_tracker.ParseSummoner(
        user, smurfs, region, name)
    if not summoners:
      return 'Unknown user. http://go/lolsummoners'
    return self._HandleSummoners(summoners, *args, **kwargs)


@command_lib.CommandRegexParser(r'ch[a|u]mp%s:(.+)' % SUMMONER_REGEX)
@command_lib.CommandRegexParser(r'ch[a|u]mp%s \[(.+)\]' % SUMMONER_REGEX)
class ChampCommand(_BaseSummonerCommand):
  """Display champion mastery."""

  _hypebot_message = messages.HYPEBOT_ALL_CHAMPS_STRING

  def _HandleSummoners(self, summoners, champ):
    return [self._core.summoner.ChampMasterySingle(summoner, champ)
            for summoner in summoners]


@command_lib.CommandRegexParser(r'ch[a|u]mps%s' % SUMMONER_REGEX)
class ChampsCommand(_BaseSummonerCommand):
  """Display top champs by mastery."""

  _hypebot_message = messages.HYPEBOT_IS_THE_CHAMP_STRING

  def _HandleSummoners(self, summoners):
    return [self._core.summoner.Champs(summoner) for summoner in summoners]


@command_lib.CommandRegexParser(r'chimps?%s' % SUMMONER_REGEX)
class ChimpsCommand(_BaseSummonerCommand):
  """Display chimp mastery."""

  _hypebot_message = messages.HYPEBOT_IS_THE_CHIMP_STRING

  def _HandleSummoners(self, summoners):
    return [self._core.summoner.Chimps(summoner) for summoner in summoners]


@command_lib.CommandRegexParser(r'who%s' % SUMMONER_REGEX)
class WhoCommand(_BaseSummonerCommand):
  """Display deets about summoner."""

  def _MaybeLoadHypebotMessage(self):
    if self._hypebot_message == _BaseSummonerCommand._hypebot_message:
      self._hypebot_message = self._CreateHypebotMessage()

  def _HandleSummoners(self, summoners):
    responses = []  # type: List[card_lib.ContextCardMessage]
    for summoner in summoners:
      rito_data = self._core.summoner.Who(summoner)
      grumble_data = None
      responses.append(self._SummonerDataToText(rito_data, grumble_data))
    return responses

  def _CreateHypebotMessage(self) -> Text:
    return messages.WHO_IS_HYPEBOT_STRING

  def _SummonerDataToText(self, summoner_data, team_data) -> Text:
    info = summoner_data['summoner']
    if summoner_data['username']:
      info = summoner_data['username'] + ' = ' + info
    extra_info = []
    # Checking is not None because "False" == a loss
    if summoner_data['last_game'].get('win') is not None:
      win = 'W' if summoner_data['last_game']['win'] else 'L'
    else:
      win = '?'
    if summoner_data['last_game'].get('time'):
      now = arrow.now(self._core.timezone)
      delta = now - summoner_data['last_game']['time']
      when = util_lib.TimeDeltaToHumanDuration(delta)
    if summoner_data.get('penta'):
      extra_info.append('PENTAKILL')
    if 'rank' in summoner_data:
      extra_info.append(summoner_data['rank'] + ' (' + summoner_data[
          'region'].upper() + ')')
    if 'champion' in summoner_data['last_game']:
      extra_info.append('%s: %s' %
                        (summoner_data['last_game'].get('type', 'Unknown'),
                         summoner_data['last_game']['champion']))
    if 'fantasy_points' in summoner_data['last_game']:
      extra_info.append('%.1fpts (%s ago, %s)' %
                        (summoner_data['last_game']['fantasy_points'], when,
                         win))
    if extra_info:
      info += ' [' + ', '.join(extra_info) + ']'
    if team_data:
      rank = team_data['team_rank']
      info += ' [(%s) %s, %d%s]' % (team_data['league_abbrev'],
                                    team_data['team_name'], rank,
                                    inflect_lib.Ordinalize(rank))
    return info
