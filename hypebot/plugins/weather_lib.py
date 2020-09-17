# Lint as: python3
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
"""Current / historical weather from darksky.net."""

import os

from typing import Any, Dict, Optional

from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.protos import weather_pb2
from hypebot.proxies import proxy_lib

_GEOCODE_URL = 'https://api.geocod.io/v1.4/geocode'
_DARKSKY_URL = 'https://api.darksky.net/forecast'
_AIRNOW_URL = 'http://www.airnowapi.org/aq'


class WeatherException(Exception):

  def __init__(self, code, message):
    super(WeatherException,
          self).__init__('Error code %s: "%s"' % (code, message))


class WeatherLib(object):
  """Is it raining, is it snowing, is a hurricane a-blowing?"""

  DEFAULT_PARAMS = params_lib.HypeParams({
      'geocode_key': None,
      'darksky_key': None,
      'airnow_key': None,
  })

  def __init__(self,
               proxy: proxy_lib.Proxy,
               params: params_lib.HypeParams):
    self._proxy = proxy
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    self._params.Lock()

  def _LocationToGPS(self, location: str) -> Optional[Dict[Any, Any]]:
    """Uses geocode API to convert human location into GPS coordinates.

    Args:
      location: Human readable location.

    Returns:
      Dictionary with location information. Important keys are
      `formatted_address` and `location` which is a dictionary of `lat`/`lng`.
      None if no results are found.

    Raises:
      WeatherException: If the API call failed.
    """
    # Override airport code from pacific.
    if location.lower() == 'mtv':
      location = 'mountain view, CA'

    response = self._proxy.FetchJson(
        _GEOCODE_URL,
        params={
            'q': location,
            'api_key': self._params.geocode_key,
            'limit': 1,
        },
        force_lookup=True)
    if not response:
      return None
    if not response['results']:
      return None
    return response['results'][0]

  def _CallForecast(self, gps: Dict[str, Any]):
    url = os.path.join(_DARKSKY_URL, self._params.darksky_key,
                       '{lat},{lng}'.format(**gps))
    return self._proxy.FetchJson(url, force_lookup=True)

  def GetForecast(self, location: str):
    """Get weather forecast for the location.

    Forecast consists of the current conditions and predictions for the future.

    Args:
      location: Location in human readable form.

    Returns:
      WeatherProto with condition and forecast filled in.
    """
    location = self._LocationToGPS(location)
    if not location:
      return None

    forecast = self._CallForecast(location['location'])
    if not forecast:
      return None

    weather = weather_pb2.Weather(
        location=location['formatted_address'],
        current=weather_pb2.Current(
            temp_f=forecast['currently']['temperature'],
            condition=forecast['currently']['summary'],
            icon=forecast['currently']['icon']))

    for day in forecast['daily']['data']:
      weather.forecast.add(
          min_temp_f=day['temperatureLow'],
          max_temp_f=day['temperatureHigh'],
          condition=day['summary'],
          icon=day['icon'])

    return weather

  def _CallAQI(self, zip_code: str):
    return self._proxy.FetchJson(
        os.path.join(_AIRNOW_URL, 'observation/zipCode/current'),
        params={
            'format': 'application/json',
            'zipCode': zip_code,
            'distance': 50,
            'API_KEY': self._params.airnow_key,
        },
        force_lookup=True)

  def GetAQI(self, location: str):
    """Get air quality index for the location.

    Args:
      location: Location in human readable form.

    Returns:
      AQI response from airnow.
    """
    location = self._LocationToGPS(location)
    if not location:
      return None
    zip_code = util_lib.Access(location, 'address_components.zip')
    if not zip_code:
      return None

    return self._CallAQI(zip_code)
