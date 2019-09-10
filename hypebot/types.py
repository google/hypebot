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
"""Core types for hypebot."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.protos import channel_pb2
from hypebot.protos import message_pb2

from typing import Dict, List, Text, Union

# Type aliases are named like classes, but pylint thinks they're variables, so
# we have to disable name checking here.
# pylint: disable=invalid-name

# Message type to send to interfaces.
Message = message_pb2.MessageList

Channel = channel_pb2.Channel

User = Text

# Union of valid targets to send Reply/Output.
Target = Union[User, Channel]

# These types will technically allow e.g. {'foo': {'bar': MyNonJsonObject}} but
# this is close enough.
BaseJsonType = Union[str, bytes, int, float, dict, list]
JsonType = Union[Dict[Text, BaseJsonType], List[BaseJsonType], BaseJsonType]


def MakeTextMessage(message: Text) -> Message:
  return Message(messages=[message_pb2.Message(text=message)])
