# Copyright 2018 The Hypebot Authors. All rights reserved.
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
"""Summoner-related libraries.

Fetches summoner data from Riot API.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from absl import logging
import arrow

from hypebot.core import inflect_lib
from hypebot.protos.riot.v4 import constants_pb2
from hypebot.protos.riot.v4 import league_pb2

DEFAULT_REGION = 'na'
GAME_MODES = {
    'ARAM': 'ARAM',
    'ASCENSION': 'Ascension',
    'CLASSIC': {
        constants_pb2.QueueType.BOT_5x5: 'Bots',
        constants_pb2.QueueType.BOT_TT_3x3: 'TT Bots',
        constants_pb2.QueueType.GROUP_FINDER_5x5: 'Team Builder',
        constants_pb2.QueueType.NORMAL_5x5_BLIND: 'Normals',
        constants_pb2.QueueType.NORMAL_5x5_DRAFT: 'Normals',
        constants_pb2.QueueType.NORMAL_3x3: 'TT Normals',
        constants_pb2.QueueType.ONEFORALL_5x5: 'One For All (SR)',
        constants_pb2.QueueType.RANKED_FLEX_SR: 'Flecks',
        constants_pb2.QueueType.RANKED_FLEX_TT: 'TT Flecks',
        constants_pb2.QueueType.RANKED_SOLO_5x5: 'YoloQ',
        constants_pb2.QueueType.TEAM_BUILDER_RANKED_SOLO:
            'YoloQ',  # this is weird
        constants_pb2.QueueType.RANKED_TEAM_3x3: 'Ranked 3s',
        constants_pb2.QueueType.RANKED_TEAM_5x5: 'Ranked 5s',
        constants_pb2.QueueType.TEAM_BUILDER_DRAFT_UNRANKED_5x5: 'Normals',
        constants_pb2.QueueType.URF_5x5: 'URF',
        constants_pb2.QueueType.CLASH: 'CLASH',
    },
    'KINGPORO': 'Poro King',
    'ODIN': 'Dominion',
    'ONEFORALL': 'One For All',
    'SIEGE': 'Nexus Siege',
    'GAMEMODEX': {
        constants_pb2.QueueType.NEXUS_BLITZ: 'Blitz',
    },
}


def NormalizeSummoner(input_text):
  return ''.join(input_text.split()).lower()


class SummonerLib(object):
  """Class for fetching various data from Riot API."""

  def __init__(self, rito, game):
    self._rito = rito
    self._game = game

  def _GetMatchParticipant(self, encrypted_account_id, match_ref, match):
    participant_ids = [
        p.participant_id
        for p in match.participant_identities
        if p.player.current_account_id == encrypted_account_id
    ]
    participant = None
    if participant_ids:
      [participant] = [
          p for p in match.participants
          if p.participant_id == participant_ids[0]
      ]
      return participant
    participants = [
        p for p in match.participants if p.champion_id == match_ref.champion
    ]
    if participants:
      # Best guess, which is wrong for blind pick and one-for-all game types.
      # Rito is full of filthy casuals.
      return participants[0]

  def Who(self, summoner):
    """Gets and formats data for a summoner."""
    summoner_data = {}
    game_data = {}

    # Populate basic data (username, summoner name, region)
    summoner_data['username'] = summoner['username']
    summoner_data['summoner'] = summoner['summoner']
    region = summoner.get('region', DEFAULT_REGION)
    summoner_data['region'] = region

    encrypted_summoner_id = summoner.get('encrypted_summoner_id', '')
    encrypted_account_id = summoner.get('encrypted_account_id', '')

    r = self._rito.GetSummoner(region, summoner['summoner'])
    if r:
      summoner_data['profile_icon_id'] = r.profile_icon_id

    r = self._rito.ListRecentMatches(region, encrypted_account_id)
    last_game_ref = None
    last_game = None
    participant = None
    if r:
      last_game_ref = r.matches[0]
      last_game = self._rito.GetMatch(region, last_game_ref.game_id)
      if last_game:
        participant = self._GetMatchParticipant(encrypted_account_id,
                                                last_game_ref, last_game)

    if last_game_ref and last_game and participant:
      # Champion played
      champion_id = participant.champion_id
      game_data['champion'] = self._game.champion_id_to_name[str(champion_id)]

      # Game type
      logging.info('Evaluating (%s, %s)', last_game.game_mode,
                   last_game.game_type)
      game_type = GAME_MODES.get(last_game.game_mode)
      if last_game.game_mode == 'CLASSIC':
        game_type = game_type.get(last_game.queue_id)
      game_data['type'] = game_type or 'Unknown'

      # Game time
      # It seems rito api returns games in US/Pacific time, but this could
      # change at any point in the future.
      logging.info('SummonerLib: gametime: %s', last_game_ref.timestamp)
      game_data['time'] = arrow.get(last_game_ref.timestamp /
                                    1000.0).to('US/Pacific')

      # Other data (win/loss, fantasy points, penta)
      game_data['win'] = participant.stats.win
      game_data['fantasy_points'] = self._ComputeFantasyPoints(
          participant.stats)
      summoner_data['penta'] = participant.stats.penta_kills > 0
    summoner_data['last_game'] = game_data

    # Find dynamic queue rank
    rank = None
    r = self._rito.ListLeaguePositions(region, encrypted_summoner_id)
    if r:
      leagues = r.positions
      for league in leagues:
        if league.queue_type == constants_pb2.QueueType.RANKED_SOLO_5x5:
          tier = constants_pb2.Tier.Enum.Name(league.tier)[0].upper()
          division = self._RomanToLatin(
              league_pb2.TierRank.Enum.Name(league.rank))
          rank = tier + division
    if not rank:
      rank = 'Unranked'
    summoner_data['rank'] = rank

    return summoner_data

  def Champs(self, summoner):
    """Gets and formats champion mastery data for summoner."""
    encrypted_summoner_id = summoner.get('encrypted_summoner_id', '')
    region = summoner.get('region', DEFAULT_REGION)
    r = self._rito.ListChampionMasteries(region, encrypted_summoner_id)
    if r:
      logging.info('Got champ mastery data for %s/%s [%s]', region,
                   encrypted_summoner_id, summoner['summoner'])
      # Calculate total number of chests received
      total_chests = sum(1 for x in r.champion_masteries if x.chest_granted)

      top_champs = []
      for champ in r.champion_masteries[:3]:
        top_champs.append(self._game.champion_id_to_name[str(
            champ.champion_id)])
      top_champ_lvl = r.champion_masteries[0].champion_level

      chest_verb = ''
      chest_verb_dict = {
          (0, 2): 'receiving',
          (2, 4): 'collecting',
          (4, 8): 'earning',
          (8, 16): 'amassing',
          (16, 32): 'hoarding'
      }
      for range_spec, verb in chest_verb_dict.items():
        if total_chests in range(*range_spec):
          chest_verb = verb
          break

      if chest_verb:
        chest_str = '%s %s' % (chest_verb,
                               inflect_lib.Plural(total_chests, 'chest'))
      else:
        chest_str = 'with a boatload of chests (%d)' % total_chests

      return (u'{0} is a L{1} {2[0]} main, but sometimes likes to play {2[1]} '
              'and {2[2]}, {3} this season.').format(summoner['summoner'],
                                                     top_champ_lvl, top_champs,
                                                     chest_str)

  def ChampMasterySingle(self, summoner, champ_name):
    """Gets and formats champion mastery for summoner and specific champ."""
    # Get the champ ID.
    champ_id = self._game.GetChampId(champ_name)
    if champ_id is None:
      return 'Champion "%s" not found.' % champ_name
    champ_display_name = self._game.GetChampDisplayName(champ_name)

    encrypted_summoner_id = summoner.get('encrypted_summoner_id', '')
    region = summoner.get('region', DEFAULT_REGION)
    r = self._rito.GetChampionMastery(region, encrypted_summoner_id, champ_id)
    if r:
      logging.info('Got single champ mastery data for %s/%s [%s] on Champ %s',
                   region, encrypted_summoner_id, summoner['summoner'],
                   champ_display_name)
      champ_level = r.champion_level
      points = r.champion_points
      return ('%s is a L%d %s player with %d mastery points.' %
              (summoner['summoner'], champ_level, champ_display_name, points))
    else:
      logging.info(
          'Got chimp mastery data for %s/%s [%s] on Champ %s (no data)', region,
          encrypted_summoner_id, summoner['summoner'], champ_display_name)
      return '%s does not play %s.' % (summoner['summoner'], champ_display_name)

  def Chimps(self, summoner):
    """Gets and formats Chimp mastery data for summoner."""
    encrypted_summoner_id = summoner.get('encrypted_summoner_id', '')
    region = summoner.get('region', DEFAULT_REGION)
    # Wukong is Champ ID 62
    r = self._rito.GetChampionMastery(region, encrypted_summoner_id, 62)
    if r:
      logging.info('Got chimp mastery data for %s/%s [%s]', region,
                   encrypted_summoner_id, summoner['summoner'])
      champ_level = r.champion_level
      points = r.champion_points
      return ('%s is a L%d Wukong player with %d mastery points.' %
              (summoner['summoner'], champ_level, points))
    else:
      logging.info('Got chimp mastery data for %s/%s [%s] (no data)', region,
                   encrypted_summoner_id, summoner['summoner'])
      return '%s is not a fan of monkeys.' % summoner['summoner']

  def _ComputeFantasyPoints(self, stats):
    """Calculates the number of fantasy points recieved in a game."""
    point_mapping = {
        'kills': 2,
        'deaths': -0.5,
        'assists': 1.5,
        'triple_kills': 2,
        'quadra_kills': 5,
        'penta_kills': 10,
        'neutral_minions_killed': 0.01,
        'total_minions_killed': 0.01
    }
    points = 0
    for stat in point_mapping:
      points += point_mapping[stat] * getattr(stats, stat)
    if max(stats.assists, stats.kills) > 10:
      points += 2
    return points

  def _RomanToLatin(self, roman_numerals):
    """Translates a str roman numeral (I to V) into the latin equivalent."""
    roman = roman_numerals.strip().upper()
    return {'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5'}[roman]


class SummonerTracker(object):
  """Tracks summoners."""

  def __init__(self, rito, user_prefs):
    self._rito = rito
    self._user_prefs = user_prefs

  def ParseSummoner(self, user, smurfs, region, name):
    """Parses a summoner(s) out of mangled garbage the user supplied as input.

    Args:
      user: The user which triggered this parsing. Converts 'me'.
      smurfs: Whether to include smurfs.
      region: If any/not default.
      name: summoner or special string (e.g., 'me').

    Returns:
      A list of summoner_info dicts with the following fields:
        - username: Unused for now
        - summoner: The parsed summoner name
        - encrypted_summoner_id: The encrypted rito summoner id, which is useful
            for other API calls
        - encrypted_account_id: The encrypted rito account id, which is useful
            for other API calls
        - encrypted_puuid: The encrypted rito PUUID, which is useful for other
            API calls
        - region: The given or inferred region for which this summoner is valid
    """
    region = (region or self._user_prefs.Get(user, 'lol_region')).lower()

    if name == 'me':
      names = self._user_prefs.Get(user, 'lol_summoner')
      if not names:
        return []
    else:
      names = self._user_prefs.Get(name, 'lol_summoner') or name
    names = [NormalizeSummoner(name) for name in names.split(',')]
    if smurfs is None:
      names = names[:1]

    summoners = []
    for name in names:
      r = self._rito.GetSummoner(region, name)
      if r:
        summoners.append({
            'username': None,
            'summoner': r.name,
            'encrypted_summoner_id': r.id,
            'encrypted_account_id': r.account_id,
            'encrypted_puuid': r.puuid,
            'region': region
        })
    return summoners
