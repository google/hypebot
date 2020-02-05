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
"""Allow hypebot to read the daily paper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc

from hypebot.core import params_lib
from six import with_metaclass

from typing import Any, Dict, List, Text


class NewsLib(with_metaclass(abc.ABCMeta)):
  """Base class for getting headlines."""

  DEFAULT_PARAMS = params_lib.HypeParams({})

  def __init__(self, params, proxy):
    self._params = params_lib.HypeParams(self.DEFAULT_PARAMS)
    self._params.Override(params)
    self._params.Lock()
    self._proxy = proxy

  @abc.abstractmethod
  def GetHeadlines(self,
                   query: Text,
                   max_results: int = 5) -> List[Dict[Text, Any]]:
    """Get headlines relating to query.

    Args:
      query: The query string to search for.
      max_results: The maximum number of headliens to return.

    Returns:
      List of dicts representing articles.
    """

  @abc.abstractmethod
  def GetTrending(self, max_results: int = 5) -> List[Dict[Text, Any]]:
    """Get the "front page" headlines at the current time.

    Args:
      max_results: The maximum nuber of headlines to return.

    Returns:
      List of Headline protos.
    """
