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
"""Creates desired proxy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.core import factory_lib
from hypebot.proxies import proxy_lib

# pylint: disable=unused-import,g-bad-import-order
from hypebot.proxies import empty_proxy
from hypebot.proxies import requests_proxy
# pylint: enable=unused-import,g-bad-import-order

_factory = factory_lib.Factory(proxy_lib.Proxy)
# Creates a proxy instance for the registered name.
Create = _factory.Create  # pylint: disable=invalid-name
