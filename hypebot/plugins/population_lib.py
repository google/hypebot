# Lint as: python3
# coding=utf-8
# Copyright 2020 The Hypebot Authors. All rights reserved.
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
"""Supply dank counts of humans."""

from typing import Optional, Text

from absl import logging
import arrow

from hypebot.core import schedule_lib
from hypebot.core import util_lib
from hypebot.proxies import proxy_lib

_DATA_URL = 'https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL'


class PopulationLib():
  """Class that serves up populations for various geographical regions."""

  # There are APIs for this, but for now hard-coded values are ok.
  # Data accurate as of 2020/03/22
  # Source:
  # https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/national/totals/nst-est2019-alldata.csv
  _US_STATE_NAMES = {
      'AL': 'Alabama',
      'AK': 'Alaska',
      'AZ': 'Arizona',
      'AR': 'Arkansas',
      'CA': 'California',
      'CO': 'Colorado',
      'CT': 'Connecticut',
      'DE': 'Delaware',
      'DC': 'District of Columbia',
      'FL': 'Florida',
      'GA': 'Georgia',
      'HI': 'Hawaii',
      'ID': 'Idaho',
      'IL': 'Illinois',
      'IN': 'Indiana',
      'IA': 'Iowa',
      'KS': 'Kansas',
      'KY': 'Kentucky',
      'LA': 'Louisiana',
      'ME': 'Maine',
      'MD': 'Maryland',
      'MA': 'Massachusetts',
      'MI': 'Michigan',
      'MN': 'Minnesota',
      'MS': 'Mississippi',
      'MO': 'Missouri',
      'MT': 'Montana',
      'NE': 'Nebraska',
      'NV': 'Nevada',
      'NH': 'New Hampshire',
      'NJ': 'New Jersey',
      'NM': 'New Mexico',
      'NY': 'New York',
      'NC': 'North Carolina',
      'ND': 'North Dakota',
      'OH': 'Ohio',
      'OK': 'Oklahoma',
      'OR': 'Oregon',
      'PA': 'Pennsylvania',
      'RI': 'Rhode Island',
      'SC': 'South Carolina',
      'SD': 'South Dakota',
      'TN': 'Tennessee',
      'TX': 'Texas',
      'UT': 'Utah',
      'VT': 'Vermont',
      'VA': 'Virginia',
      'WA': 'Washington',
      'WV': 'West Virginia',
      'WI': 'Wisconsin',
      'WY': 'Wyoming',
      'PR': 'Puerto Rico'
  }
  _US_STATE_POPULATIONS = {
      'AL': 4903185,
      'AK': 731545,
      'AZ': 7278717,
      'AR': 3017804,
      'CA': 39512223,
      'CO': 5758736,
      'CT': 3565287,
      'DE': 973764,
      'DC': 705749,
      'FL': 21477737,
      'GA': 10617423,
      'HI': 1415872,
      'ID': 1787065,
      'IL': 12671821,
      'IN': 6732219,
      'IA': 3155070,
      'KS': 2913314,
      'KY': 4467673,
      'LA': 4648794,
      'ME': 1344212,
      'MD': 6045680,
      'MA': 6892503,
      'MI': 9986857,
      'MN': 5639632,
      'MS': 2976149,
      'MO': 6137428,
      'MT': 1068778,
      'NE': 1934408,
      'NV': 3080156,
      'NH': 1359711,
      'NJ': 8882190,
      'NM': 2096829,
      'NY': 19453561,
      'NC': 10488084,
      'ND': 762062,
      'OH': 11689100,
      'OK': 3956971,
      'OR': 4217737,
      'PA': 12801989,
      'RI': 1059361,
      'SC': 5148714,
      'SD': 884659,
      'TN': 6829174,
      'TX': 28995881,
      'UT': 3205958,
      'VT': 623989,
      'VA': 8535519,
      'WA': 7614893,
      'WV': 1792147,
      'WI': 5822434,
      'WY': 578759,
      'PR': 3193694
  }

  def __init__(self, proxy: proxy_lib.Proxy):
    self._proxy = proxy
    self._scheduler = schedule_lib.HypeScheduler()
    self._ids_to_names = self._US_STATE_NAMES.copy()
    self._populations = self._US_STATE_POPULATIONS.copy()
    # 5am is an arbitrary time, can be changed without any semantic effect.
    self._scheduler.DailyCallback(
        util_lib.ArrowTime(5), self._UpdatePopulations)
    self._UpdatePopulations()

  def GetPopulation(self, raw_region: Text) -> int:
    """Gets the total population for raw_region, or 0 for unknown regions."""
    region = self._NormalizeId(raw_region)
    return self._populations.get(region, 0)

  def GetNameForRegion(self, raw_region: Text) -> Optional[Text]:
    """Takes user input and tries to convert it to a region."""
    region = self._NormalizeId(raw_region)
    return self._ids_to_names.get(region)

  def IsUSState(self, raw_region: Text) -> bool:
    """Returns if the region passed is a US state or not."""
    region = self._NormalizeId(raw_region)
    return region in self._US_STATE_NAMES

  def _UpdatePopulations(self):
    """Fetches new population data, and updates existing saved data."""
    cur_year = arrow.now().year
    raw_result = None
    try:
      raw_result = self._proxy.FetchJson(_DATA_URL, {
          'format': 'json',
          'source': '40',
          'per_page': '500',
          'date': cur_year
      })
    except Exception:  # pylint: disable=broad-except
      logging.exception('Failed to fetch population data')
    if not raw_result or len(raw_result) < 2:
      return

    raw_result = raw_result[1]
    ids_to_names = {}
    populations = {}
    for region_info in raw_result:
      if 'country' not in region_info:
        logging.warning('Got population entry with no country entry:\n%s',
                        region_info)
        continue
      if not region_info['value']:
        logging.info('Got population entry with null value:\n%s', region_info)
        continue
      country_info = region_info['country']
      ids_to_names[country_info['id']] = country_info['value']
      populations[country_info['id']] = region_info['value']

    self._ids_to_names.update(ids_to_names)
    self._populations.update(populations)
    logging.info('Populations updated')

  def _NormalizeId(self, raw_region: Text) -> Optional[Text]:
    """Takes a user-provided region and tries to map it to a valid region ID."""
    region = raw_region.upper().strip()
    if region in self._ids_to_names:
      return region
    # Title-casing because most country names are title-cased.
    region = region.title()
    names_to_ids = {v: k for k, v in self._ids_to_names.items()}
    if region in names_to_ids:
      return names_to_ids[region]
    # Finally, attempt to find a prefix match. For regions that could match
    # multiple prefixes, the first one found is returned.
    for name in names_to_ids:
      if name.startswith(region):
        return names_to_ids[name]
    logging.info('Region "%s" unknown', raw_region)
    return None
