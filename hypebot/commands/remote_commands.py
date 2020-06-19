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

import random

from absl import logging
import arrow

from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import inflect_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.plugins import vegas_game_lib
from hypebot.plugins import weather_lib
from hypebot.protos import channel_pb2
from hypebot.protos import message_pb2
from hypebot.protos import stock_pb2
from hypebot.protos import user_pb2
from typing import Text


@command_lib.CommandRegexParser(r'(?:crypto)?kitties sales')
class KittiesSalesCommand(command_lib.BaseCommand):
  """Humor brcooley."""

  def _Handle(self, channel: channel_pb2.Channel,
              user: user_pb2.User) -> hype_types.CommandResponse:
    data = self._core.proxy.FetchJson(
        'https://kittysales.herokuapp.com/data', {
            'offset': 0,
            'count': 1
        },
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


@command_lib.CommandRegexParser(r'(?:news|headlines)(?: (.*))?')
class NewsCommand(command_lib.BaseCommand):
  """If it's on the internet, it must be true."""

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              query: Text) -> hype_types.CommandResponse:
    if not query:
      raw_results = self._core.news.GetTrending()
      return self._BuildHeadlineCard('Here are today\'s top stories',
                                     raw_results)

    raw_results = self._core.news.GetHeadlines(query)
    return self._BuildHeadlineCard('Stories about "%s"' % query, raw_results)

  def _BuildHeadlineCard(self, header_text, raw_results):
    card = message_pb2.Card(
        header=message_pb2.Card.Header(
            title=header_text, image=self._core.news.icon),
        visible_fields_count=6)

    sorted_results = sorted(
        raw_results,
        key=lambda x: x.get('pub_date', arrow.get(0)),
        reverse=True)
    for article in sorted_results:
      field = message_pb2.Card.Field(text=article['title'])
      if article.get('pub_date'):
        field.title = 'Published %s ago' % util_lib.TimeDeltaToHumanDuration(
            arrow.utcnow() - arrow.get(article['pub_date']))
      source = article.get('source')
      if source and source != self._core.news.source:
        field.bottom_text = source
      card.fields.append(field)
      card.fields.append(
          message_pb2.Card.Field(buttons=[
              message_pb2.Card.Field.Button(
                  text='Read article', action_url=article['url'])
          ]))

    return card


@command_lib.CommandRegexParser(r'pop(?:ulation)?\s*(.*)')
class PopulationCommand(command_lib.BaseCommand):
  """Returns populations for queried regions."""

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              query: Text) -> hype_types.CommandResponse:
    if not query:
      return message_pb2.Card(
          header=message_pb2.Card.Header(
              title='usage: %spopulation [region_id]' % self.command_prefix),
          fields=[
              message_pb2.Card.Field(
                  text=('Population data is provided by The World Bank, the US '
                        'Census Bureau, and viewers like you.'))
          ])

    region_name = self._core.population.GetNameForRegion(query)
    if not region_name:
      return 'I don\'t know where that is, so I\'ll say {:,} or so.'.format(
          random.randint(1, self._core.population.GetPopulation('world')))

    provider = 'US Census Bureau' if self._core.population.IsUSState(
        query) else 'The World Bank'
    return message_pb2.Card(fields=[
        message_pb2.Card.Field(
            text='{} has a population of {:,}'.format(
                region_name, self._core.population.GetPopulation(query)),
            title='Source: %s' % provider)
    ])


@command_lib.CommandRegexParser(r'stocks?(?: (.*))?')
class StocksCommand(command_lib.BaseCommand):
  """Stonks go up."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'enable_betting': True,
      })

  def __init__(self, *args):
    super(StocksCommand, self).__init__(*args)
    if self._params.enable_betting:
      self._game = vegas_game_lib.StockGame(self._core.stocks)
      self._core.betting_games.append(self._game)

      self._core.scheduler.DailyCallback(
          util_lib.ArrowTime(16, 0, 30, 'America/New_York'), self._BetCallback)

  def _BetCallback(self):
    notifications = self._core.bets.SettleBets(self._game,
                                               self._core.name.lower(),
                                               self._Reply)
    if notifications:
      self._core.PublishMessage('stocks', notifications)

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              symbols: Text):
    symbols = symbols or self._core.user_prefs.Get(user, 'stocks')
    symbols = self._core.stocks.ParseSymbols(symbols)
    quotes = self._core.stocks.Quotes(symbols)
    if 'HYPE' in symbols:
      quotes['HYPE'] = stock_pb2.Quote(
          symbol='HYPE', price=13.37, change=4.2, change_percent=45.80)
    if not quotes:
      if symbols[0].upper() == self._core.name.upper():
        return ('You can\'t buy a sentient AI for some vague promise of future '
                'value, peon.')
      else:
        return ('You can\'t trade money for %s openly, try the black market.' %
                symbols[0])

    responses = []
    histories = self._core.stocks.History(symbols)
    if 'HYPE' in symbols:
      histories['HYPE'] = [1, 2, 4, 8]
    for symbol in symbols:
      if symbol not in quotes:
        continue
      if len(responses) >= 5:
        responses.insert(
            0,
            'Only displaying 5 quotes, I\'m a(n) %s not a financial advisor' %
            self._core.name)
        break
      quote = quotes[symbol]
      history = histories.get(symbol)
      change_str = self._FormatChangeStr(quote.change, quote.change_percent)
      response = 'One share of %s is currently worth %0.2f%s' % (
          symbol, quote.price, change_str)
      if quote.extended_change:
        ext_change_str = self._FormatChangeStr(quote.extended_change,
                                               quote.extended_change_percent)
        response += ' [ext: %0.2f%s]' % (quote.extended_price, ext_change_str)
      if history:
        response += ' %s' % util_lib.Sparkline(history)
      responses.append(response)
    return responses

  def _FormatChangeStr(self, change, percent):
    if not change and not percent:
      return ''
    change_str = ' %0.2f (%0.2f%%)' % (change, percent)
    if change > 0:
      change_str = util_lib.Colorize('⬆%s' % change_str, 'green')
    elif change < 0:
      change_str = util_lib.Colorize('⬇%s' % change_str, 'red')
    return change_str


@command_lib.CommandRegexParser(
    r'(?:virus|covid|corona(?:virus)?)(full)?[- ]?(.+)?')
class VirusCommand(command_lib.BaseCommand):
  """How bad is it now?"""

  _API_URL = 'https://covidtracking.com/api/'

  def _Handle(self, unused_channel, unused_user, detailed, region):
    endpoint = 'us'
    if region:
      region = region.upper()
      endpoint = 'states'
    region = region or 'USA'
    raw_results = self._core.proxy.FetchJson(self._API_URL + endpoint)
    logging.info('CovidAPI raw_result: %s', raw_results)
    if not raw_results:
      return 'Unknown region, maybe everyone should move there.'

    state_data = {}
    if len(raw_results) == 1:
      state_data = raw_results[0]
    else:
      state_data = [state for state in raw_results
                    if state.get('state') == region][0]

    if not state_data:
      return 'Unknown region, maybe everyone should move there.'

    # Raw data
    cases = state_data.get('positive', 0)
    tests = state_data.get('totalTestResults', 0)
    hospitalized = state_data.get('hospitalizedCurrently', 0)
    ventilators = state_data.get('onVentilatorCurrently', 0)
    icu_patients = state_data.get('inIcuCurrently', 0)
    deaths = state_data.get('death', 0)
    population = self._core.population.GetPopulation(region)
    if detailed:
      fields = []
      if cases:
        fields.append(self._InfoField('Confirmed cases', cases, population))
      if tests:
        fields.append(self._InfoField('Tests administered', tests, population))
      if hospitalized:
        fields.append(self._InfoField('Hospitalized', hospitalized, population))
      if icu_patients:
        fields.append(self._InfoField('ICU patients', icu_patients, population))
      if ventilators:
        fields.append(
            self._InfoField('Ventilators in use', ventilators, population))
      if deaths:
        fields.append(self._InfoField('Deaths', deaths, population))

      update_time = state_data.get('dateChecked') or state_data.get(
          'lastModified')
      update_time_str = 'some time'
      if update_time:
        update_timedelta = arrow.utcnow() - arrow.get(update_time)
        update_time_str = util_lib.TimeDeltaToHumanDuration(update_timedelta)

      fields.append(
          message_pb2.Card.Field(buttons=[
              message_pb2.Card.Field.Button(
                  text='Source', action_url='https://covidtracking.com/')
          ]))
      return message_pb2.Card(
          header=message_pb2.Card.Header(
              title='%s COVID-19 Statistics' %
              self._core.population.GetNameForRegion(region),
              subtitle='Updated %s ago' % update_time_str),
          fields=fields,
          visible_fields_count=4)

    deaths, descriptor = inflect_lib.Plural(deaths, 'death').split()
    death_str = '{:,} {}'.format(int(deaths), descriptor)

    cases, descriptor = inflect_lib.Plural(cases,
                                           'confirmed cases').split(maxsplit=1)
    case_str = '{:,} {}'.format(int(cases), descriptor)

    tests, descriptor = inflect_lib.Plural(tests, 'test').split()
    percent_tested = float(tests) / population
    test_str = '{:,} [{:.1%} of the population] {}'.format(
        int(tests), percent_tested, descriptor)

    return '%s has %s (%s) with %s administered.' % (
        region or 'The US', case_str, death_str, test_str)

  def _InfoField(self, title, value, population=None):
    value_str = '{:,}'.format(value)
    if population:
      percent = float(value) / population
      if percent >= 0.0005:
        value_str += ' [{:.1%} of the population]'.format(percent)
    return message_pb2.Card.Field(title=title, text=value_str)


@command_lib.CommandRegexParser(r'weather(?:-([kfc]))?(?: (.*))?')
class WeatherCommand(command_lib.BaseCommand):
  """Okay Google, what's the weather?"""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'forecast_days': ['Today', 'Tomorrow', 'The next day'],
          'geocode_key': None,
          'darksky_key': None,
      })

  _ICON_URL = 'https://darksky.net/images/weather-icons/%s.png'

  def __init__(self, *args):
    super(WeatherCommand, self).__init__(*args)  # pytype: disable=wrong-arg-count
    self._weather = weather_lib.WeatherLib(self._core.proxy,
                                           self._params.darksky_key,
                                           self._params.geocode_key)

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              unit: Text, location: Text):
    unit = unit or self._core.user_prefs.Get(user, 'temperature_unit')
    unit = unit.upper()
    location = location or self._core.user_prefs.Get(user, 'location')
    # Override airport code from pacific.
    if location.lower() == 'mtv':
      location = 'mountain view, CA'

    weather = self._weather.GetForecast(location)
    if not weather:
      return 'Unknown location.'

    card = message_pb2.Card(
        header=message_pb2.Card.Header(
            title=weather.location,
            subtitle='%s and %s' %
            (self._FormatTemp(weather.current.temp_f, unit),
             weather.current.condition),
            image={
                'url': self._ICON_URL % weather.current.icon,
                'alt_text': weather.current.icon,
            }))

    for index, day in enumerate(
        weather.forecast[:len(self._params.forecast_days)]):
      card.fields.add(
          icon_url=self._ICON_URL % day.icon,
          text='%s: %s - %s %s' %
          (self._params.forecast_days[index],
           self._FormatTemp(day.min_temp_f, unit),
           self._FormatTemp(day.max_temp_f, unit), day.condition))

    return card

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
      raw_str = '%.1f°C' % ((temp_f - 32) * 5 / 9)
    elif unit == 'K':
      raw_str = '%.1fK' % ((temp_f - 32) * 5 / 9 + 273.15)
    else:
      raw_str = '%.0f°F' % temp_f
    return util_lib.Colorize(raw_str, color, irc=False)
