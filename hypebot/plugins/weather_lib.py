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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from typing import Any, Dict, Optional, Text

from hypebot.protos import weather_pb2
from hypebot.proxies import proxy_lib

_GEOCODE_URL = 'https://api.geocod.io/v1.4/geocode'
_DARKSKY_URL = 'https://api.darksky.net/forecast'


class WeatherException(Exception):

  def __init__(self, code, message):
    super(WeatherException,
          self).__init__('Error code %s: "%s"' % (code, message))


class WeatherLib(object):

  def __init__(self, proxy: proxy_lib.Proxy, darksky_key: Text,
               geocode_key: Text):
    self._proxy = proxy
    self._darksky_key = darksky_key
    self._geocode_key = geocode_key

  def _LocationToGPS(self, location: Text) -> Optional[Dict[Any, Any]]:
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
    response = self._proxy.FetchJson(
        _GEOCODE_URL,
        params={
            'q': location,
            'api_key': self._geocode_key,
            'limit': 1,
        },
        force_lookup=True)
    if not response:
      return None
    if not response['results']:
      return None
    return response['results'][0]

  def _CallForecast(self, gps: Dict[Text, Any]):
    url = os.path.join(_DARKSKY_URL, self._darksky_key,
                       '{lat},{lng}'.format(**gps))
    return self._proxy.FetchJson(url, force_lookup=True)

  def GetForecast(self, location: Text):
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
            condition=forecast['currently']['summary']))

    for day in forecast['daily']['data']:
      weather.forecast.add(
          min_temp_f=day['temperatureLow'],
          max_temp_f=day['temperatureHigh'],
          condition=day['summary'])

    return weather
