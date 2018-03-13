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
"""Library for inflection.

Verb:
  change the form of (a word) to express a particular grammatical function or
  attribute, typically tense, mood, person, number, case, and gender.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inflection


def Ordinalize(number: int) -> str:
  """Converts an int into the ordinal string representation.

  Args:
    number: Number to convert.
  Returns:
    Ordinal representation. E.g., 1st, 2nd, 3rd.
  """
  if 10 < number < 20:
    return 'th'
  elif number % 10 == 1:
    return 'st'
  elif number % 10 == 2:
    return 'nd'
  elif number % 10 == 3:
    return 'rd'
  else:
    return 'th'


def Plural(quantity: int, noun: str, plural: str = None) -> str:
  """Formats a quanity of a noun correctly.

  Args:
    quantity: Amount of noun to format.
    noun: Singular form of noun to format.
    plural: Optional plural form of noun if it is too special for us to handle
      with normal English rules.
  Returns:
    Quantity of noun: e.g., 0 houses, 1 house, 2 houses.
  """
  if quantity != 1:
    noun = plural if plural else inflection.pluralize(noun)
  return '%d %s' % (quantity, noun)
