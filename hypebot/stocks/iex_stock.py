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

from typing import Dict, List, Text

from hypebot.core import params_lib
from hypebot.protos import stock_pb2
from hypebot.stocks import stock_lib


class IEXStock(stock_lib.StockLib):
  """Data provided for free by IEX."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      stock_lib.StockLib.DEFAULT_PARAMS,
      {
          'base_url': 'https://api.iextrading.com/1.0/stock/market/batch',
      })

  def __init__(self, params, proxy):
    super(IEXStock, self).__init__(params)
    self._proxy = proxy

  def Quotes(self,
             symbols: List[Text]) -> Dict[Text, stock_pb2.Quote]:
    """See StockLib.Quotes for details."""
    request_params = {
        'symbols': ','.join(symbols),
        'types': 'quote',
        'displayPercent': 'true',  # Keep string, not boolean.
    }
    response = self._proxy.FetchJson(self._params.base_url,
                                     params=request_params,
                                     force_lookup=True)

    stock_info = {}
    for symbol, data in response.items():
      quote = data['quote']

      stock_info[symbol] = stock_pb2.Quote(
          symbol=symbol,
          open=quote.get('open', 0),
          close=quote.get('close', 0),
          price=quote.get('latestPrice', 0),
          change=quote.get('change', 0),
          change_percent=quote.get('changePercent', 0),
          extended_price=quote.get('extendedPrice', 0),
          extended_change=quote.get('extendedChange', 0),
          extended_change_percent=quote.get('extendedChangePercent', 0))
    return stock_info

  def History(self,
              symbols: List[Text],
              span: Text = '1m') -> Dict[Text, List[float]]:
    """See StockLib.History for details."""
    request_params = {
        'symbols': ','.join(symbols),
        'types': 'chart',
        'range': span,
    }
    response = self._proxy.FetchJson(self._params.base_url,
                                     params=request_params,
                                     force_lookup=True)
    stock_info = {}
    for symbol, data in response.items():
      stock_info[symbol] = [day['close'] for day in data['chart']][-5:]
    return stock_info
