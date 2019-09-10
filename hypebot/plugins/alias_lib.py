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
"""Library for pulling and formatting alias information.

Aliases are stored on a per-user basis. They are stored in a row keyed on that
user, each represented as a comma-separated list of strings.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

ALIAS_SUBKEY = 'user_aliases'
ME_REGEX = re.compile(r'\\me\b')
ALL_ARGS_REGEX = re.compile(r'\\@:?')
ALL_ARGS_RANGED_REGEX = re.compile(r'\\@(-?\d+)?:(-?\d+)?')
ARGS_REGEX = re.compile(r'\\\d+')


def GetAliases(store, user):
  return store.GetJsonValue(user, ALIAS_SUBKEY) or {}


def AddOrUpdateAlias(store, user, alias_name, alias_cmd):
  return store.UpdateJson(user, ALIAS_SUBKEY,
                          lambda a: a.update({alias_name: alias_cmd}),
                          lambda a: alias_name in a)


def RemoveAlias(store, user, alias_name):
  return store.UpdateJson(user, ALIAS_SUBKEY,
                          lambda a: a.pop(alias_name, None),
                          lambda a: alias_name in a)


def ExpandAliases(store, user, msg):
  r"""Replaces placeholders in an alias with the arguments from the alias.

  \me becomes the username of whoever invoked the command.
  \d+ is replaced with the arguments (words) that follow the alias.
    Unused placeholdes are discarded.

  Args:
    store: Reference to a HypeStore.
    user: whoever invoked the alias.
    msg: text that follows the alias.
  Returns:
    Expanded alias replacing placeholders with the given arguments.
  """

  aliases = GetAliases(store, user)
  msg_args = msg.split(' ')

  for alias_key, alias_value in aliases.items():
    if msg_args[0] == alias_key:
      transformed_msg = alias_value

      transformed_msg = ME_REGEX.sub(user, transformed_msg)
      transformed_msg = _ExpandAllSign(transformed_msg, msg_args[1:])
      transformed_msg = ALL_ARGS_REGEX.sub(' '.join(msg_args[1:]),
                                           transformed_msg)

      for i in range(1, len(msg_args)):
        transformed_msg = re.sub(r'\\%d(?=\D|$)' % i, r'%s' % msg_args[i],
                                 transformed_msg)
      transformed_msg = ARGS_REGEX.sub('', transformed_msg)
      # Hack to support deferred execution, provided you didn't actually want to
      # use { or } in your command.
      transformed_msg = transformed_msg.replace('{', '(').replace('}', ')')
      return transformed_msg

  return msg


def _ExpandAllSign(alias, msg_args):
  r"""Replaces \@ and \@<start>:<end> with all arguments or a range of them.

  * <start> and <end> are optional, and \@: is a valid placeholder which is
    equivalent to \@.
  * The ranges work like python slice notation, but <step> is not supported.

  Args:
    alias: alias message to replace the placeholders from.
    msg_args: arguments passed to the alias.
  Returns:
    Expanded alias replacing \@ placeholders with the given arguments.
  """
  for result in ALL_ARGS_RANGED_REGEX.finditer(alias):
    start = result.group(1) or ''
    end = result.group(2) or ''
    if not start and not end:
      continue  # `\@:` will be ignored because it will be processed as a `\@`.
    alias = re.sub(r'\\@%s:%s(?=\D|$)' % (start, end), ' '.join(
        msg_args[int(start) if start else None:int(end) if end else None]),
                   alias)

  return alias
