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
"""Monitor your networth in almost real time."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
from collections import namedtuple
from typing import Dict, List, Text
import re

from six import with_metaclass

from hypebot.core import params_lib


class StockQuote(namedtuple('StockQuote', 'price change percent')):
  """Current stock quote value.

  Fields:
    price: float Latest price for stock in USD.
    change: float Price change since opening in USD.
    percent: float Percent change of stock price since opening. 0-100 scale.
  """


class StockLib(with_metaclass(abc.ABCMeta)):
  """Base class for getting stock information."""

  DEFAULT_PARAMS = params_lib.HypeParams({})

  def __init__(self, params):
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    self._params.Lock()

  def ParseSymbols(self, symbols_str: Text) -> List[Text]:
    """Convert incoherent user input into a list of stock symbols."""
    symbols = re.split(r'[\s,;|+\\/]+', symbols_str.upper())
    return [s for s in symbols if s]

  @abc.abstractmethod
  def Quotes(self,
             symbols: List[Text]) -> Dict[Text, StockQuote]:
    """Fetches current quote data for each symbol.

    Stocks which aren't found, are not added to the return dict.

    Args:
      symbols: List of symbols to research.
    Returns:
      Dict keyed on symbol of quotes.
    """

  @abc.abstractmethod
  def History(self,
              symbols: List[Text],
              span: Text) -> Dict[Text, List[float]]:
    """Fetches daily historical data for each symbol.

    Stocks which aren't found, are not added to the return dict.

    Args:
      symbols: List of symbols to research.
      span: Timespan of days to fetch.
    Returns:
      Dict keyed on symbol of historical closing values.
    """

