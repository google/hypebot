# coding=utf-8
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
"""Commands that interface with a remote library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot import types
from hypebot.commands import command_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.plugins import weather_lib


@command_lib.CommandRegexParser(r'(?:crypto)?kitties sales')
class KittiesSalesCommand(command_lib.BaseCommand):
  """Humor brcooley."""

  @command_lib.MainChannelOnly
  def _Handle(self, channel: types.Channel, user: str):
    data = self._core.proxy.FetchJson(
        'https://kittysales.herokuapp.com/data', {'offset': 0, 'count': 1},
        force_lookup=True)
    if data:
      totals = data['totals']
      num_kitties = util_lib.FormatHypecoins(totals['sales'], True)[:-1]
      usd = util_lib.FormatHypecoins(totals['usdSold'], True)[:-1]
      eth = util_lib.FormatHypecoins(totals['etherSold'], True)[:-1]
      return 'There have been %s cryptokitties sold for $%s [Ξ %s]' % (
          num_kitties, usd, eth)
    else:
      return 'I don\'t know right now, but we\'ll say, a lot.'


@command_lib.CommandRegexParser(r'stocks?(?: (.*))?')
class StocksCommand(command_lib.BaseCommand):

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: types.Channel,
              unused_user: str,
              symbols: str):
    symbols = symbols or 'GOOG,GOOGL'
    symbols = self._core.stocks.ParseSymbols(symbols)
    quotes = self._core.stocks.Quotes(symbols)
    if not quotes:
      if symbols[0].upper() == self._core.nick.upper():
        return ('You can\'t buy a sentient AI for some vague promise of future '
                'value, peon.')
      else:
        return ('You can\'t trade money for %s openly, try the black market.' %
                symbols[0])

    responses = []
    if len(quotes) > 5:
      responses.append(
          'Only displaying 5 quotes, I\'m a(n) %s not a financial advisor' %
          self._core.nick)
    histories = self._core.stocks.History(symbols)
    for symbol, quote in list(quotes.items())[:5]:
      history = histories.get(symbol)
      change_str = '%0.2f (%0.2f%%)' % (quote.change, quote.percent)
      if quote.change > 0:
        change_str = util_lib.Colorize(u'⬆ %s' % change_str, 'green')
      elif quote.change < 0:
        change_str = util_lib.Colorize(u'⬇ %s' % change_str, 'red')
      if history:
        change_str += ' %s' % util_lib.Sparkline(history)
      responses.append('One share of %s is currently worth %0.2f [%s]' %
                       (symbol, quote.price, change_str))
    return responses


@command_lib.CommandRegexParser(r'weather(?:-([kfc]))?(?: (.*))?')
class WeatherCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          'forecast_days': ['Today', 'Tomorrow', 'The next day'],
          'apixu_key': None,
      })

  def __init__(self, *args):
    super(WeatherCommand,
          self).__init__(*args)  # pytype: disable=wrong-arg-count
    self._weather = weather_lib.WeatherLib(self._core.proxy,
                                           self._params.apixu_key)

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: types.Channel,
              unused_user: str,
              unit: str,
              location: str):
    unit = unit or 'F'
    unit = unit.upper()
    location = location or 'mountain view'
    # Override airport code from pacific.
    if location.lower() == 'mtv':
      location = 'mountain view'

    weather = self._weather.GetForecast(location,
                                        days=len(self._params.forecast_days))
    if not weather:
      return 'Unknown location.'

    responses = []
    responses.append('Currently %s and %s in %s' %
                     (self._FormatTemp(weather.current.temp_f, unit),
                      weather.current.condition,
                      weather.location))

    weather.MergeFrom(self._weather.GetHistory(location, unused_days=1))
    if weather.hindsight:
      yesterday = weather.hindsight[0]
      responses.append('Yesterday: %s (%s - %s)' % (
          yesterday.condition,
          self._FormatTemp(yesterday.min_temp_f, unit),
          self._FormatTemp(yesterday.max_temp_f, unit)))

    for index, day in enumerate(weather.forecast):
      condition_str = '%s: %s' % (
          self._params.forecast_days[index],
          day.condition)
      temp_str = '(%s - %s)' % (
          self._FormatTemp(day.min_temp_f, unit),
          self._FormatTemp(day.max_temp_f, unit))
      if index == 0:
        condition_str = util_lib.Bold(condition_str)
      responses.append('%s %s' % (condition_str, temp_str))

    return responses

  def _FormatTemp(self, temp_f, unit):
    color = ''
    if temp_f <= 10:
      color = 'cyan'
    elif temp_f <= 32:
      color = 'blue'
    elif temp_f >= 100:
      color = 'red'
    elif temp_f >= 80:
      color = 'orange'

    if unit == 'C':
      raw_str = u'%.1f°C' % ((temp_f - 32) * 5 / 9)
    elif unit == 'K':
      raw_str = u'%.1fK' % ((temp_f - 32) * 5 / 9 + 273.15)
    else:
      raw_str = u'%.1f°F' % temp_f
    return util_lib.Colorize(raw_str, color)
