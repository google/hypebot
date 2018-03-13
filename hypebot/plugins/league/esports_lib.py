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
"""esports_lib fetches LCS and other professional tournament data from Riot."""

# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import Counter
from collections import defaultdict
import copy
import re
from threading import Lock

from absl import logging
import arrow

from hypebot.core import name_complete_lib
from hypebot.core import util_lib
from hypebot.data.league import messages
from hypebot.data.league import nicknames

LIVESTREAM_LINK_FORMAT = 'https://gaming.youtube.com/embed/%s'
PLAYOFF_REGEX = r'(?i).*(playoff|region).*'
REGION_MAP = {
    'NA': {
        'aliases': ['North America'],
        'ids': {
            'na-lcs': {'stats_enabled': True}
        },
        'locale': 'en',
    },
    'EU': {
        'aliases': ['Europe'],
        'ids': {
            'eu-lcs': {'stats_enabled': True}
        },
        'locale': 'en',
    },
    'CN': {
        'aliases': ['LPL', 'China'],
        'ids': {
            # LPL games not in esports API.
            'lpl-china': {'stats_enabled': False}
        }
    },
    'KR': {
        'aliases': ['LCK', 'Korea'],
        'ids': {
            'lck': {'stats_enabled': True}
        },
    },
    'IN': {
        'aliases': [
            'International', 'Worlds', 'All-Star', 'MSI', 'Rift-Rivals'
        ],
        'ids': {
            'worlds': {'stats_enabled': False},
            'all-star': {},
            'msi': {},
            'rift-rivals': {}
        }
    },
}
ESPORTS_API_BASE_URL = 'https://arcturus.cooleyweb.org/esports/'


class EsportsLib(object):
  """Class for fetching various data from Riot API."""

  _load_status = None
  _rosters = {}
  _rosters_lock = Lock()
  _schedule = []
  _schedule_lock = Lock()
  _matches = {}
  _matches_lock = Lock()
  _player_name_completer = None
  _player_name_completer_lock = Lock()
  _standings = set()
  _standings_lock = Lock()
  _teams = {}
  _teams_lock = Lock()

  def __init__(self, proxy, executor, game_lib, rito_tz):
    self._proxy = proxy
    self._executor = executor
    self._game = game_lib
    self._timezone = rito_tz

    # Maintains mappings from champ_key -> per-region stats about picks, etc.
    self._champ_to_stats = defaultdict(lambda: defaultdict(Counter))
    self._champ_to_stats_lock = Lock()
    # Maintains mappings from player_key -> various stats about the player like
    # per-champion wins/picks/etc.
    self._player_to_stats = defaultdict(lambda: defaultdict(Counter))
    self._player_to_stats_lock = Lock()
    # Maintains total number of games played per region
    self._num_games = Counter()
    self._num_games_lock = Lock()
    # Load eSports data in the background on startup so we don't have to wait
    # for years while we fetch the bio of every player in multiple languages
    # once for every API call we make regardless of endpoint.
    self._load_status = self._executor.submit(self.LoadEsports)

  @property
  def champ_to_stats(self):
    return self._champ_to_stats

  @champ_to_stats.setter
  def champ_to_stats(self, value):
    with self._champ_to_stats_lock:
      self._champ_to_stats = value

  @property
  def rosters(self):
    return self._rosters

  @rosters.setter
  def rosters(self, value):
    with self._rosters_lock:
      self._rosters = value

  @property
  def schedule(self):
    return self._schedule

  @schedule.setter
  def schedule(self, value):
    with self._schedule_lock:
      self._schedule = value

  @property
  def matches(self):
    return self._matches

  @matches.setter
  def matches(self, value):
    with self._matches_lock:
      self._matches = value

  @property
  def num_games(self):
    return self._num_games

  @num_games.setter
  def num_games(self, value):
    with self._num_games_lock:
      self._num_games = value

  @property
  def player_name_completer(self):
    return self._player_name_completer

  @player_name_completer.setter
  def player_name_completer(self, value):
    with self._player_name_completer_lock:
      self._player_name_completer = value

  @property
  def player_to_stats(self):
    return self._player_to_stats

  @player_to_stats.setter
  def player_to_stats(self, value):
    with self._player_to_stats_lock:
      self._player_to_stats = value

  @property
  def standings(self):
    return self._standings

  @standings.setter
  def standings(self, value):
    with self._standings_lock:
      self._standings = value

  @property
  def teams(self):
    return self._teams

  @teams.setter
  def teams(self, value):
    with self._teams_lock:
      self._teams = value

  def IsReady(self):
    """Returns if all the dependant data for EsportsLib has been loaded."""
    return self._load_status.done()

  def ReloadData(self):
    self._proxy.FlushCache()
    self._proxy.HTTPFetch(ESPORTS_API_BASE_URL + 'reload')
    self.LoadEsports()

  def LoadEsports(self):
    """Loads teams, schedules, and standings for all regions in REGION_MAP.

    Things are broken down into tournaments, brackets, matches, and games.
      tournaments: Large event, e.g., LCS split, MSI
      brackets: regular_season, playoffs, relegation, gauntlet, group
      matches: Bo#
      games: individual games
    We operate at the match level.
    """
    teams = {}  # keyed on team number.
    rosters = {}  # teams keyed on roster id.
    matches = {}  # matches keyed on match id.
    standings = {}  # ['region']['bracket'] only use most recent tournament.

    # Functions as a "reset" so we don't just accumulate data forever.
    self.champ_to_stats = defaultdict(lambda: defaultdict(Counter))
    self.player_to_stats = defaultdict(lambda: defaultdict(Counter))
    self.num_games = Counter()

    for region in REGION_MAP:
      standings[region] = {}
      for league in REGION_MAP[region]['ids']:
        league_data = self.FetchEsportsData('leagues', league)
        if not league_data or 'leagues' not in league_data:
          continue
        league_id = league_data['leagues'][0]['id']

        for team in league_data['teams']:
          teams[team['id']] = {
              'acronym': team['acronym'],
              'name': team['name'],
              'slug': team['slug'],
          }

        # Find the most recent tournament
        for tournament in self._FindActiveTournaments(
            league_data['highlanderTournaments']):
          logging.info('Pulling esports data from %s for %s/%s',
                       tournament['title'], region, league)
          for roster_id, roster in tournament['rosters'].items():
            if 'team' in roster:
              rosters[roster_id] = teams[int(roster['team'])]
            else:
              # It's a player at All-Stars
              rosters[roster_id] = {
                  'acronym': roster['name'],
                  'name': roster['name'],
              }

          for bracket in tournament['brackets'].values():
            def _ExtractStandings(record, rank=None):
              return {
                  'rank': rank,
                  'team': rosters[record['roster']],
                  'wins': record.get('wins', 0),
                  'losses': record.get('losses', 0),
                  'ties': record.get('ties', 0),
                  'score': record.get('score', 0),
              }

            # Rito was almost nice and gave us the ordering and grouping of
            # teams in bracket['standings'], but it only works for a select few.
            cur_standings = []
            if 'standings' in bracket:
              for group in bracket['standings']['result']:
                rank = len(cur_standings) + 1
                for roster in group:
                  record = ([
                      r for r in league_data['highlanderRecords']
                      if r['tournament'] == tournament['id'] and r['bracket'] ==
                      bracket['id'] and r['roster'] == roster['roster']
                  ] or [None])[0]
                  if record:
                    cur_standings.append(_ExtractStandings(record, rank))
            else:
              cur_standings = [
                  _ExtractStandings(r) for r in league_data['highlanderRecords']
                  if (r['tournament'] == tournament['id'] and r['bracket'] ==
                      bracket['id'])
              ]
              cur_standings.sort(
                  key=lambda x: (x['score'] * 100 + x['wins'] - x['losses']),
                  reverse=True)

            bracket_name = '|'.join((league, bracket['name']))
            standings[region][bracket_name] = cur_standings

            # Find all matches
            for match in bracket['matches'].values():
              bracket_name = '|'.join((tournament['title'], bracket['name']))
              playoff_match = re.match(PLAYOFF_REGEX, bracket_name) or False
              match_teams = self._ExtractMatchTeams(match, rosters)
              if not match_teams:
                continue
              matches[match['id']] = {
                  'id': match['id'],
                  'time': arrow.Arrow.min,
                  'playoffs': playoff_match,
                  'announced': {},
                  'region': region,
                  'bracket': bracket_name,
                  'blue': match_teams[0],
                  'red': match_teams[1],
              }

              # Parse match for pick/ban rates
              if (match['state'].lower() == 'resolved' and
                  REGION_MAP[region]['ids'][league].get('stats_enabled')):
                self._ScrapePickBanData(tournament['id'], region, match)

              # Determine if match has been won.
              if 'standings' in match:
                top_group = match['standings']['result'][0]
                if len(top_group) > 1:
                  winner = 'TIE'
                elif len(top_group) == 1:
                  winner = rosters[top_group[0]['roster']]['acronym']
                else:
                  winner = None
                matches[match['id']]['winner'] = winner

          # Go back and fetch the times for the matches, because rito teases us.
          schedule_data = self.FetchEsportsData('scheduleItems', league_id)
          if not schedule_data or 'scheduleItems' not in schedule_data:
            continue
          for match in schedule_data['scheduleItems']:
            match_id = match.get('match', 0)
            if match_id in matches:
              matches[match_id]['time'] = arrow.get(match['scheduledTime'])

    self.rosters = rosters
    self.schedule = sorted(
        [m for m in matches.values()], key=lambda x: x['time'])
    self.matches = matches
    self.standings = standings
    self.teams = teams
    self.player_name_completer = name_complete_lib.NameComplete(
        nicknames.LCS_PLAYER_NICKNAME_MAP, self.player_to_stats,
        [x['name'] for x in self.player_to_stats.values()])
    logging.info('Loading esports complete')

  def UpdateEsportsMatches(self):
    """Determines if any matches have been wonnered and returns them."""
    updated_matches = []
    updated_regions = set()
    for region in REGION_MAP:
      for league in REGION_MAP[region]['ids']:
        # We bypass the cache to make sure we get the latest results.
        league_data = self.FetchEsportsData('leagues', league, True)
        if not league_data or 'leagues' not in league_data:
          continue

        # Only use the last tournament.
        for tournament in self._FindActiveTournaments(
            league_data['highlanderTournaments']):
          for bracket in tournament['brackets'].values():
            for match in bracket['matches'].values():
              our_match = self.matches.get(match['id'], None)
              # Try to update any previously 'TBD' teams in the match
              if our_match and 'TBD' in (our_match['blue'], our_match['red']):
                match_teams = self._ExtractMatchTeams(match, self.rosters)
                if match_teams:
                  our_match['blue'] = match_teams[0]
                  our_match['red'] = match_teams[1]

              # Determine if match has been won and we didn't know previously.
              if (our_match and 'standings' in match and
                  not our_match.get('winner', None)):
                updated_regions.add(region)
                top_group = match['standings']['result'][0]
                if len(top_group) > 1:
                  winner = 'TIE'
                elif len(top_group) == 1:
                  winner = self.rosters[top_group[0]['roster']]['acronym']
                else:
                  winner = None
                our_match['winner'] = winner
                updated_matches.append(our_match)

    # We reload the esports API here just to make sure we have the latest
    # schedule. Once all data is sourced from there we can remove this as the
    # API server keeps the data fresh internally.
    if updated_regions:
      param_str = '?region=%s' % ','.join(updated_regions)
      self._proxy.HTTPFetch('%s%s%s' % (ESPORTS_API_BASE_URL, 'reload',
                                        param_str))
    return updated_matches

  def GetLivestreamLinks(self, locale='en'):
    """Get links to the livestream(s), if any are currently active.

    Args:
      locale: Restrict to streams in the given language.

    Returns:
      Dict of match_id to link for livestreams.
    """
    data = self.FetchEsportsData('streamgroups', force_lookup=True)
    if not data:
      logging.error('Could not retrieve livestream')
      return {}

    # Build a lookup from stream_id to match that stream is currently showing
    stream_id_to_match = {}
    for s in data['streamgroups']:
      for i in s['streams']:
        # Using get because content is always present but could be empty
        if s.get('content'):
          m_id = s['content'].split('match:')[1]
          stream_id_to_match[i] = m_id

    streams = (x for x in data['streams'] if x['id'] in stream_id_to_match)
    links = {}
    for s in streams:
      if s['provider'] == 'youtube' and s['locale'] == locale:
        try:
          watch_id = re.search(r'youtube.com/embed/([^?&]+)\??',
                               s['embedHTML']).groups()[0]
        except Exception:
          logging.info('Stream in correct locale missing link:\n\t%s', s)
          continue
        links[stream_id_to_match[s['id']]] = LIVESTREAM_LINK_FORMAT % watch_id
    return links

  def GetSchedule(self, subcommand, include_playoffs, num_games=5):
    """Get the schedule for the specified region or team."""
    qualifier = 'All'
    if subcommand in [t['acronym'] for t in self.teams.values()]:
      qualifier = subcommand
    qualifier = self._AliasToRegion(subcommand) or qualifier

    now = arrow.utcnow()
    query_params = {'num_games': num_games, 'include_completed': False}
    schedule_data = self._proxy.FetchJson(
        ESPORTS_API_BASE_URL + 'schedule/%s' % qualifier, query_params)

    schedule = []
    livestream_links = self.GetLivestreamLinks()
    for match in schedule_data.get('matches', []):
      # Parse the match time into an Arrow object. Yay for serialization.
      match['time'] = arrow.get(match['time'])
      if self._MatchIsInteresting(match, qualifier, now, include_playoffs):
        # If the game is in the future, add a livestream link if one exists. If
        # the game is considered live, add either an existing livestream link or
        # the fallback link.
        if match['time'] > now:
          if match['time'] == arrow.Arrow.max:
            # This means rito hasn't scheduled this match yet
            date_time = 'TBD'
          else:
            local_time = match['time'].to(self._timezone)
            date_time = local_time.strftime('%a %m/%d %I:%M%p %Z')
          if match['id'] in livestream_links:
            date_time += ' - %s' % livestream_links[match['id']]
        else:
          date_time = 'LIVE - ' + (livestream_links.get(match['id']) or
                                   messages.FALLBACK_LIVESTREAM_LINK)
        num_games_str = ''
        if match['num_games']:
          num_games_str = 'Bo%s - ' % match['num_games']
        blue_team = util_lib.Colorize('{:3}'.format(match['blue']), 'blue')
        red_team = util_lib.Colorize('{:3}'.format(match['red']), 'red')
        schedule.append('{} v {}: {}{}'.format(blue_team, red_team,
                                               num_games_str, date_time))
        if len(schedule) >= num_games:
          break

    if not schedule:
      schedule = [messages.SCHEDULE_NO_GAMES_STRING]
      qualifier = 'No'
    return schedule[:num_games], qualifier

  def GetResults(self, subcommand, num_games=5):
    """Get the results of past games for the specified region or team."""
    qualifier = 'All'
    is_team = False
    if subcommand in [t['acronym'] for t in self.teams.values()]:
      qualifier = subcommand
      is_team = True
    region_qualifier = self._AliasToRegion(subcommand)
    if region_qualifier:
      qualifier = region_qualifier
      is_team = False

    results = []
    # Shallow copy so we don't actually reverse the schedule
    tmp_schedule = self.schedule[:]
    tmp_schedule.reverse()
    for match in tmp_schedule:
      if self._ResultIsInteresting(match, qualifier):
        blue_team = util_lib.Colorize('{:3}'.format(match['blue']), 'blue')
        red_team = util_lib.Colorize('{:3}'.format(match['red']), 'red')
        is_tie = match['winner'] == 'TIE'
        if is_team:
          winner_msg = 'Won!' if match['winner'] == qualifier else 'Lost'
        else:
          winner_msg = '{} {}'.format(
              match['winner'] if is_tie else util_lib.Colorize(
                  '{:3}'.format(match['winner']),
                  'red' if match['red'] == match['winner'] else 'blue'),
              ':^)' if is_tie else 'wins!')
        results.append('{} v {}: {}'.format(blue_team, red_team, winner_msg))
        if len(results) >= num_games:
          break

    return results[:num_games], qualifier

  def GetStandings(self, req_region, req_brackets):
    """Gets the standings for a specified region."""
    region = self._AliasToRegion(req_region)
    if region:
      if region == 'IN':
        req_brackets.append(req_region)
      req_region = region
    if req_region not in self.standings:
      return []

    standings = []
    for bracket, teams in self.standings[req_region].items():
      if not all([x in bracket.upper() for x in req_brackets]):
        continue
      has_ties = bracket == 'eu-lcs|regular_season'
      human_bracket = bracket.split('|')[-1].replace('_', ' ').title()
      standings.append('%s-%s Standings (%s):' % (req_region, human_bracket,
                                                  'W-T-L' if has_ties else
                                                  'W-L'))
      for team in teams:
        if has_ties:
          standings.append('{:2}: {:3} ({}-{}-{}, {} {})'.format(
              team['rank'], team['team']['acronym'], team['wins'], team['ties'],
              team['losses'], team['score'], 'pt' if team['score'] == 1 else
              'pts'))
        else:
          standings.append('{}{} {} ({}-{})'.format(team[
              'rank'] or '', ':' if team['rank'] else '', team['team'][
                  'acronym'], team['wins'], team['losses']))
    return standings

  def GetRoster(self, team, region, include_subs):
    """Gets roster for specified team."""
    roster = []
    query = util_lib.CanonicalizeName(team)
    slug_to_role = {
        'toplane': 'Top',
        'jungle': 'Jungle',
        'midlane': 'Mid',
        'adcarry': 'ADC',
        'support': 'Support'
    }
    role_ordering = {
        'toplane': 0,
        'jungle': 1,
        'midlane': 2,
        'adcarry': 3,
        'support': 4
    }

    query_params = {}
    if region:
      query_params['region'] = region
    if include_subs:
      query_params['full'] = True
    roster_data = self._proxy.FetchJson(
        ESPORTS_API_BASE_URL + 'roster/%s' % query, query_params)
    if 'error' in roster_data:
      if roster_data.get('ready'):
        logging.warning('Roster service returned an error: %s',
                        roster_data['error'])
        return roster
      return ['Roster data is still loading, try again soon.']
    elif not roster_data:
      logging.error('Could not retrieve roster.')
      return roster

    roster.append('%s %sRoster:' %
                  (util_lib.Access(roster_data, 'team.0.name', query),
                   'Full ' if include_subs else ''))

    # A map of actual player names to what their name should be displayed as.
    # You know, for memes.
    player_name_substitutions = {'Revolta': 'Travolta',
                                 'MikeYeung': 'Mike "Mike Yeung" Yeung'}
    players = []
    sorted_roster_data = sorted(
        roster_data.items(), key=lambda x: role_ordering.get(x[0], -1))
    for position, player_list in sorted_roster_data:
      if position not in slug_to_role:
        continue
      # Make sure we add the starter before any possible subs
      for player in sorted(player_list, key=lambda x: not x['starter']):
        real_name = player['name']
        display_name = player_name_substitutions.get(real_name, real_name)
        player_pair = [display_name, slug_to_role[position]]
        if not player['starter']:
          player_pair[1] += ' (Sub)'
        players.append(player_pair)

    roster.extend([' - '.join(p) for p in players])
    return roster

  def GetChampPickBanRate(self, region, champ):
    """Returns pick/ban data for champ, optionally filtered by region."""
    champ_id = self._game.GetChampId(champ)
    region = self._AliasToRegion(region) or region
    if not champ_id:
      logging.info('%s doesn\'t map to any known champion', champ)
      return None, None
    canonical_name = self._game.GetChampDisplayName(champ)
    pick_ban_data = self.champ_to_stats[champ_id]

    summed_pick_ban_data = Counter()
    for region_data in [v for k, v in pick_ban_data.items() if
                        region in ('all', k)]:
      summed_pick_ban_data.update(region_data)
    summed_pick_ban_data['num_games'] = sum(v for k, v in self.num_games.items()
                                            if region in ('all', k))

    return canonical_name, summed_pick_ban_data

  def GetPlayerChampStats(self, player):
    """Returns champ statistics for LCS player."""
    player_info = self.player_name_completer.GuessThing(player)
    if not player_info:
      logging.info('%s is ambiguous or doesn\'t map to any known player',
                   player)
      return None, None

    player_name = player_info['name']
    player_data = {}
    player_data['champs'] = copy.deepcopy(player_info)
    player_data['num_games'] = copy.deepcopy(player_info['num_games'])
    # Remove non-champ keys from the champ data. This is also why we need the
    # deepcopies above.
    del player_data['champs']['name']
    del player_data['champs']['num_games']
    return player_name, player_data

  def GetTopPickBanChamps(self, region, sort_key_fn, descending=True):
    """Returns the top 5 champions sorted by sort_key_fn for region."""
    region = self._AliasToRegion(region) or region
    champs_to_flattened_data = {}
    for champ_id, region_data in self.champ_to_stats.items():
      champ_name = self._game.GetChampNameFromId(champ_id)
      if not champ_name:
        logging.error('Couldn\'t parse %s into a champ_name', champ_id)
        continue
      champs_to_flattened_data[champ_name] = Counter()
      for r, pb_data in region_data.items():
        if region in ('all', r):
          champs_to_flattened_data[champ_name].update(pb_data)

    num_games = sum(v for k, v in self.num_games.items()
                    if region in ('all', k))

    # First filter out champs who were picked in fewer than 5% of games
    filtered_champs = [
        x for x in champs_to_flattened_data.items()
        if x[1]['picks'] >= (num_games / 20.0)
    ]
    # We sort by the secondary key (picks) first
    sorted_champs = sorted(
        filtered_champs, key=lambda x: x[1]['picks'], reverse=True)

    sorted_champs.sort(key=lambda x: sort_key_fn(x[1]), reverse=descending)

    logging.info('TopPickBanChamps in %s [key=%s, desc? %s] => (%s, %s)',
                 region, sort_key_fn, descending, num_games, sorted_champs[:5])
    return num_games, sorted_champs[:5]

  def GetUniqueChampCount(self, region):
    region = self._AliasToRegion(region) or region
    num_unique = sum(1 for c in self.champ_to_stats.values()
                     if region == 'all' or region in c.keys())
    num_games = sum(v for k, v in self.num_games.items()
                    if region in ('all', k))
    return num_unique, num_games

  def FetchEsportsData(self,
                       api_endpoint,
                       api_id=None,
                       force_lookup=False,
                       use_storage=False):
    """Gets eSports data from rito, bypassing the cache if force_lookup."""
    if api_endpoint != 'streamgroups' and not api_id:
      return
    base_esports_url = 'http://api.lolesports.com/api/'
    endpoint_urls = {
        'leagues': 'v1/leagues?slug=%s',
        'matchDetails': 'v2/highlanderMatchDetails?tournamentId=%s&matchId=%s',
        'scheduleItems': 'v1/scheduleItems?id=%s',
        'streamgroups': 'v2/streamgroups%s',
        'teams': 'v1/teams?slug=%s&tournament=%s'
    }
    full_url = base_esports_url + endpoint_urls[api_endpoint] % (api_id or '')
    return self._proxy.FetchJson(full_url,
                                 force_lookup=force_lookup,
                                 use_storage=use_storage)

  def FindTeam(self, query):
    query = query.upper()
    for t in self.teams.values():
      if query in (n.upper() for n in (t['acronym'], t['slug'], t['name'])):
        return t
    return None

  def _AliasToRegion(self, alias):
    for region, region_data in REGION_MAP.items():
      if (alias == region.upper() or
          alias in [x.upper() for x in region_data.get('aliases', '')]):
        return region
    return None

  def _ExtractMatchTeams(self, match, rosters):
    """Returns a (red_team, blue_team) tuple of acroynms for teams in match."""
    match_teams = match.get('input', [])
    if len(match_teams) != 2:
      return

    def _FindTeam(team):
      if 'roster' in team:
        return rosters[team['roster']]['acronym']
      return 'TBD'

    match_teams = [_FindTeam(t) for t in match_teams]
    return match_teams

  def _FindActiveTournaments(self, tournaments):
    """From a list of highlanderTournaments, finds all active or most recent."""
    active_tournaments = []
    tournament = None
    newest_start_date = arrow.Arrow.min
    t_now = arrow.utcnow()
    for t in tournaments:
      if 'startDate' not in t:
        continue
      t_start_date = arrow.get(t['startDate'])
      t_end_date = arrow.get(t['endDate'])
      if t_start_date > newest_start_date:
        newest_start_date = t_start_date
        tournament = t
      if t_start_date <= t_now <= t_end_date:
        active_tournaments.append(t)
    return active_tournaments or [tournament]

  def _MatchIsInteresting(self, match, qualifier, now, include_playoffs):
    """Small helper method to check if a match is interesting right now."""
    region_and_teams = (match['region'], match['blue'], match['red'])
    return ((qualifier == 'All' or qualifier in region_and_teams) and
            (match['time'] == arrow.Arrow.max or
             # Shift match time 3 hours into the future to show live games.
             match['time'].shift(hours=3) > now) and
            (include_playoffs or not match['playoff_match']))

  def _ResultIsInteresting(self, match, qualifier):
    region_and_teams = (match['region'], match['blue'], match['red'])
    if ((qualifier == 'All' or qualifier in region_and_teams) and
        match.get('winner', None)):
      return True
    return False

  def _ScrapePickBanData(self, tournament_id, region, match):
    """For each game in match, fetches and tallies pick/ban data from Riot."""
    game_id_mappings = self.FetchEsportsData(
        'matchDetails', (tournament_id, match['id']),
        use_storage=True).get('gameIdMappings')
    if not game_id_mappings:
      # We won't be able to find the gameHash, so just log
      logging.info('Not retrieving game stats for match %s', match['id'])
      return

    # Skip games that weren't actually played
    for guid, game in (m for m in match['games'].items() if 'gameId' in m[1]):
      self.num_games[region] += 1
      game_hash = [i['gameHash'] for i in game_id_mappings if i['id'] == guid]
      if len(game_hash) != 1:
        logging.warning('Couldn\'t find exactly one hash for match/game %s/%s:',
                        match['id'], guid)
        logging.warning('\tActual: %s', game_hash)
        continue

      game_hash = game_hash[0]
      game_stats = self._proxy.FetchJson(
          'https://acs.leagueoflegends.com/v1/stats/game/%s/%s?gameHash=%s' %
          (game['gameRealm'], game['gameId'], game_hash),
          use_storage=True)
      winning_team = None

      participant_to_player = {
          p['participantId']: util_lib.Access(p, 'player.summonerName')
          for p in game_stats.get('participantIdentities', [])
      }

      # Collect ban data
      for team in game_stats.get('teams', []):
        if team.get('win') == 'Win':
          winning_team = team.get('teamId')
        for ban in team.get('bans', []):
          self.champ_to_stats[ban['championId']][region]['bans'] += 1

      # Collect pick and W/L data
      for player in game_stats.get('participants', []):
        champ_id = player['championId']
        champ_name = self._game.GetChampNameFromId(champ_id)

        # We need to use separate player_name and player_key here because Rito
        # doesn't like to keep things like capitalization consistent with player
        # names so they aren't useful as keys, but we still want to display the
        # "canonical" player name back to the user eventually, so we save it as
        # a value in player_to_stats instead.
        player_name = participant_to_player[player['participantId']]
        player_key = util_lib.CanonicalizeName(player_name)
        self.player_to_stats[player_key]['name'] = player_name
        if player.get('teamId') == winning_team:
          self.champ_to_stats[champ_id][region]['wins'] += 1
          self.player_to_stats[player_key][champ_name]['wins'] += 1
          self.player_to_stats[player_key]['num_games']['wins'] += 1
        self.champ_to_stats[champ_id][region]['picks'] += 1
        self.player_to_stats[player_key][champ_name]['picks'] += 1
        self.player_to_stats[player_key]['num_games']['picks'] += 1
