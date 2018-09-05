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
"""Proxy that uses requests."""

# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import requests

from hypebot.proxies import proxy_lib


class RequestsProxy(proxy_lib.Proxy):
  """Use python requests library to fetch urls."""

  def _GetUrl(self, url, params):
    try:
      req = requests.get(url,
                         params=params,
                         headers={'User-Agent': 'HypeBot'})
      if req.status_code != requests.codes.ok:
        self._LogError(url, req.status_code)
        return None
    except Exception as e:
      self._LogError(url, exception=e)
      return None
    return req.text
