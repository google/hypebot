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
"""Professional league related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial
import random
from threading import Lock

from absl import flags
import arrow

from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import name_complete_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data.league import messages
from hypebot.protos import message_pb2

LCS_TOPIC_STRING = u'#LcsHype | %s'

FLAGS = flags.FLAGS

flags.DEFINE_multi_string('spoiler_free_channels', ['#lol'], 'Channels where '
                          'LCS spoilers should be avoided')


@command_lib.CommandRegexParser(r'body ?(.*?)')
class BodyCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, bodyer):
    if not bodyer:
      bodyer = 'Jensen'
    bodyer = util_lib.StripColor(bodyer)
    if util_lib.CanonicalizeName(bodyer) == 'me':
      self._core.last_command = partial(self._Handle, bodyer=bodyer)
      bodyer = user
    return u'Yo, %s, body these fools!' % bodyer


@command_lib.CommandRegexParser(r'lcs-ch(a|u)mps (.+?)')
class LCSPlayerStatsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _FormatChamp(self, champ):
    """Formats champ tuple to display name (wins-losses)."""
    wins = champ[1].get('wins', 0)
    losses = champ[1]['picks'] - wins
    return '%s (%s-%s)' % (champ[0], wins, losses)

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, a_or_u, player):
    serious_output = a_or_u == 'a'
    # First, attempt to parse the query against the summoner tracker. If it
    # matches a username, then use it. The summoner tracker internally queries
    # Rito if it doesn't find a username, so we ignore those since LCS is on a
    # separate server and we don't want name conflicts.
    summoner = (self._core.summoner_tracker.ParseSummoner(
        user, None, None, player) or [{}])[0]
    if summoner.get('username'):
      player = summoner['summoner']
    player_name, player_data = self._core.esports.GetPlayerChampStats(player)
    if summoner.get('username'):
      player_name = '%s = %s' % (summoner['username'], player_name)
    if not player_name:
      return 'Unknown player. I can only give data about LCS players.'
    elif not player_data or not player_data['champs']:
      return '%s hasn\'t done much this split.' % player_name

    best_champs = sorted(
        player_data['champs'].items(),
        key=lambda x: (x[1].get('wins', 0), -x[1]['picks']),
        reverse=True)

    if serious_output:
      output = [
          '%s:' % self._FormatChamp((player_name, player_data['num_games']))
      ]
      output.extend(
          ['* %s' % self._FormatChamp(champ) for champ in best_champs[:5]])
      return output
    elif player_name == 'G2 Perkz':
      # Worst isn't the opposite order of best since more losses is worse than
      # fewer wins.
      worst_champ = sorted(
          player_data['champs'].items(),
          key=lambda x: (x[1]['picks'] - x[1].get('wins', 0), -x[1]['picks']),
          reverse=True)[0]
      return ('My {} is bad, my {} is worse; you guessed right, I\'m G2 Perkz'
              .format(
                  self._FormatChamp(worst_champ),
                  'Azir' if user == 'koelze' else 'Ryze'))
    else:
      most_played_champ = sorted(
          player_data['champs'].items(),
          key=lambda x: (x[1]['picks'], x[1].get('wins', 0)),
          reverse=True)[0]
      return (
          'My {} is fine, my {} is swell; you guessed right, I\'m {} stuck in '
          'LCS hell').format(
              self._FormatChamp(best_champs[0]),
              self._FormatChamp(most_played_champ),
              self._FormatChamp((player_name, player_data['num_games'])))


@command_lib.CommandRegexParser(r'lcs-link')
class LCSLivestreamLinkCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user):
    livestream_links = self._core.esports.GetLivestreamLinks()
    if livestream_links:
      self._core.interface.Topic(
          self._core.lcs_channel,
          LCS_TOPIC_STRING % list(livestream_links.values())[0])
      return ['Current LCS livestreams:'] + list(livestream_links.values())
    else:
      return ('I couldn\'t find any live LCS games, why don\'t you go play '
              'outside?')


class LCSMatchNotificationCommand(command_lib.BaseCommand):
  """Sends a notification when matches are nearing scheduled start time."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          # How soon before an LCS match to send a notification to subscribed
          # channels.
          'match_notification_sec': 15 * 60,
          'main_channel_only': False,
      })

  def __init__(self, *args):
    super(LCSMatchNotificationCommand, self).__init__(*args)
    self._core.esports.RegisterCallback(self._ScheduleAnnouncements)
    self._lock = Lock()
    self._scheduled_announcements = []

  def _ScheduleAnnouncements(self):
    now = arrow.utcnow()
    with self._lock:
      # Clear pending announcements.
      for job in self._scheduled_announcements:
        self._core.scheduler.UnscheduleJob(job)
      self._scheduled_announcements = []

      for match in self._core.esports.schedule:
        # TODO: Determine a good way to handle matches split across
        # multiple days.
        if match.announced:
          continue
        time_until_match = match.time - now
        seconds_until_match = (time_until_match.days * 86400
                               + time_until_match.seconds)
        if seconds_until_match > 0:
          self._scheduled_announcements.append(self._core.scheduler.InSeconds(
              seconds_until_match - self._params.match_notification_sec,
              self._AnnounceMatch, match))

  def _AnnounceMatch(self, match):
    match.announced = True
    topic = 'lcs_match'
    if self._core.esports.brackets[match.bracket_id].is_playoffs:
      topic = 'lcs_match_playoffs'

    blue = self._core.esports.MatchTeamName(match.blue)
    red = self._core.esports.MatchTeamName(match.red)
    if blue and red:
      match_name = '%s v %s' % (blue, red)
    else:
      match_name = 'An LCS match'
    call_to_action_str = 'Get #Hyped!'
    livestream_link = self._core.esports.GetLivestreamLinks().get(
        match.match_id)
    if livestream_link:
      call_to_action_str = 'Watch at %s and get #Hyped!' % livestream_link
      self._core.interface.Topic(
          self._core.lcs_channel, LCS_TOPIC_STRING % livestream_link)

    self._core.PublishMessage(
        topic, u'%s is starting soon. %s' % (match_name, call_to_action_str))


@command_lib.CommandRegexParser(
    r'lcs-p(?:ick)?b(?:an)?-?(\w+)? (.+?) ?([v|^]?)')
class LCSPickBanRatesCommand(command_lib.BaseCommand):
  """Better stats than LCS production."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _PopulatePickBanChampStr(self, champ_str, champ, stats, subcommand,
                               num_games):
    pb_info = {}
    pb_info['champ'] = champ
    pb_info['rate_str'] = subcommand[:-1].lower()
    pb_info['appear_str'] = ''
    if subcommand == 'all':
      pb_info['appear_str'] = '{:4.3g}% pick+ban rate, '.format(
          (stats['bans'] + stats['picks']) / num_games * 100)
      # For 'all' we show both pick+ban rate and win rate
      pb_info['rate_str'] = 'win'

    per_subcommand_data = {
        'ban': {
            'rate': stats['bans'] / num_games * 100,
            'stat': stats['bans'],
            'stat_desc': 'ban',
            'include_win_loss': False
        },
        'pick': {
            'rate': stats['picks'] / num_games * 100,
            'stat': stats['picks'],
            'stat_desc': 'game',
            'include_win_loss': True
        },
        'win': {
            'rate':
                0 if not stats['picks'] else
                stats['wins'] / stats['picks'] * 100,
            'stat':
                stats['picks'],
            'stat_desc':
                'game',
            'include_win_loss':
                True
        }
    }

    pb_info.update(per_subcommand_data[pb_info['rate_str']])
    pb_info['stat_str'] = inflect_lib.Plural(
        pb_info['stat'], pb_info['stat_desc'])
    pb_info['win_loss_str'] = ''
    if pb_info['include_win_loss']:
      pb_info['win_loss_str'] = ', %s-%s' % (stats['wins'],
                                             stats['picks'] - stats['wins'])
    return champ_str.format(**pb_info)

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, region, subcommand, order):
    if region:
      region = region.upper()
      region_msg = 'in %s' % region
    else:
      region = 'all'
      region_msg = 'across all LCS regions'

    subcommand = subcommand.lower()
    if subcommand == 'unique':
      num_unique, num_games = self._core.esports.GetUniqueChampCount(region)
      if num_games == 0:
        return 'I don\'t have any data =(.'
      avg_unique_per_game = num_games / num_unique
      return ('There have been {} unique champs [1 every {:.1f} '
              'games] picked or banned {}.').format(
                  num_unique, avg_unique_per_game, region_msg)

    elif subcommand in ('all', 'bans', 'picks', 'wins'):
      specifier_to_sort_key_fn = {
          'all': lambda stats: stats['picks'] + stats['bans'],
          'bans': lambda stats: stats['bans'],
          'picks': lambda stats: stats['picks'],
          'wins': lambda stats: stats['wins'] / stats['picks'],
      }
      sort_key_fn = specifier_to_sort_key_fn[subcommand]
      descending = order != '^'

      order_str = 'Top' if descending else 'Bottom'
      rate_str = subcommand[:-1].title()
      if subcommand == 'all':
        rate_str = 'Pick+Ban'
      num_games, top_champs = self._core.esports.GetTopPickBanChamps(
          region, sort_key_fn, descending)

      min_game_str = inflect_lib.Plural(max(1, num_games / 20), 'game')
      responses = ['%s Champs by %s Rate %s [min %s].' %
                   (order_str, rate_str, region_msg, min_game_str)]

      max_champ_len = max(len(x[0]) for x in top_champs)
      champ_str = ('{champ:%s} - {appear_str}{rate:4.3g}%% {rate_str} rate '
                   '({stat_str}{win_loss_str})' % max_champ_len)
      for champ, stats in top_champs:
        responses.append(self._PopulatePickBanChampStr(
            champ_str, champ, stats, subcommand, num_games))
      return responses

    canonical_name, pb_data = self._core.esports.GetChampPickBanRate(
        region, subcommand)
    if not canonical_name:
      return ('While you may want {0} to be a real champ, your team doesn\'t '
              'think {0} is a real champ.').format(subcommand)

    if pb_data['num_games'] == 0 or ('picks' not in pb_data and
                                     'bans' not in pb_data):
      return '%s is not very popular %s.' % (canonical_name, region_msg)

    appear_rate = (
        pb_data['bans'] + pb_data['picks']) / pb_data['num_games']
    win_msg = ' with a {:.0%} win rate'
    if pb_data['picks'] == 0:
      win_msg = ''
    else:
      win_msg = win_msg.format(pb_data['wins'] / pb_data['picks'])
    losses = pb_data['picks'] - pb_data['wins']

    return '{} has appeared in {:.1%} of games ({}, {}){} ({}-{}) {}.'.format(
        canonical_name, appear_rate,
        inflect_lib.Plural(pb_data['bans'], 'ban'),
        inflect_lib.Plural(pb_data['picks'], 'pick'), win_msg, pb_data['wins'],
        losses, region_msg)


@command_lib.CommandRegexParser(r'schedule(full)? ?(.*?)')
class LCSScheduleCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'num_games': 5,
          'full_num_games': 10,
      })

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, full, subcommand):
    include_playoffs = True
    # Avoid spoilers in spoiler-free channels.
    if channel.id in FLAGS.spoiler_free_channels:
      include_playoffs = False
    subcommand = subcommand.upper()
    num_games = self._params.num_games
    if full == 'full':
      num_games = self._params.full_num_games
    schedule, subcommand = self._core.esports.GetSchedule(
        subcommand or 'All', include_playoffs, num_games)

    lines = ['%s Upcoming Matches' % subcommand]
    lines.extend(schedule)
    # Print a disclaimer if we (potentially) omitted any matches.
    if not include_playoffs and len(schedule) != num_games:
      lines.append('(Note: Some matches may be omitted for spoiler reasons)')
    return lines


@command_lib.CommandRegexParser(r'standings ?(.*?)')
class LCSStandingsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'default_region': 'NA',
          'main_channel_only': False
      })

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, query):
    # Avoid spoilers in spoiler-free channels.
    if channel.id in FLAGS.spoiler_free_channels:
      return 'pls no spoilerino'
    query = query.split()
    league = query[0] if query else self._params.default_region
    bracket = ' '.join(query[1:]) if len(query) > 1 else 'regular'

    standings = self._core.esports.GetStandings(league, bracket)

    cards = []
    for standing in standings:
      has_ties = any([team.ties for team in standing['teams']])
      format_str = '{0.wins}-{0.losses}'
      if has_ties:
        format_str += '-{0.ties}, {0.points}'
      card = message_pb2.Card(
          header={
              'title': standing['league'].name,
              'subtitle': '%s (%s)' % (standing['bracket'].name,
                                       'W-L-D, Pts' if has_ties else 'W-L'),
          },
          # We will place the top-n teams into the first field separated by
          # newlines so that we don't have extra whitespace.
          visible_fields_count=1)
      team_strs = [
          ('*{0.rank}:* {0.team.abbreviation} (%s)' % format_str).format(team)
          for team in standing['teams']
      ]
      # If there are a lot of teams in the bracket, only display the top few.
      # 6 is chosen since many group stages and Grumble consist of 6 team
      # brackets.
      if len(team_strs) > 6:
        # The number placed into the visible field is n-1 so that we don't only
        # show a single team in the collapsed section.
        card.fields.add(text='\n'.join(team_strs[:5]))
        card.fields.add(text='\n'.join(team_strs[5:]))
      else:
        card.fields.add(text='\n'.join(team_strs))
      cards.append(card)
    return cards


@command_lib.CommandRegexParser(r'results(full)? ?(.*?)')
class LCSResultsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'num_games': 5,
          'full_num_games': 10,
          'main_channel_only': False,
      })

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, full, region):
    # Avoid spoilers in spoiler-free channels.
    if channel.id in FLAGS.spoiler_free_channels:
      return 'pls no spoilerino'
    num_games = self._params.num_games
    if full == 'full':
      num_games = self._params.full_num_games
    schedule, region = self._core.esports.GetResults(region or 'All', num_games)

    schedule.insert(0, '%s Past Matches' % region)
    return schedule


@command_lib.CommandRegexParser(r'roster(full)?(?:-(\w+))? (.+?)')
class LCSRosterCommand(command_lib.BaseCommand):
  """Display players and their roles."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  # A map of actual player names to what their name should be displayed as.
  # You know, for memes.
  NAME_SUBSTITUTIONS = {
      'Revolta': 'Travolta',
      'MikeYeung': 'Mike "Mike Yeung" Yeung',
  }

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, include_subs, region, team):
    teams = self._core.esports.teams
    if region:
      league = self._core.esports.leagues[region]
      if not league:
        return 'Unknown region'
      teams = {team.team_id: team for team in league.teams}
      teams = name_complete_lib.NameComplete(
          dict({team.name: team_id for team_id, team in teams.items()}, **{
              team.abbreviation: team_id for team_id, team in teams.items()
          }), teams)

    team = teams[team]
    if not team:
      return 'Unknown team.'
    response = ['%s Roster:' % team.name]
    players = [player for player in team.players
               if not player.is_substitute or include_subs]
    role_order = {'Top': 0, 'Jungle': 1, 'Mid': 2, 'Bottom': 3, 'Support': 4}
    players.sort(key=lambda p: role_order.get(p.position, 5))
    for player in players:
      response.append('%s - %s' % (
          self.NAME_SUBSTITUTIONS.get(player.summoner_name,
                                      player.summoner_name),
          player.position))
    return response


@command_lib.CommandRegexParser(r'rooster(full)? (.+?)')
class LCSRoosterCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, include_sub, team):
    team = team.upper()
    roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
    if include_sub:
      pos, role = random.choice(list(enumerate(roles)))
      roles.insert(int(pos) + 1, '%s (Sub)' % role)
    players = random.sample(messages.ROOSTERS, len(roles))
    responses = ['%s Roosters:' % team]
    for role, player in zip(roles, players):
      responses.append('%s - %s' % (player, role))
    return responses
