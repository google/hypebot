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
"""Use IEX for stock data.

https://iextrading.com/developer/
https://iextrading.com/api-exhibit-a/
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from typing import Dict, List, Text

from hypebot.core import params_lib
from hypebot.protos import stock_pb2
from hypebot.stocks import stock_lib


class IEXStock(stock_lib.StockLib):
  """Data provided for free by IEX."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      stock_lib.StockLib.DEFAULT_PARAMS,
      {
          'base_url': 'https://cloud.iexapis.com/v1',
          # Sign up for token at iexcloud.io
          'token': None,
      })

  def __init__(self, params, proxy):
    super(IEXStock, self).__init__(params)
    self._proxy = proxy

  def Quotes(self, symbols: List[Text]) -> Dict[Text, stock_pb2.Quote]:
    """See StockLib.Quotes for details."""
    request_params = {
        'symbols': ','.join(symbols),
        'types': 'quote',
        'displayPercent': 'true',  # Keep string, not boolean.
        'token': self._params.token,
    }
    response = self._proxy.FetchJson(
        os.path.join(self._params.base_url, 'stock/market/batch'),
        params=request_params,
        force_lookup=True)

    stock_info = {}
    for symbol, data in response.items():
      quote = data['quote']

      stock = stock_pb2.Quote(
          symbol=symbol,
          open=quote.get('open', 0),
          close=quote.get('previousClose', 0),
          price=quote.get('latestPrice', 0))
      # These fields may exist and be `null` in the JSON, so we set the default
      # outside of `get()`.
      stock.change = quote.get('change') or stock.price - stock.close
      stock.change_percent = quote.get('changePercent') or (
          stock.change / (stock.close or 1) * 100)
      realtime_price = quote.get('iexRealtimePrice')
      if realtime_price and realtime_price != stock.price:
        stock.extended_price = realtime_price
        stock.extended_change = realtime_price - stock.price
        stock.extended_change_percent = int(
            float(stock.extended_change) / stock.price * 100 + 0.5)
      if stock.price:
        stock_info[symbol] = stock

    # If it wasn't a stock symbol, try to look it up as a crypto.
    for symbol in set(symbols) - set(stock_info):
      response = self._proxy.FetchJson(
          os.path.join(self._params.base_url, 'crypto', symbol, 'price'),
          params={'token': self._params.token},
          force_lookup=True)
      if response:
        stock_info[symbol] = stock_pb2.Quote(
            symbol=symbol, price=float(response.get('price', 0)))

    return stock_info

  def History(self,
              symbols: List[Text],
              span: Text = '1m') -> Dict[Text, List[float]]:
    """See StockLib.History for details."""
    request_params = {
        'symbols': ','.join(symbols),
        'types': 'chart',
        'range': span,
        'token': self._params.token,
    }
    response = self._proxy.FetchJson(
        os.path.join(self._params.base_url, 'stock/market/batch'),
        params=request_params,
        force_lookup=True)
    stock_info = {}
    for symbol, data in response.items():
      stock_info[symbol] = [day['close'] for day in data['chart']][-5:]
    return stock_info
