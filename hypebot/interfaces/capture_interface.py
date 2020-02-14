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
"""Interface that captures messages sent as output."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from typing import List, Text

from hypebot import types
from hypebot.interfaces import interface_lib


class CaptureInterface(interface_lib.BaseChatInterface):
  """Interface that captures output."""

  def __init__(self, unused_params):
    """This interface ignores everything."""
    self._msgs = []  # type: List[Text]

  def MessageLog(self) -> Text:
    return '\n'.join(self._msgs)

  # =======================
  # BaseInterface overrides
  # =======================

  def Join(self, channel: types.Channel):
    """This interface does not interact with a chat application."""
    pass

  def Leave(self, channel: types.Channel):
    """This interface does not interact with a chat application."""
    pass

  def Loop(self):
    """This interface does not interact with a chat application."""
    pass

  def Who(self, unused_user: types.User):
    """This interface doesn't care about plebs."""
    pass

  def WhoAll(self):
    """This interface doesn't care about plebs."""
    pass

  def SendMessage(self, unused_channel: types.Channel, message: types.Message):
    for msg in message.messages:
      # Messages with only cards and no text will have had default text already
      # added by the HypeCore.
      self._msgs.extend(msg.text)

  def Notice(self, unused_channel: types.Channel,
             unused_message: types.Message):
    pass

  def Topic(self, unused_channel: types.Channel, unused_new_topic: Text):
    pass
