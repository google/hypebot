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
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data.league import messages
from hypebot.plugins.league import summoner_lib
from hypebot.protos import message_pb2


SUMMONER_REGEX = r'(all)?(?:-(\w+))? (.+)'
_U_GG = 'https://u.gg/lol/profile/{region}1/{summoner}/overview'


class _BaseSummonerCommand(command_lib.BaseCommand):
  """Base class for commands that want to access summoners."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

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
      if name == 'me':
        return 'Unknown user. Try `!set-pref lol_summoner $summoner_name`'
      return 'Unknown user.'
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
      team_data = self._core.esports.Who(summoner)
      responses.append(self._SummonerDataToMessage(rito_data, team_data))
    return responses

  def _CreateHypebotMessage(self) -> Text:
    return messages.WHO_IS_HYPEBOT_STRING

  def _SummonerDataToMessage(self, summoner_data, team_data):
    # Build a custom text response since the default card -> text is a bit
    # verbose.
    text_response = summoner_data['summoner']
    if summoner_data['username']:
      text_response = summoner_data['username'] + ' = ' + text_response
    if 'rank' in summoner_data:
      text_response += ', %s %s' % (
          summoner_data['region'].upper(), summoner_data['rank'])
    card = message_pb2.Card(
        header=message_pb2.Card.Header(
            title=summoner_data['summoner'],
            subtitle='%s %s, %s' %
            (summoner_data['region'].upper(),
             summoner_data.get('rank', 'Unranked'),
             summoner_data.get('username', 'HypeBot Pleb')),
            image={
                'url':
                    self._core.game.GetImageUrl(
                        'profileicon', '%d.png' %
                        summoner_data.get('profile_icon_id', 0))
            }))

    last_game_info = []
    win = '?'
    when = '?'
    # Checking is not None because "False" == a loss
    if summoner_data['last_game'].get('win') is not None:
      win = 'W' if summoner_data['last_game']['win'] else 'L'
    if summoner_data['last_game'].get('time'):
      when = util_lib.TimeDeltaToHumanDuration(
          arrow.now(self._core.timezone) - summoner_data['last_game']['time'])
    if summoner_data.get('penta'):
      last_game_info.append('PENTAKILL')
    if 'champion' in summoner_data['last_game']:
      last_game_info.append('%s: %s' % (summoner_data['last_game'].get(
          'type', 'Unknown'), summoner_data['last_game']['champion']))
    if 'fantasy_points' in summoner_data['last_game']:
      last_game_info.append('%.1fpts (%s ago, %s)' % (
          summoner_data['last_game']['fantasy_points'], when, win))
    if last_game_info:
      text_response += ' [%s]' % ', '.join(last_game_info)
      card.fields.add(title='Last Game', text=', '.join(last_game_info))

    if team_data:
      league = self._core.esports.leagues[team_data.team.league_id]
      team_text = '%s: %d%s' % (
          team_data.team.name, team_data.rank,
          inflect_lib.Ordinalize(team_data.rank))
      card.fields.add(title=league.name, text=team_text)
      text_response += ' [(%s) %s]' % (league.name, team_text)
    if not card.fields:
      card.fields.add(text='A very dedicated player.')

    card.fields.add(
        buttons=[{
            'text': 'u.gg',
            'action_url': _U_GG.format(**summoner_data),
        }])
    return message_pb2.Message(text=[text_response], card=card)
