# Lint as: python3
# coding=utf-8
"""Library for tracking user activity."""

import collections
import hashlib
import json
import threading
from typing import Dict, Text

from absl import logging
from hypebot.core import schedule_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2


# TODO: Migrate util_lib.UserTracker behavior to ActivityTracker.
# TODO: Migrate BaseCommand._RateLimit tracking to ActivityTracker.
class ActivityTracker(object):
  """A class for tracking user activity."""

  def __init__(self, scheduler: schedule_lib.HypeScheduler):
    self._lock = threading.Lock()
    self._ResetDelta()

    # TODO: This will lose up to 30m of activity on restart.
    scheduler.FixedRate(5, 30 * 60, self._LogAndResetDelta)

  def RecordActivity(self, channel: channel_pb2.Channel, user: user_pb2.User,
                     command: Text):
    """Records that a user issued a command in a channel."""
    with self._lock:
      self._users[user.user_id] += 1
      if channel.visibility == channel_pb2.Channel.PUBLIC:
        self._public_channels[channel.id] += 1
      elif channel.visibility == channel_pb2.Channel.PRIVATE:
        self._private_channels[channel.id] += 1
      elif channel.visibility == channel_pb2.Channel.SYSTEM:
        self._system_callbacks[channel.id] += 1
      else:
        raise ValueError('Unknown channel_pb2.Channel visibility: %s' %
                         channel.visibility)
      self._commands[command] += 1

  def _ResetDelta(self):
    self._commands = collections.defaultdict(lambda: 0)  # type: Dict[Text, int]
    self._users = collections.defaultdict(lambda: 0)  # type: Dict[Text, int]
    self._public_channels = collections.defaultdict(
        lambda: 0)  # type: Dict[Text, int]
    self._private_channels = collections.defaultdict(
        lambda: 0)  # type: Dict[Text, int]
    self._system_callbacks = collections.defaultdict(
        lambda: 0)  # type: Dict[Text, int]

  def _LogAndResetDelta(self):
    """Logs the activity delta since the last call, and resets all counters."""
    delta = None
    with self._lock:
      delta = {
          'users': self._users,
          'channels': {
              'public': self._public_channels,
              'private': self._private_channels,
              'system': self._system_callbacks,
          },
          'commands': self._commands,
      }
      self._ResetDelta()

    delta['users'] = _HashKeys(delta['users'])
    delta['channels']['public'] = _HashKeys(delta['channels']['public'])
    delta['channels']['private'] = _HashKeys(delta['channels']['private'])
    delta['channels']['system'] = _HashKeys(delta['channels']['system'])

    # TODO: Write to a structured logging service or a TSDB.
    logging.info('Command deltas:\n%s', json.dumps(delta))


def _HashKeys(dictionary: Dict[Text, int]) -> Dict[Text, int]:
  return {
      hashlib.sha1(key.encode('utf-8')).hexdigest()[:8]: value
      for (key, value) in dictionary.items()
  }
