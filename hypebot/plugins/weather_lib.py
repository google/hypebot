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
"""Current / historical weather from apixu.com."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import arrow
from typing import Optional

from hypebot.protos import weather_pb2
from hypebot.proxies import proxy_lib

# Free API allows up to 5k requests per month.
_BASE_URL = 'https://api.apixu.com'

FORECAST_ICONS = {
    1000: u'☼',  # Sunny, Clear
    1003: u'⛅',  # Partly cloudy
    1006: u'☁',  # Cloudy
    1009: u'☁',  # Overcast
    1030: u'⛆',  # Mist
    1063: u'☂',  # Patchy rain possible
    1066: u'☂❄',  # Patchy snow possible
    1069: u'☂',  # Patchy sleet possible
    1072: u'☂',  # Patchy freezing drizzle possible
    1087: u'⛈',  # Thundery outbreaks possible
    1114: u'❄',  # Blowing snow
    1117: u'❄❄',  # Blizzard
    # 1135: Fog
    # 1147: Freezing Fog
    1150: u'☂',  # Patchy light drizzle
    1153: u'☔',  # Light drizzle
    1168: u'☔',  # Freezing drizzle
    1171: u'⛆',  # Heavy freezing drizzle
    1180: u'☂',  # Patchy light rain
    1183: u'☔',  # Light rain
    1186: u'⛆',  # Moderate rain at times
    1189: u'⛆',  # Moderate rain
    1192: u'⛆',  # Heavy rain at times
    1195: u'⛆',  # Heavy rain
    1198: u'☔',  # Light freezing rain
    1201: u'⛆',  # Moderate or heavy freezing rain
    1204: u'☔',  # Light sleet
    1207: u'⛆',  # Moderate or heavy sleet
    1210: u'❄',  # Patchy light snow
    1213: u'❄',  # Light snow
    1216: u'❄',  # Patchy moderate snow
    1219: u'❄',  # Moderate snow
    1222: u'❄',  # Patchy heavy snow
    1225: u'❄❄',  # Heavy snow
    # 1237: Ice pellets
    1240: u'☔',  # Light rain shower
    1243: u'☔',  # Moderate or heavy rain shower
    1246: u'⛆',  # Torrential rain shower
    1249: u'☔',  # Light sleet showers
    1252: u'⛆',  # Moderate or heavy sleet showers
    1255: u'❄',  # Light snow showers
    1258: u'❄',  # Moderate or heavy snow showers
    # 1261: Light showers of ice pellets
    # 1264: Moderate or heavy showers of ice pellets
    1273: u'⛈',  # Patchy light rain with thunder
    1276: u'⛆⛈',  # Moderate or heavy rain with thunder
    1279: u'❄⛈',  # Patchy light snow with thunder
    1282: u'❄⛈❄',  # Moderate or heavy snow with thunder
}


class WeatherException(Exception):

  def __init__(self, code, message):
    super(WeatherException, self).__init__('Error code %s: "%s"' % (code,
                                                                    message))


class WeatherLib(object):

  def __init__(self, proxy: proxy_lib.Proxy, api_key: str,
               base_url: str = _BASE_URL):
    self._proxy = proxy
    self._api_key = api_key
    self._base_url = base_url.rstrip('/')

  def _CallApi(self, url: str, request_params: Optional[dict] = None):
    if not request_params:
      request_params = {}
    request_params['key'] = self._api_key
    response = self._proxy.FetchJson(
        url, params=request_params, force_lookup=True)
    # This code will not be executed since the API returns a 400.
    if 'error' in response:
      raise WeatherException(response['error'].get('code'),
                             response['error'].get('message'))
    return response

  def GetForecast(self, location: str, days: int = 7):
    """Get weather forecast for the location.

    Forecast consists of the current conditions and predictions for the future.

    Args:
      location: Location in human readable form.
      days: Number of days to fetch forecast.

    Returns:
      WeatherProto, actually a dict, with condition and forecast filled in.
    """
    url = '%s/v1/forecast.json' % self._base_url
    request_params = {
        'q': location,
        'days': days,
    }

    response = self._CallApi(url, request_params)
    if not response:
      return None

    weather = weather_pb2.Weather(
        location=_FormatLocation(response['location']),
        current=weather_pb2.Current(
            temp_f=response['current']['temp_f'],
            condition=_FormatCondition(response['current']['condition'])))

    for day in response['forecast']['forecastday']:
      weather.forecast.add(
          min_temp_f=day['day']['mintemp_f'],
          max_temp_f=day['day']['maxtemp_f'],
          condition=_FormatCondition(day['day']['condition']))

    return weather

  def GetHistory(self, location: str, unused_days: int = 1):
    """Get historical weather data for the location for the past n days.

    Args:
      location: Location in human readable form.
      unused_days: Ignored. Number of days in the past to fetch results.

    Returns:
      WeatherProto, actually a dict, with hindsight filled in.
    """
    url = '%s/v1/history.json' % self._base_url
    historical_day = arrow.now().shift(days=-1)
    request_params = {
        'q': location,
        'dt': historical_day.format('YYYY-MM-DD'),
    }
    response = self._CallApi(url, request_params)
    if not response:
      return None

    weather = weather_pb2.Weather(
        location=_FormatLocation(response['location']))

    for day in response['forecast']['forecastday']:
      weather.hindsight.add(
          min_temp_f=day['day']['mintemp_f'],
          max_temp_f=day['day']['maxtemp_f'],
          condition=_FormatCondition(day['day']['condition']))
    return weather


def _FormatLocation(location):
  if location['country'] in ['United States of America', 'USA', 'Murrica']:
    return '%s, %s' % (location['name'], location['region'])
  return '%s, %s' % (location['name'], location['country'])


def _FormatCondition(condition):
  if condition['code'] in FORECAST_ICONS:
    # Extra space after symbol since unicode characters are too wide.
    return u'%s %s ' % (condition['text'], FORECAST_ICONS[condition['code']])
  return condition['text']
