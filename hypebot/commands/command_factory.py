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
"""Factory to create commands from parameters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hypebot.commands import command_lib
from hypebot.core import factory_lib

# pylint: disable=unused-import
# Importing commands before constructing the factory.
import hypebot.commands.bash_commands
import hypebot.commands.bling_commands
import hypebot.commands.deploy_commands
import hypebot.commands.hypecoin_commands
import hypebot.commands.hypestack_commands
import hypebot.commands.interface_commands
import hypebot.commands.inventory_commands
import hypebot.commands.league.lcs_commands
import hypebot.commands.league.lol_commands
import hypebot.commands.league.summoner_commands
import hypebot.commands.league.trivia_commands
import hypebot.commands.public_commands
import hypebot.commands.remote_commands
import hypebot.commands.simple_commands
# pylint: enable=usused-import

_factory = factory_lib.Factory(command_lib.BaseCommand)
# Creates a command instance for the registered name.
# ARGS:
#   name: {string} The registered name.
#   params: {HypeParams} Parameter overrides.
#   *args: Arguments to be passed to the subclass' constructor.
Create = _factory.Create  # pylint: disable=invalid-name
