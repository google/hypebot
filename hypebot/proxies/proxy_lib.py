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
"""Library for performing HTTP requests."""

# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
from functools import partial
import json

from absl import logging
from six import with_metaclass

from hypebot.core import cache_lib
from hypebot.core import util_lib


class Proxy(with_metaclass(abc.ABCMeta)):
  """A class to proxy requests."""

  _STORAGE_SUBKEY = 'fetch_results'

  def __init__(self, store=None):
    self._request_cache = cache_lib.LRUCache(256, max_age=60 * 60)
    self._store = store

  @abc.abstractmethod
  def _GetUrl(self, url, params):
    """Fetches data from a specified URL.

    Args:
      url: (string) URL to request data from
      params: Dict of url GET params.

    Returns:
      HTTP response body if it exists, otherwise None
    """

  def FlushCache(self):
    self._request_cache.Flush()

  def RawFetch(self, key, action, validate_fn=None, force_lookup=False,
               use_storage=False):
    """Do action, checking cache/storage first and updating key if required.

    Actions are arbitrary functions that execute and return values. For example,
    an action could be a function that fetches an HTTP request and returns the
    response body's JSON.

    Args:
      key: The key associated with the action to perform.
      action: The action to perform if the result is not cached against the key.
      validate_fn: Callable that takes the result of action and validates if it
          should be cached. If not specified, any non-None return from action is
          cached.
      force_lookup: If this lookup should bypass the cache and storage lookup.
          Note that valid results will still be saved to the cache/storage.
      use_storage: If the results of this fetch should be written to a
          persistent storage layer. Useful when the data is not expected to
          change.
    Returns:
      The data or None if the action failed.
    """
    if not force_lookup:
      if use_storage and self._store:
        try:
          return_data = self._store.GetValue(key, self._STORAGE_SUBKEY)
          if return_data:
            return return_data
        except Exception as e:
          logging.error('Error fetching %s from storage: %s', key, e)
        logging.info('Storage missing %s', key)
      return_data = self._request_cache.Get(key)
      if return_data:
        return return_data
      logging.info('Cache miss for %s', key)

    return_data = action()
    if not validate_fn:
      validate_fn = lambda x: True

    if return_data and validate_fn(return_data):
      self._request_cache.Put(key, return_data)
      if use_storage and self._store:
        try:
          self._store.SetValue(key, self._STORAGE_SUBKEY, return_data)
        except Exception as e:
          logging.error('Error storing return_data: %s', e)
    return return_data

  def FetchJson(self, url, params={}, force_lookup=False, use_storage=False):
    """Returns a python-native version of a JSON response from url."""
    try:
      return json.loads(
          self.HTTPFetch(url, params, self._ValidateJson, force_lookup,
                         use_storage) or '{}')
    except Exception as e:  # pylint: disable=broad-except
      self._LogError(url, exception=e)
      return {}

  def _ValidateJson(self, return_data):
    """Validates if return_data should be cached by looking for an error key."""
    try:
      obj = json.loads(return_data or '{}')
      # Don't cache 200 replies with errors in the body
      return 'error' not in obj
    except Exception as e:
      logging.error('Failed to decode json object:\nError: %s\nRaw data:%s', e,
                    return_data)
    return False

  def HTTPFetch(self,
                url,
                params={},
                validate_fn=None,
                force_lookup=False,
                use_storage=False):
    """Fetch url, checking the cache/storage first and updating it if required.

    Args:
      url: The url to fetch data from.
      params: Data for URL query string.
      validate_fn: Function used to validate if the response should be cached.
      force_lookup: If this lookup should bypass the cache and storage lookup.
          Note that valid results will still be saved to the cache/storage.
      use_storage: If the results of this fetch should be written to a
          persistent storage layer. Useful when the data is not expected to
          change.
    Returns:
      The data or None if the fetch failed.
    """
    action = partial(self._GetUrl, url, params)
    return self.RawFetch(
        util_lib.SafeUrl(url),
        action,
        validate_fn,
        force_lookup=force_lookup,
        use_storage=use_storage)

  def _LogError(self, url, error_code=None, exception=None):
    """Logs an error in a standardized format."""
    safe_url = util_lib.SafeUrl(url)
    logging.error('Fetch for %s failed', safe_url)

    if error_code:
      logging.error('  Error code %s', error_code)
    if exception:
      logging.exception(exception)
