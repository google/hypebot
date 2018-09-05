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
"""HypeBot Factory Pattern.

HypeBot uses a factory pattern for instantiating many parts of the bot. This
allows for specification of functionality via the params JSON string. E.g.,
commands or the chat application interface can be specified in the params and
the correct python object will be constructed.

The factory pattern uses auto-registration of all leaf classes (by default) or
all subclasses from a BaseClass.
E.g., With the following class hierarchy, only the commands marked with an
asterisk could be created through the factory unless register_internal_nodes is
set at factory creation time:

  BaseCommand
  - CoinCommand
  -- BalanceCommand *
  -- GiftCommand *
  - HypeCommand *

Here is an example of how to use the pattern.

vehicle_lib.py
---
class BaseVehicle(object):
  ...

bus.py
---
import vehicle_lib
class Bus(vehicle_lib.BaseVehicle):
  ...

cars.py
---
import vehicle_lib
class FordFocus(vehicle_lib.BaseVehicle):
  ...

vehicle_factory.py
---
import factory_lib
import vehicle_lib
import bus
import cars
_factory = factory_lib.Factory(vehicle_lib.BaseVehicle)
Create = _factory.Create

something_that_wants_a_vehicle.py
---
import vehicle_factory
vehicle = vehicle_factory.Create('FordFocus')
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from typing import Text

from hypebot.core import params_lib


class Factory(object):
  """Allows creation of magical goodness from strings."""

  def __init__(self, base_class, register_internal_nodes=False):
    self._base_class = base_class
    self._register_internal_nodes = register_internal_nodes
    self._registrar = {}

  def _Register(self, klass, register_internal_nodes):
    """Recursively register all valid subclasses of the klass."""
    for subclass in klass.__subclasses__():
      if register_internal_nodes or not subclass.__subclasses__():
        self._registrar[subclass.__name__] = subclass
      if subclass.__subclasses__():
        self._Register(subclass, register_internal_nodes)

  def Create(self, name: Text, *args, **kwargs):
    if name not in self._registrar:
      # Last minute re-registration to avoid import order issues.
      self._Register(self._base_class, self._register_internal_nodes)
      if name not in self._registrar:
        raise ValueError('Name %s does not exist in the registrar.' % name)
    return self._registrar[name](*args, **kwargs)

  def CreateFromParams(self,
                       params: params_lib.HypeParams,
                       *args, **kwargs):
    """Creates an instance of the class based on the params.

    Creates a new instance of the registered subclass for params.type. Assumes
    the subclass accepts a HypeParams object as the first argument to the ctor.

    params.AsDict() is assumed to have the following structure:
    {
        # Name in registrar of class to create.
        'type': 'CAR',

        # Parameters shared between all subclasses.
        'owner': 'HypeBot',

        # Parameters specific to different registered names/subclass.
        'CAR': {
            'wheels': 4,
        },
        'BUS': {
            'passengers': 60,
        },
    }

    Args:
      params: Parameters.
      *args: Additional arguments passed to the subclass' ctor.
      **kwargs: Keyword arguments passed to the subclass' ctor.

    Returns:
      Newly constructed instance of subclass registered to params.name.
    """
    name = params.type
    subclass_params = params.get(name, {})
    # Remove keys that are registered names and the special name key.
    params = params.AsDict()
    for key in list(params.keys()):
      if key in self._registrar.keys() or key == 'type':
        del params[key]

    # Recreate params with the subclass specific params raised to the top level.
    params = params_lib.HypeParams(params)
    params.Override(subclass_params)
    return self.Create(name, params, *args, **kwargs)
