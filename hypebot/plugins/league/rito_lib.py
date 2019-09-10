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
"""rito_lib is a wrapper around Riot API v4.

Due to the deprecation of the static data API, we use data dragon and mimic the
old response from the static-data-api.

usage:
  # setup
  import rito_lib
  s = rito_lib.RitoLib(api_key, proxy, rito_api_channel)

  # wrappers for api calls.
  s.GetSummoner(region, summoner_name)
  s.GetSummonerBySummonerId(region, summoner_id)
  s.ListLeaguePositions(region, summoner_id)
  s.ListChampionMasteries(region, summoner_id)
  s.GetChampionMastery(region, summoner_id, champ_id)
  s.ListRecentMatches(region, account_id)
  s.GetMatch(region, game_id)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from absl import logging
from google.protobuf import json_format
from google.protobuf import text_format
import grpc
import os
import six

from hypebot.protos.riot import platform_pb2
from hypebot.protos.riot.v4 import champion_mastery_pb2
from hypebot.protos.riot.v4 import champion_mastery_pb2_grpc
from hypebot.protos.riot.v4 import league_pb2
from hypebot.protos.riot.v4 import league_pb2_grpc
from hypebot.protos.riot.v4 import match_pb2
from hypebot.protos.riot.v4 import match_pb2_grpc
from hypebot.protos.riot.v3 import static_data_pb2
from hypebot.protos.riot.v4 import summoner_pb2
from hypebot.protos.riot.v4 import summoner_pb2_grpc

PLATFORM_IDS = {
    'br': platform_pb2.BR1,
    'eune': platform_pb2.EUN1,
    'euw': platform_pb2.EUW1,
    'jp': platform_pb2.JP1,
    'kr': platform_pb2.KR,
    'lan': platform_pb2.LA1,
    'las': platform_pb2.LA2,
    'na': platform_pb2.NA1,
    'oce': platform_pb2.OC1,
    'tr': platform_pb2.TR1,
    'ru': platform_pb2.RU,
    'pbe': platform_pb2.PBE1,
}


class DataDragonLib(object):
  """Wraps ddragon to mimic old static-data-api."""

  _BASE_URL = 'https://ddragon.leagueoflegends.com'

  def __init__(self, proxy):
    self._proxy = proxy

  def _EndpointUrl(self, endpoint, realm='na'):
    response = self._proxy.FetchJson(
        os.path.join(self._BASE_URL, 'realms', '%s.json' % realm))
    version = response.get('v')
    return os.path.join(self._BASE_URL, 'cdn', version, 'data/en_US',
                        '%s.json' % endpoint)

  def ListChampions(self):
    """Use undocumented endpoint to list champions."""
    response = self._proxy.FetchJson(self._EndpointUrl('championFull'))
    # Fix differences between static-data and ddragon.
    for _, champ in response['data'].items():
      tmp = champ['id']
      champ['id'] = champ['key']
      champ['key'] = tmp

      for spell in champ['spells']:
        spell['effectBurn'][0] = ''
        for var in spell['vars']:
          if not isinstance(var['coeff'], list):
            var['coeff'] = [var['coeff']]

    return json_format.ParseDict(
        response,
        static_data_pb2.ListChampionsResponse(),
        ignore_unknown_fields=True)

  def ListItems(self):
    response = self._proxy.FetchJson(self._EndpointUrl('item'))
    return json_format.ParseDict(
        response,
        static_data_pb2.ListItemsResponse(),
        ignore_unknown_fields=True)

  def ListReforgedRunePaths(self):
    response = self._proxy.FetchJson(self._EndpointUrl('runesReforged'))
    return json_format.ParseDict(
        {
            'paths': response
        },  # ddragon pls.
        static_data_pb2.ListReforgedRunePathsResponse(),
        ignore_unknown_fields=True)


class RitoLib(object):
  """Class for fetching various data from Riot API."""

  def __init__(self, proxy, channel, api_key):
    self._proxy = proxy
    self.api_key = api_key

    self._champion_mastery_service = (
        champion_mastery_pb2_grpc.ChampionMasteryServiceStub(channel))
    self._league_service = league_pb2_grpc.LeagueServiceStub(channel)
    self._match_service = match_pb2_grpc.MatchServiceStub(channel)
    self._summoner_service = summoner_pb2_grpc.SummonerServiceStub(channel)

    self._ddragon = DataDragonLib(self._proxy)

  def _GetPlatformMetadata(self, region):
    return platform_pb2.PlatformId.Name(
        PLATFORM_IDS.get(region, platform_pb2.NA1))

  def _CallApi(self, method, request, region, use_storage=False):
    """Send an RPC to the Riot API.

    Returns cached results, if available. By default, results are cached in-
    memory. Results may also be cached permanently in long-term storage.

    Args:
      method: The RPC method to call.
      request: The RPC request.
      region: The Riot API region.
      use_storage: If True, permanently store the result.

    Returns:
      The data or None if the RPC failed.
    """
    metadata = (('api-key', self.api_key), ('platform-id',
                                            self._GetPlatformMetadata(region)))
    rpc_action = lambda: method(request, metadata=metadata).SerializeToString()
    request_plain_text = text_format.MessageToString(
        request, as_utf8=not six.PY2, as_one_line=True)
    method_name = method._method.decode('utf8')
    key = ':'.join((region, method_name, request_plain_text))
    # Handle RPC exceptions outside of the proxy fetch so temporary errors are
    # not cached.
    try:
      r = self._proxy.RawFetch(key, rpc_action, use_storage=use_storage)
      if r:
        return method._response_deserializer(r)
    except grpc.RpcError as e:
      logging.error('RPC %s with request %s failed: %s', method_name, request,
                    e)

  def GetSummoner(self, region, summoner_name):
    return self._CallApi(
        self._summoner_service.GetSummoner,
        summoner_pb2.GetSummonerRequest(summoner_name=summoner_name), region)

  def GetSummonerBySummonerId(self, region, encrypted_summoner_id):
    return self._CallApi(
        self._summoner_service.GetSummoner,
        summoner_pb2.GetSummonerRequest(
            encrypted_summoner_id=encrypted_summoner_id), region)

  def GetSummonerByAccountId(self, region, encrypted_account_id):
    return self._CallApi(
        self._summoner_service.GetSummoner,
        summoner_pb2.GetSummonerRequest(
            encrypted_account_id=encrypted_account_id), region)

  def GetSummonerByPuuid(self, region, encrypted_puuid):
    return self._CallApi(
        self._summoner_service.GetSummoner,
        summoner_pb2.GetSummonerRequest(encrypted_puuid=encrypted_puuid),
        region)

  def ListLeaguePositions(self, region, encrypted_summoner_id):
    return self._CallApi(
        self._league_service.ListLeaguePositions,
        league_pb2.ListLeaguePositionsRequest(
            encrypted_summoner_id=encrypted_summoner_id), region)

  def ListChampionMasteries(self, region, encrypted_summoner_id):
    return self._CallApi(
        self._champion_mastery_service.ListChampionMasteries,
        champion_mastery_pb2.ListChampionMasteriesRequest(
            encrypted_summoner_id=encrypted_summoner_id), region)

  def GetChampionMastery(self, region, encrypted_summoner_id, champ_id):
    return self._CallApi(
        self._champion_mastery_service.GetChampionMastery,
        champion_mastery_pb2.GetChampionMasteryRequest(
            encrypted_summoner_id=encrypted_summoner_id, champion_id=champ_id),
        region)

  def ListRecentMatches(self, region, encrypted_account_id):
    return self._CallApi(
        self._match_service.ListMatches,
        match_pb2.ListMatchesRequest(
            encrypted_account_id=encrypted_account_id, end_index=20), region)

  def GetMatch(self, region, game_id):
    return self._CallApi(
        self._match_service.GetMatch,
        match_pb2.GetMatchRequest(game_id=game_id),
        region,
        use_storage=True)

  def ListItems(self):
    return self._ddragon.ListItems()

  def ListChampions(self):
    return self._ddragon.ListChampions()

  def ListReforgedRunePaths(self):
    return self._ddragon.ListReforgedRunePaths()
