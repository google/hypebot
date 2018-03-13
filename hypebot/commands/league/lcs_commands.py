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

from absl import flags
import arrow

from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data.league import messages

LCS_TOPIC_STRING = u'#LcsHype | %s'

FLAGS = flags.FLAGS

flags.DEFINE_multi_string('spoiler_free_channels', ['#lol'], 'Channels where '
                          'LCS spoilers should be avoided')


@command_lib.CommandRegexParser(r'body ?(.*?)')
class BodyCommand(command_lib.BaseCommand):

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

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, a_or_u, player):
    serious_output = a_or_u == 'a'
    player_name, player_data = self._core.esports.GetPlayerChampStats(player)
    if not player_name:
      return 'Unknown player. I can only give data about LCS players.'
    elif not player_data or not player_data['champs']:
      return '%s hasn\'t done much this split.' % player_name

    champ_data = player_data['champs']
    total_wins = player_data['num_games']['wins']
    total_losses = player_data['num_games']['picks'] - total_wins
    player_str = '%s (%s-%s)' % (player_name, total_wins, total_losses)

    # Break ties in most_played by wins
    champs = sorted(champ_data.items(), key=lambda x: x[1].get('wins', 0))
    most_played_champ = sorted(champs, key=lambda x: x[1]['picks'])[-1][0]
    most_played_champ_wins = champ_data[most_played_champ]['wins']
    most_played_champ_losses = champ_data[most_played_champ][
        'picks'] - most_played_champ_wins
    most_played_champ_str = '%s (%s-%s)' % (
        most_played_champ, most_played_champ_wins, most_played_champ_losses)

    # Break ties in best_champ by picks
    champs = sorted(champ_data.items(), key=lambda x: x[1]['picks'])
    best_champ = sorted(champs, key=lambda x: x[1]['wins'])[-1][0]
    best_champ_wins = champ_data[best_champ]['wins']
    best_champ_losses = champ_data[best_champ]['picks'] - best_champ_wins
    best_champ_str = '%s (%s-%s)' % (best_champ, best_champ_wins,
                                     best_champ_losses)
    if serious_output:
      return '{}: Most Wins: {}, Most Played: {}.'.format(
          player_str, best_champ_str, most_played_champ_str)
    elif player_name == 'G2 Perkz':
      # Break ties in worst_champ by picks
      champs = sorted(champ_data.items(), key=lambda x: x[1]['picks'])
      worst_champ = sorted(
          champs, key=lambda x: x[1]['picks'] - x[1].get('wins', 0))[-1][0]
      worst_champ_wins = champ_data[worst_champ].get('wins', 0)
      worst_champ_losses = champ_data[worst_champ]['picks'] - worst_champ_wins
      worst_champ_str = '%s (%s-%s)' % (worst_champ, worst_champ_wins,
                                        worst_champ_losses)
      return ('My {} is bad, my {} is worse; you guessed right, I\'m G2 Perkz'.
              format(worst_champ_str, 'Azir' if user == 'koelze' else 'Ryze'))
    else:
      return (
          'My {} is fine, my {} is swell; you guessed right, I\'m {} stuck in '
          'LCS hell').format(best_champ_str, most_played_champ_str, player_str)


@command_lib.CommandRegexParser(r'lcs-link')
class LCSLivestreamLinkCommand(command_lib.BaseCommand):

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


# TODO(b/65917977) Convert to a scheduled callback.
@command_lib.PublicParser
class LCSMatchNotificationCommand(command_lib.BasePublicCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          # How soon before an LCS match to send a notification to subscribed
          # channels.
          'match_notification_sec': 15 * 60,
          'ratelimit': {'enabled': False},
      })

  def _Handle(self, channel, user, message):
    now = arrow.utcnow()
    for match in self._core.esports.schedule:
      if channel.id in match['announced']:
        continue
      time_until_match = match['time'] - now
      if time_until_match.days < 0 or time_until_match.seconds < 0:
        match['announced'][channel.id] = True
        continue

      if (time_until_match.days == 0 and
          time_until_match.seconds < self._params.match_notification_sec):
        if match.get('playoffs') and channel.id in FLAGS.spoiler_free_channels:
          continue
        match['announced'][channel.id] = True
        blue, red = (match.get('blue'), match.get('red'))
        if blue and red:
          match_name = '%s v %s' % (blue, red)
        else:
          match_name = 'A LCS match'
        livestream_str = messages.FALLBACK_LIVESTREAM_LINK
        livestream_link = self._core.esports.GetLivestreamLinks().get(
            match['id'])
        if livestream_link:
          livestream_str = 'Watch at %s' % livestream_link
          self._core.interface.Topic(
              self._core.lcs_channel, LCS_TOPIC_STRING % livestream_link)
        self._core.interface.Notice(
            channel, u'%s is starting in ~%s. %s and get #Hyped!' %
            (match_name, inflect_lib.Plural(time_until_match.seconds / 60,
                                            'minute'), livestream_str))


@command_lib.CommandRegexParser(
    r'lcs-p(?:ick)?b(?:an)?-?(\w+)? (.+?) ?([v|^]?)')
class LCSPickBanRatesCommand(command_lib.BaseCommand):
  """Better stats than LCS production."""

  def _PopulatePickBanChampStr(self, champ_str, champ, stats, subcommand,
                               num_games):
    pb_info = {}
    pb_info['champ'] = champ
    pb_info['rate_str'] = subcommand[:-1].lower()
    pb_info['appear_str'] = ''
    if subcommand == 'all':
      pb_info['appear_str'] = '{:4.3g}% pick+ban rate, '.format(
          (stats['bans'] + stats['picks']) / float(num_games) * 100)
      # For 'all' we show both pick+ban rate and win rate
      pb_info['rate_str'] = 'win'

    per_subcommand_data = {
        'ban': {
            'rate': stats['bans'] / float(num_games) * 100,
            'stat': stats['bans'],
            'stat_desc': 'ban',
            'include_win_loss': False
        },
        'pick': {
            'rate': stats['picks'] / float(num_games) * 100,
            'stat': stats['picks'],
            'stat_desc': 'game',
            'include_win_loss': True
        },
        'win': {
            'rate':
                0 if not stats['picks'] else
                stats['wins'] / float(stats['picks']) * 100,
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
      avg_unique_per_game = float(num_games) / num_unique
      return ('There have been {} unique champs [1 every {:.1f} '
              'games] picked or banned {}.').format(
                  num_unique, avg_unique_per_game, region_msg)

    elif subcommand in ('all', 'bans', 'picks', 'wins'):
      specifier_to_sort_key_fn = {
          'all': lambda stats: stats['picks'] + stats['bans'],
          'bans': lambda stats: stats['bans'],
          'picks': lambda stats: stats['picks'],
          'wins': lambda stats: stats['wins'] / float(stats['picks']),
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
        pb_data['bans'] + pb_data['picks']) / float(pb_data['num_games'])
    win_msg = ' with a {:.0%} win rate'
    if pb_data['picks'] == 0:
      win_msg = ''
    else:
      win_msg = win_msg.format(pb_data['wins'] / float(pb_data['picks']))
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
        subcommand, include_playoffs, num_games)

    lines = ['%s Upcoming Matches' % subcommand]
    lines.extend(schedule)
    # Print a disclaimer if we (potentially) omitted any matches.
    if not include_playoffs and len(schedule) != num_games:
      lines.append('(Note: Some matches may be omitted for spoiler reasons)')
    return lines


@command_lib.CommandRegexParser(r'standings ?(.*?)')
class LCSStandingsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {'default_region': 'NA'})

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, query):
    # Avoid spoilers in spoiler-free channels.
    if channel.id in FLAGS.spoiler_free_channels:
      return 'pls no spoilerino'
    query = query.upper().split()
    req_league = query[0] if query else self._params.default_region
    req_brackets = query[1:] if len(query) > 1 else ['SEASON']

    return self._core.esports.GetStandings(req_league, req_brackets)


@command_lib.CommandRegexParser(r'results(full)? ?(.*?)')
class LCSResultsCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'num_games': 5,
          'full_num_games': 10,
      })

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, full, region):
    # Avoid spoilers in spoiler-free channels.
    if channel.id in FLAGS.spoiler_free_channels:
      return 'pls no spoilerino'
    num_games = self._params.num_games
    if full == 'full':
      num_games = self._params.full_num_games
    schedule, region = self._core.esports.GetResults(region.upper(), num_games)

    schedule.insert(0, '%s Past Matches' % region)
    return schedule


@command_lib.CommandRegexParser(r'roster(full)?(?:-(\w+))? (.+?)')
class LCSRosterCommand(command_lib.BaseCommand):

  @command_lib.RequireReady('_core.esports')
  def _Handle(self, channel, user, include_subs, region, team):
    roster = self._core.esports.GetRoster(team, region, include_subs)
    if not roster:
      return 'Unknown team.'
    return roster


@command_lib.CommandRegexParser(r'rooster(full)? (.+?)')
class LCSRoosterCommand(command_lib.BaseCommand):

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
