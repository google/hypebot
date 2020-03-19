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
"""General utilities for use throughout hypebot code."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import datetime
import math
import random
import re
import threading
import unicodedata

import arrow
from dateutil.relativedelta import relativedelta
from hypebot import hype_types
from hypebot.protos import channel_pb2
from hypebot.protos import message_pb2
from hypebot.protos import user_pb2
import six
from typing import Callable, Dict, Iterable, List, Optional, Text, Tuple


def Access(obj, path, default=None):
  """Tries to get a value from obj given by path, otherwise return default."""
  keys = path.split('.')
  for k in keys:
    try:
      obj = obj.get(k)
    except AttributeError:
      if obj is None:
        continue
      k = int(k)
      if k < len(obj):
        obj = obj[int(k)]
      else:
        obj = None
    if obj is None:
      return default
  return obj


def ArrowTime(hour=0, minute=0, second=0, tz='UTC', weekday=None):
  """Returns an Arrow object with the time portion set to a specific time."""
  time = arrow.now(tz).replace(
      hour=hour, minute=minute, second=second, microsecond=0)
  if weekday is not None:
    return arrow.Arrow.fromdatetime(time.datetime +
                                    relativedelta(weekday=weekday))
  return time


def CanonicalizeName(raw_name: Text):
  """Strips away all non-alphanumeric characters and converts to lowercase."""
  unicode_norm = unicodedata.normalize('NFKC', raw_name).lower()
  # We only match Ll (lowercase letters) since alphanumeric filtering is done
  # after converting to lowercase. Nl and Nd are numeric-like letters and
  # numeric digits.
  return ''.join(
      x for x in unicode_norm if unicodedata.category(x) in ('Ll', 'Nl', 'Nd'))


DECIMAL_POWERS = ('', 'k', 'm', 'b', 't', 'q', 'p')


def UnformatHypecoins(value):
  value = value.lower().rstrip()

  # Separate number and units.
  units = value.lstrip('0123456789eE-+.')
  if units:
    number = value[:-len(units)]
  else:
    number = value
  units = units.lstrip()
  try:
    number = int(number)
  except ValueError:
    number = float(number)

  scale = 0
  if units in DECIMAL_POWERS:
    scale = 1e3**DECIMAL_POWERS.index(units)
  if not scale:
    scale = 1
  return number * scale


def ExtractRegex(pattern: Text,
                 string: Text) -> Optional[Tuple[List[Text], Text]]:
  """Searches for pattern in string and extracts all matches from the string.

  Args:
    pattern: a reguar expression in string format to search for in string.
    string: the string to extract matches of pattern from.

  Returns:
    If pattern was found at least once in string, returns a tuple of the matches
    and the string with the matches removed. Otherwise, returns None to match
    the semantics of re.match/search.
  """
  pattern = re.compile(pattern)
  m = pattern.search(string)
  if m:
    return (pattern.findall(string), pattern.sub('', string))


def FormatHypecoins(amount, abbreviate=False):
  """Format hypecoins to a human readable amount.

  Args:
    amount: {int} amount of hypecoins to format.
    abbreviate: {boolean} whether to display full amount or convert large
      amounts to small strings. Abbreviate shows 3 sig figs using the k, M, G
      suffix system. Without abbreviate, just adds commas and ₡.

  Returns:
    {string} formatted hypecoin amount.
  """
  amount_str = 'NaN'
  if abbreviate:
    for power, prefix in enumerate(DECIMAL_POWERS):
      value = amount * 1e3**-power
      if abs(round(value)) < 1e3:
        break
    if prefix:
      # Round to at most 3 sigfigs.
      pattern = '%.{}f%s'.format(max(0, 2 - int(math.log10(round(abs(value))))))
      amount_str = pattern % (value, prefix)
    else:
      amount_str = '%d' % round(value)
  else:
    amount_str = '{:,d}'.format(amount)
  return '%s₡' % amount_str


def SafeCast(value, desired_type, default=None):
  """Cast between types without any pesky errors."""
  try:
    return desired_type(value)
  except (ValueError, TypeError):
    return default


def TimeDeltaToHumanDuration(time_delta, precision=1):
  """Converts a python timedelta object to a human-readable duration.

  Args:
    time_delta: Python timedelta object
    precision: Number of different units to display. The duration is converted
      into year, month, days, hours, minute, seconds.

  Returns:
    Human-readable string representing the duration of time_delta.
  """
  # A bunch of constants for funsies.
  # pylint: disable=invalid-name
  YEAR_IN_DAYS = 365.25  # Approximate.
  MONTH_IN_DAYS = YEAR_IN_DAYS / 12.0  # Average.
  HOUR_IN_SECONDS = 60 * 60.0
  MINUTE_IN_SECONDS = 60.0
  # pylint: enable=invalid-name

  parts = []
  if time_delta.days >= YEAR_IN_DAYS:
    parts.append('%dy' % (time_delta.days / YEAR_IN_DAYS))
    time_delta = datetime.timedelta(days=time_delta.days % YEAR_IN_DAYS)
  if time_delta.days >= 30:
    parts.append('%dmo' % (time_delta.days / MONTH_IN_DAYS))
    time_delta = datetime.timedelta(days=time_delta.days % MONTH_IN_DAYS)
  if time_delta.days >= 1:
    parts.append('%dd' % time_delta.days)
    time_delta = datetime.timedelta(seconds=time_delta.seconds)
  if time_delta.seconds >= HOUR_IN_SECONDS:
    parts.append('%dh' % (time_delta.seconds / HOUR_IN_SECONDS))
    time_delta = datetime.timedelta(seconds=time_delta.seconds %
                                    HOUR_IN_SECONDS)
  if time_delta.seconds >= MINUTE_IN_SECONDS:
    parts.append('%dm' % (time_delta.seconds / MINUTE_IN_SECONDS))
    time_delta = datetime.timedelta(seconds=time_delta.seconds %
                                    MINUTE_IN_SECONDS)
  parts.append('%ds' % time_delta.seconds)
  return ' '.join(parts[0:precision])


def SafeUrl(url, params=None):
  """Returns url with any sensitive information (API key) stripped."""
  m = re.search(url, '(api[-_]key)')
  if m:
    url = ''.join((url.split(m.group(1))[0], '<redacted>'))
  if params:
    url += '?'
    params = copy.copy(params)
    for key in ('api-key', 'api_key'):
      if key in params:
        params[key] = '<redacted>'
    url += ','.join(['%s=%s' % (k, v) for k, v in params.items()])
  return url


class WeightedCollection(object):
  """A thread-safe collection of choices and associated weights."""

  def __init__(self, items: Iterable[Text]):
    self._prob_table = {i: 1.0 for i in items}
    self._prob_table_lock = threading.RLock()
    self._NormalizeProbs()

  def GetItem(self) -> Text:
    """Returns an item at random (biased by associated weights)."""
    with self._prob_table_lock:
      ordered_choices = sorted(self._prob_table.items(), key=lambda x: x[1])

    r = random.random()
    total = 0
    for item, weight in ordered_choices:
      total += weight
      if r < total:
        return item

  def GetAndDownweightItem(self) -> Text:
    """Returns a random item while increasing the weight of every other item.

    The exact way the non-selected item weights are modified is an
    implementation detail and subject to change.

    Returns:
      A random item from the collection.
    """
    r = random.random()
    total = 0
    selection = None
    with self._prob_table_lock:
      weight_addition = 1 / len(self._prob_table)
      for item, weight in self._prob_table.items():
        total += weight
        if r < total:
          selection = item
          # Set r > any possible total to ensure we finish updating all of the
          # weights.
          r = sum(self._prob_table.values()) + 1
        else:
          self._prob_table[item] += weight_addition
      self._NormalizeProbs()
    return selection

  def ModifyWeight(self, item: Text, update_fn: Callable[[float],
                                                         float]) -> float:
    """Modifies the weight of item using update_fn.

    Args:
      item: Item in collection to update.
      update_fn: Function that takes the current weight of item as an input and
        returns the new weight. An example to add 1 to the current weight:
          ModifyWeight('my-item', lambda cur_weight: cur_weight + 1.0)

    Returns:
      The updated weight for item.

    Raises:
      KeyError if item is not already in the collection.
    """
    with self._prob_table_lock:
      cur_weight = self._prob_table[item]
      new_weight = update_fn(cur_weight)
      self._prob_table[item] = new_weight
      self._NormalizeProbs()
    return new_weight

  def _NormalizeProbs(self):
    with self._prob_table_lock:
      normalize_denom = sum(self._prob_table.values())
      self._prob_table = {
          k: v / normalize_denom for k, v in self._prob_table.items()
      }


def Bold(string):
  """Returns string wrapped in escape codes representing bold typeface."""
  return '\x02%s\x0F' % string


def Italic(string):
  """Returns string wrapped in escape codes representing italic typeface."""
  return '\x1D%s\x0F' % string


def Underline(string):
  """Returns string wrapped in escape codes representing underlines."""
  return '\x1F%s\x0F' % string


_MIRC_COLORS = {
    'white': (0, '#ffffff'),
    'black': (1, '#000000'),
    'blue': (2, '#000075'),
    'green': (3, '#009300'),
    'red': (4, '#ff0000'),
    'brown': (5, '#750000'),
    'purple': (6, '#9c009c'),
    'orange': (7, '#fc7500'),
    'yellow': (8, '#ffff00'),
    'light green': (9, '#00fc00'),
    'cyan': (10, '#009393'),
    'light cyan': (11, '#00ffff'),
    'light blue': (12, '#0000fc'),
    'pink': (13, '#ff00ff'),
    'grey': (14, '#757575'),
    'light grey': (15, '#d2d2d2'),
}


def Colorize(string, color, irc=True):
  """Returns string wrapped in escape codes representing color."""
  try:
    color = _MIRC_COLORS[color.lower()]
  except (KeyError, ValueError):
    return string
  if irc:
    return '\x03%02d%s\x0f' % (color[0], string)
  return '<font color="%s">%s</font>' % (color[1], string)


def StripColor(string):
  """Returns string with color escape codes removed."""
  regex = re.compile(r'\x03(?:\d{1,2}(?:,\d{1,2})?)?', re.UNICODE)
  return regex.sub('', string)


def Dankify(string):
  """Returns string with non-dank replaced by more dank ones."""
  return re.sub(r'([dD])(ark|usk)', r'\1ank', string)


def FuzzyBool(value):
  """Returns value as a boolean with special handling for false-like strings."""
  if (isinstance(value, six.string_types) and
      value.strip().lower() in ('false', 'no', '0')):
    return False
  return bool(value)


def Sparkline(values):
  """Returns an unicode sparkline representing values."""
  unicode_values = '▁▂▃▄▅▆▇█'
  if not values:
    return ''
  elif len(values) == 1:
    # Special case a single value to always return the middle value instead of
    # the smallest one, which would always be the case otherwise
    return unicode_values[len(unicode_values) // 2]
  min_value = min(values)
  # Really small offset used to ensure top bin includes max(values).
  value_range = max(values) - min_value + 1e-10
  bucket_size = value_range / len(unicode_values)
  bucketized_values = [int((v - min_value) / bucket_size) for v in values]
  return ''.join(unicode_values[v] for v in bucketized_values)


class _UserTrack(object):

  def __init__(self, user: user_pb2.User):
    # Last known message from the user.
    self.last_seen = arrow.get(0)
    # Full user proto.
    self.user = user
    # Set of channel ids where we have seen the user.
    self.channels = set()


class UserTracker(object):
  """A class for tracking users (humans / bots) and their channels."""

  def __init__(self):
    self._users = {}  # type: Dict[Text, _UserTrack]
    self._lock = threading.RLock()

  def RecordActivity(self, user: user_pb2.User, channel: channel_pb2.Channel):
    with self._lock:
      self.AddUser(user, channel)
      self._users[user.user_id].last_seen = arrow.utcnow()

  def LastActivity(self, user: user_pb2.User):
    with self._lock:
      self.AddUser(user)
      return self._users[user.user_id].last_seen

  def AddUser(self,
              user: user_pb2.User,
              channel: Optional[channel_pb2.Channel] = None):
    """Adds name as a known user."""
    with self._lock:
      if user.user_id not in self._users:
        self._users[user.user_id] = _UserTrack(user)
      if channel:
        self._users[user.user_id].channels.add(channel.id)

  def AllHumans(self, channel: Optional[channel_pb2.Channel] = None):
    """Returns a list of all users that are humans.

    Args:
      channel: If specified, only return humans in the channel.
    """
    with self._lock:
      humans = []
      for track in self._users.values():
        if not track.user.bot and (not channel or channel.id in track.channels):
          humans.append(track.user)
    return humans

  def AllBots(self, channel: Optional[channel_pb2.Channel] = None):
    """Returns a list of all users that are bots.

    Args:
      channel: If specified, only return bots in the channel.
    """
    with self._lock:
      bots = []
      for track in self._users.values():
        if track.user.bot and (not channel or channel.id in track.channels):
          bots.append(track.user)
    return bots

  def AllUsers(self, channel: Optional[channel_pb2.Channel] = None):
    """Returns a list of all known users.

    Args:
      channel: If specified, only return users in the channel.
    """
    return self.AllHumans(channel) + self.AllBots(channel)


def MatchesAny(channels, channel):
  """Whether any channels' id is a prefix of channel.id."""
  for chan in channels:
    if channel.id.startswith(chan.id):
      return True
  return False


def _CardAsTextList(card: message_pb2.Card) -> List[Text]:
  """Make a reasonable text-only rendering of a card."""
  text = []
  if card.header.title:
    text.append(card.header.title)
  if card.header.subtitle:
    text.append(card.header.subtitle)
  # Separator between header and fields if both exist.
  if text and card.fields:
    text.append('---')
  for field in card.fields:
    line = ''
    if field.HasField('title'):
      line = '%s: ' % field.title
    if field.HasField('text'):
      line += field.text
    elif field.HasField('image'):
      line += field.image.alt_text
    else:
      line += ', '.join([
          '[%s](%s)' % (button.text, button.action_url)
          for button in field.buttons
      ])
    text.append(line)
  return text


def _AppendToMessage(msg: hype_types.Message,
                     response: hype_types.CommandResponse):
  """Append a single response to the message list."""
  if isinstance(response, (bytes, Text)):
    msg.messages.add(text=response.split('\n'))
  elif isinstance(response, message_pb2.Message):
    msg.messages.extend([response])
  elif isinstance(response, message_pb2.Card):
    msg.messages.add(card=response, text=_CardAsTextList(response))
  elif isinstance(response, message_pb2.MessageList):
    msg.messages.extend(response.messages)
  else:
    assert isinstance(response, list)
    for line in response:
      _AppendToMessage(msg, line)


def MakeMessage(response: hype_types.CommandResponse) -> hype_types.Message:
  """Converts from the highly permissible CommandResponse into a Message."""
  msg = hype_types.Message()
  _AppendToMessage(msg, response)
  return msg
