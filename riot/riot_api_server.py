# Lint as: python3
# Copyright 2020 The Hypebot Authors. All rights reserved.
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
"""Main server to fetch data from Riot API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import concurrent
import os

from absl import app
from absl import flags
from absl import logging
from google.protobuf import json_format
import grpc
import requests

from hypebot.protos.riot.v4 import champion_mastery_pb2
from hypebot.protos.riot.v4 import champion_mastery_pb2_grpc
from hypebot.protos.riot.v4 import league_pb2
from hypebot.protos.riot.v4 import league_pb2_grpc
from hypebot.protos.riot.v4 import match_pb2
from hypebot.protos.riot.v4 import match_pb2_grpc
from hypebot.protos.riot.v4 import summoner_pb2
from hypebot.protos.riot.v4 import summoner_pb2_grpc

FLAGS = flags.FLAGS

flags.DEFINE_string('host', 'localhost', 'Which host to use.')
flags.DEFINE_integer('port', 50051, 'Which port to bind to.')


def _convert_metadata_to_dict(metadata):
  metadata_dict = {}
  for key, value in metadata:
    metadata_dict[key] = value
  return metadata_dict


def _call_riot(endpoint, params, message, metadata, body_transform=None):
  """Helper function to call rito API.

  Args:
    endpoint: relative path to endpoint within Riot API.
    params: Additional params to pass to the web request.
    message: Proto message into which to write response. Note: this is an actual
      message object and not simply the type. E.g., match_pb2.Match() not
      match_pb2.Match.
    metadata: Invocation_metadata from gRPC.
    body_transform: Optional function to apply to raw response body prior to
      parsing. JSON supports lists as the base object in the response, but
      protos do not, so we sometimes need to add a wrapper Dict around the
      response.

  Returns:
    The input message with fields set based on the call.

  Raises:
    RuntimeError: If request fails.
  """
  metadata = _convert_metadata_to_dict(metadata)

  url = os.path.join(
      'https://%s.api.riotgames.com' % metadata.get('platform-id', 'na1'),
      endpoint)
  headers = {'X-Riot-Token': metadata['api-key']}
  response = requests.get(url, params=params, headers=headers)
  if response.status_code != requests.codes.ok:
    raise RuntimeError('Failed request for: %s' % url)
  body = response.text
  if body_transform:
    body = body_transform(body)
  return json_format.Parse(body, message, ignore_unknown_fields=True)


class ChampionMasteryService(
    champion_mastery_pb2_grpc.ChampionMasteryServiceServicer):
  """Champion Mastery API."""

  def ListChampionMasteries(self, request, context):
    return _call_riot(
        'lol/champion-mastery/v4/champion-masteries/by-summoner/%s' %
        request.encrypted_summoner_id, {},
        champion_mastery_pb2.ListChampionMasteriesResponse(),
        context.invocation_metadata(),
        body_transform=lambda x: '{"championMasteries": %s }' % x)

  def GetChampionMastery(self, request, context):
    endpoint = ('lol/champion-mastery/v4/champion-masteries/by-summoner/%s/'
                'by-champion/%s' %
                (request.encrypted_summoner_id, request.champion_id))
    return _call_riot(endpoint, {}, champion_mastery_pb2.ChampionMastery(),
                      context.invocation_metadata())

  def GetChampionMasteryScore(self, request, context):
    return _call_riot(
        'lol/champion-mastery/v4/scores/by-summoner/%s' %
        request.encrypted_summoner_id, {},
        champion_mastery_pb2.ChampionMasteryScore(),
        context.invocation_metadata(),
        body_transform=lambda x: '{"score": %s }' % x)


class MatchService(match_pb2_grpc.MatchServiceServicer):
  """Match API."""

  def ListMatches(self, request, context):
    params = {}
    if request.queues:
      params['queue'] = [int(q) for q in request.queues]
    if request.seasons:
      params['season'] = [int(s) for s in request.seasons]
    if request.champions:
      params['champions'] = request.seasons
    if request.begin_time_ms:
      params['beginTime'] = request.begin_time_ms
      params['endTime'] = request.end_time_ms
    if request.begin_index:
      params['beginIndex'] = request.begin_index
      params['endIndex'] = request.end_index

    return _call_riot(
        'lol/match/v4/matchlists/by-account/%s' % request.encrypted_account_id,
        params, match_pb2.ListMatchesResponse(), context.invocation_metadata())

  def ListTournamentMatchIds(self, request, context):
    return _call_riot(
        'lol/match/v4/matches/by-tournament-code/%s/ids' %
        request.tournament_code, {}, match_pb2.ListTournamentMatchIdsResponse(),
        context.invocation_metadata())

  def GetMatch(self, request, context):
    endpoint = 'lol/match/v4/matches/%s' % request.game_id
    if request.tournament_code:
      endpoint += '/by-tournament-code/%s' % request.tournament_code
    return _call_riot(endpoint, {}, match_pb2.Match(),
                      context.invocation_metadata())


class SummonerService(summoner_pb2_grpc.SummonerServiceServicer):
  """Summoner API."""

  def GetSummoner(self, request, context):
    endpoint = 'lol/summoner/v4/summoners'
    key_type = request.WhichOneof('key')
    if key_type == 'encrypted_summoner_id':
      endpoint += '/%s' % request.encrypted_summoner_id
    elif key_type == 'encrypted_account_id':
      endpoint += '/by-account/%s' % request.encrypted_account_id
    elif key_type == 'summoner_name':
      endpoint += '/by-name/%s' % request.summoner_name
    elif key_type == 'encrypted_puuid':
      endpoint += '/by-puuid/%s' % request.encrypted_puuid
    else:
      raise ValueError('GetSummoner: no key specified')
    return _call_riot(endpoint, {}, summoner_pb2.Summoner(),
                      context.invocation_metadata())


class LeagueService(league_pb2_grpc.LeagueServiceServicer):
  """League API."""

  def ListLeaguePositions(self, request, context):
    endpoint = ('lol/league/v4/entries/by-summoner/%s' %
                request.encrypted_summoner_id)
    return _call_riot(
        endpoint, {},
        league_pb2.ListLeaguePositionsResponse(),
        context.invocation_metadata(),
        body_transform=lambda x: '{"positions": %s }' % x)


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')
  server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
  champion_mastery_pb2_grpc.add_ChampionMasteryServiceServicer_to_server(
      ChampionMasteryService(), server)
  league_pb2_grpc.add_LeagueServiceServicer_to_server(LeagueService(), server)
  match_pb2_grpc.add_MatchServiceServicer_to_server(MatchService(), server)
  summoner_pb2_grpc.add_SummonerServiceServicer_to_server(
      SummonerService(), server)
  authority = '%s:%s' % (FLAGS.host, FLAGS.port)
  logging.info('Starting server at %s', authority)
  server.add_insecure_port(authority)
  server.start()
  server.wait_for_termination()


if __name__ == '__main__':
  app.run(main)
