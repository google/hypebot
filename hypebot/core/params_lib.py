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

Parameter keys ending with `channel` or `channels` are special and converted
into Channel protos.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import os

from absl import logging
from hypebot.protos import channel_pb2
import six


def _ParseChannel(channel):
  """Parse a single messy definition of a channel into a Channel proto.

  Parsing:
    * If a Channel, return as is.
    * If a string, convert into a public channel with id equal to the string.
    * If a dictionary or HypeParams object, convert into a public channel with
      the matching fields set.

  Args:
    channel: The messy object to convert into a channel.

  Returns:
    Channel or None if it failed to parse.
  """
  if isinstance(channel, channel_pb2.Channel):
    return channel
  if isinstance(channel, HypeParams):
    channel = channel.AsDict()
  if isinstance(channel, dict):
    try:
      return channel_pb2.Channel(visibility=channel_pb2.Channel.PUBLIC,
                                 **channel)
    except KeyError:
      logging.error('Failed to parse %s as a Channel', channel)
      return None
  if isinstance(channel, six.string_types):
    return channel_pb2.Channel(visibility=channel_pb2.Channel.PUBLIC,
                               id=channel, name=channel)
  return None


def _ParseChannels(channels):
  """Parse channels from params.

  In multiple places it is useful to specify a list of channels in HypeParams.
  However, when parsing HypeParams, dictionaries within lists are treated as
  dictionaries and not as HypeParams or as a definable proto type. This converts
  a messy definition of channels within HypeParams into a consist list of actual
  Channel protos.

  Logic:
    * If None, return None.
    * If a non-list object, convert into a single element list.
    * If a list, parse each element of the list into a channel.

  Args:
    channels: Messy definition of a list of channels.

  Returns:
    None or a List of Channel protos.
  """
  if channels is None:
    return None
  if isinstance(channels, list):
    channels = [_ParseChannel(channel) for channel in channels]
  else:
    channels = [_ParseChannel(channels)]
  return [c for c in channels if c is not None]


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
    """Assigns value to key and converts dict values to HypeParams.

    Keys which end in `channel` or `channels` are special and get converted into
    Channel protos.

    Args:
      key: Key to set in internal dictionary.
      value: Value to assign to key in internal dictionary.
    """
    if key.endswith('channel'):
      self.__dict__[key] = _ParseChannel(value)
    elif key.endswith('channels'):
      self.__dict__[key] = _ParseChannels(value)
    elif isinstance(value, dict):
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
