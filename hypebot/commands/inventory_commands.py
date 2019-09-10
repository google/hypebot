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
"""Commands for inventory usage."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial

from hypebot.commands import command_lib
from hypebot.plugins import inventory_lib


# TODO: This should probably be moved to inflect_lib.
def FormatStacks(item_params):
  if item_params['number'] > 1:
    return ' (x%d)' % item_params['number']
  return ''


@command_lib.CommandRegexParser(r'inventory ?(.+)?')
class InventoryList(command_lib.BaseCommand):

  def _Handle(self, channel, user, inventory_user):
    inventory_user = inventory_user or user
    if inventory_user == 'me':
      self._core.last_command = partial(self._Handle,
                                        inventory_user=inventory_user)
      inventory_user = user
    inventory = self._core.inventory.GetUserInventory(inventory_user)
    if not inventory:
      return '%s\'s backpack has a hole in the bottom' % inventory_user
    msgs = ['%s\'s inventory:' % inventory_user]
    for key, params in inventory.items():
      item = inventory_lib.Create(key, self._core, inventory_user, params)
      msgs.append('%s%s' % (item.human_name, FormatStacks(params)))
    # TODO: Worry about putting multiple items on a single line if
    # inventories become large.
    return msgs


@command_lib.CommandRegexParser(r'use (.+)')
class InventoryUse(command_lib.BaseCommand):

  @command_lib.LimitPublicLines()
  def _Handle(self, channel, user, item_name):
    inventory = self._core.inventory.GetUserInventory(user)
    for key, params in inventory.items():
      item = inventory_lib.Create(key, self._core, user, params)
      if item_name.lower() == item.human_name.lower():
        msg, should_delete = item.Use()
        if should_delete:
          self._core.inventory.RemoveItem(user, item)
        return msg
    return 'You try to use your %s, but it was just a dream.' % item_name
