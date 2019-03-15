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
"""HypeParams.

HypeParams is a class for managing parameters with the following goals.

1. Initializable with a python dict, JSON string, or JSON file.
2. Overridable. Both by subclasses and at initialization.
3. Lockable. Once fully initialized, they should be constant.
4. Accessible. Dot notation is more readable than dict access with strings.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import os

import six


class HypeParams(object):
  """See file docstring for details."""

  SPECIAL_ATTRS = ['_locked']
  # Allow integration with static python type checking. Since HypeParams
  # dynamically sets its attributes, pytype needs guidance to know that pc.key1
  # is valid.
  HAS_DYNAMIC_ATTRIBUTES = True

  def __init__(self, defaults=None):
    if defaults is None:
      defaults = {}
    self._locked = False
    self.Override(defaults)

  def __str__(self):
    return str(self.AsDict())

  def Override(self, params):
    self._RaiseIfLocked()
    params_dict = self._ParseDict(params)
    for key, value in params_dict.items():
      if not isinstance(key, six.string_types):
        raise ValueError('HypeParams keys must all be strings. Encountered %s '
                         '(type: %s).' % (key, type(key)))
      self._AssignValueConvertDict(key, value)

  def _AssignValueConvertDict(self, key, value):
    """Assigns value to key and converts dict values to HypeParams."""
    if isinstance(value, dict):
      if (not hasattr(self, key) or
          not isinstance(self.__dict__[key], HypeParams)):
        self.__dict__[key] = HypeParams()
      self.__dict__[key].Override(value)
    else:
      self.__dict__[key] = value

  def _ParseDict(self, params):
    """Parses a dictionary from whatever.

    Handles HypeParams, Dict, JSON string, or JSON file.

    Args:
      params: Unknown type of params.

    Returns:
      Dict representation of params.

    Raises:
      ValueError: If JSON fails to parse.
    """
    if isinstance(params, HypeParams):
      return params.AsDict()
    if isinstance(params, six.string_types):
      if os.path.isfile(params):
        with open(params) as params_file:
          params = json.load(params_file)
      else:
        params = json.loads(params)
    return params or {}

  def __setattr__(self, key, value):
    self._RaiseIfLocked()
    if key not in list(self.__dict__.keys()) + self.SPECIAL_ATTRS:
      raise AttributeError('Unrecognized param: %s' % key)
    self._AssignValueConvertDict(key, value)

  # Lowercase name to make this match the dict method.
  def get(self, key, default_value=None):  # pylint: disable=invalid-name
    return self.__dict__.get(key, default_value)

  def AsDict(self):
    """Converts params into a dictionary."""
    params = {}
    for key, value in self.__dict__.items():
      if key in self.SPECIAL_ATTRS:
        continue
      params[key] = value.AsDict() if isinstance(value, HypeParams) else value
    return params

  def Lock(self):
    for value in self.__dict__.values():
      if isinstance(value, HypeParams):
        value.Lock()
    self._locked = True

  def _RaiseIfLocked(self):
    if hasattr(self, '_locked') and self._locked:
      raise AttributeError('HypeParams is locked.')


def MergeParams(defaults, *overrides):
  """Merges parameter containers."""
  params = HypeParams(defaults)
  for override in overrides:
    params.Override(override)
  return params
