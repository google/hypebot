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
"""Factory for building interfaces.

Hypebot is like Amumu and wants friends. Hypebot wants to talk to you.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.core import factory_lib
from hypebot.interfaces import interface_lib

# pylint: disable=unused-import
# Importing commands registers them with factory.
import hypebot.interfaces.capture_interface
import hypebot.interfaces.discord_interface
import hypebot.interfaces.terminal_interface
# pylint: enable=usused-import


_factory = factory_lib.Factory(interface_lib.BaseChatInterface)
Create = _factory.Create  # pylint: disable=invalid-name
CreateFromParams = _factory.CreateFromParams  # pylint: disable=invalid-name
