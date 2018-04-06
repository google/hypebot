# coding=utf-8
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
"""Collection of League client variable values.

Some of Rito's API methods return description strings that have variables.
Unfortunately, Rito habitually does not make variable values accessible through
the API. Instead, the substitution table lives in the League client and we chose
to copy them here.
"""


REFORGED_RUNE_VARS = {
    'SummonAery': {
        '@DamageBase@': '15',
        '@DamageMax@': '40',
        '@DamageAPRatio.-1@': '0.1',
        '@DamageADRatio.-1@': '0.15',
        '@ShieldBase@': '30',
        '@ShieldMax@': '80',
        '@ShieldRatio.-1@': '0.25',
        '@ShieldRatioAD.-1@': '0.4',
    },
    'ArcaneComet': {
        '@DamageBase@': '30',
        '@DamageMax@': '100',
        '@APRatio.-1@': '0.2',
        '@ADRatio.-1@': '0.35',
        '@RechargeTime@': '20',
        '@RechargeTimeMin@': '8',
        '@PercentRefund*100@': '20',
        '@AoEPercentRefund*100@': '10',
        '@DotPercentRefund*100@': '5',
    },
    'PhaseRush': {
        '@Window@': '3',
        '@HasteBase*100@': '15',
        '@HasteMax*100@': '40',
        '@SlowResist*100@': '75',
        '@Duration@': '3',
        '@Cooldown@': '15',
    },
    # TODO(???): Fill in the rest of these.
}
