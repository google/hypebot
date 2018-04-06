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
"""Store your hypes in redis."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import partial
import json
from typing import Any, List, Optional, Tuple

from absl import logging
import redis

from hypebot.types import HypeStr, JsonType
from hypebot.core import params_lib
from hypebot.storage import storage_lib


class RedisTransaction(storage_lib.HypeTransaction):
  """Redis implementation of HypeTransaction.

  All lowercase methods (e.g. get, set, ltrim, etc.) are merely pass-through
  methods that ensure we're watching the key we're trying to operate on. This
  class has built-in protection for bad transaction construction (trying to read
  a value you've already written to, etc.).
  """

  def __init__(self, redis_pipeline: redis.client.StrictPipeline, *args,
               **kwargs):
    super(RedisTransaction,
          self).__init__(*args, **kwargs)  # pytype: disable=wrong-arg-count
    self._pipe = redis_pipeline
    self._command_buffer = []

  def watch(self, full_key: HypeStr) -> None:
    self._pipe.watch(full_key)

  def get(self, full_key: HypeStr) -> Optional[HypeStr]:
    self._WatchKey(full_key)
    return self._pipe.get(full_key)

  def set(self, full_key: HypeStr, value: HypeStr) -> bool:
    if self._TryBuffer(full_key, partial(self.set, full_key, value)):
      return True
    return self._pipe.set(full_key, value)

  def type(self, full_key: HypeStr) -> HypeStr:
    self._WatchKey(full_key)
    return self._pipe.type(full_key)

  def lindex(self, full_key: HypeStr, index: int) -> Optional[HypeStr]:
    self._WatchKey(full_key)
    return self._pipe.lindex(full_key, index)

  def lpush(self, full_key: HypeStr, value: HypeStr) -> int:
    if self._TryBuffer(full_key, partial(self.lpush, full_key, value)):
      return 1
    return self._pipe.lpush(full_key, value)

  def lrange(self, full_key: HypeStr, start: int, end: int) -> List[HypeStr]:
    self._WatchKey(full_key)
    return self._pipe.lrange(full_key, start, end)

  def ltrim(self, full_key: HypeStr, start: int, end: int) -> bool:
    if self._TryBuffer(full_key, partial(self.ltrim, full_key, start, end)):
      return True
    return self._pipe.ltrim(full_key, start, end)

  def _ApplyBufferedCommands(self) -> bool:
    if self._command_buffer:
      logging.info('%s Draining command buffer of %s command(s)', self,
                   len(self._command_buffer))
      self._pipe.multi()
      if not all(cmd() for cmd in self._command_buffer):
        logging.info('%s Failed to set a value, commit aborting', self)
        return False
      return True

  def _TryBuffer(self, full_key: HypeStr, command: partial) -> bool:
    """Returns if a mutating command was buffered for future execution."""
    if not self._pipe.explicit_transaction:
      self._command_buffer.append(command)
      return True
    # This means we're already in a MULTI block for this transaction, so calling
    # a mutating command is ok.
    return False

  def _WatchKey(self, full_key: HypeStr) -> bool:
    """Adds full_key to transaction if no pending write for full_key exist."""
    if full_key in (cmd.args for cmd in self._command_buffer):
      raise ValueError('Key %s already has a pending write in %s.' % (full_key,
                                                                      self))
    self.watch(full_key)

  def Commit(self):
    if not self._ApplyBufferedCommands():
      return False
    try:
      status = self._pipe.execute()
      self._pipe.reset()
      return status
    except Exception:
      logging.info('%s Commit aborted, due to watch failure, raising', self)
      raise storage_lib.CommitAbortException


class RedisStore(storage_lib.HypeStore):
  """Store hype in Redis.

  Note: Redis does not actually have strongly atomic reads, only optimistic
  transactions. Put another way, you can't guarantee a read of two separte keys
  is consistent (one might change before you can read the other). Redis supports
  optimistic transactions using WATCH on any keys you've read, which means that
  given enough time (potentially infinite :^) ), you'll get an atomic read.
  """

  DEFAULT_PARAMS = params_lib.MergeParams(
      storage_lib.HypeStore.DEFAULT_PARAMS, {
          'host': '127.0.0.1',
          'port': 6379
      })

  def __init__(self, params: Any, *args, **kwargs):
    self._params = self.DEFAULT_PARAMS
    self._params.Override(params)
    self._params.Lock()
    self._redis = redis.StrictRedis(self._params.host, self._params.port,
                                    decode_responses=True)

  @property
  def engine(self) -> HypeStr:
    return 'redis'

  def GetValue(self, key, subkey, tx=None) -> HypeStr:
    if tx:
      return self._GetValue(key, subkey, tx)
    return self.RunInTransaction(self._GetValue, key, subkey)

  def _GetValue(self, key, subkey, tx):
    datatype, full_key = self._GetFullKey(key, subkey, tx)
    if not datatype:
      # full_key doesn't exist
      return ''

    if datatype == 'list':
      return tx.lindex(full_key, 0)
    elif datatype == 'string':
      return tx.get(full_key)
    else:
      raise NotImplementedError(
          'RedisStore can\'t operate on redis type "%s" yet' % datatype)

  def SetValue(self, key: HypeStr, subkey: HypeStr, value,
               tx: RedisTransaction = None):
    if tx:
      return self._SetValue(key, subkey, value, tx)
    return self.RunInTransaction(self._SetValue, key, subkey, value)

  def _SetValue(self, key, subkey, value, tx):
    datatype, full_key = self._GetFullKey(key, subkey, tx)
    if not datatype or datatype == 'string':
      return tx.set(full_key, value)
    elif datatype == 'list':
      return tx.lpush(full_key, value)
    else:
      raise NotImplementedError(
          'RedisStore can\'t operate on redis type "%s" yet' % datatype)

  def GetSubkey(self, subkey, tx=None):
    if tx:
      return self._GetSubkey(subkey, tx)
    return self.RunInTransaction(self._GetSubkey, subkey)

  def _GetSubkey(self, subkey: HypeStr,
                 tx: RedisTransaction) -> List[Tuple[HypeStr, HypeStr]]:
    results = []
    for full_key in self._redis.scan_iter('%s:*' % subkey):
      key = full_key.replace('%s:' % subkey, '', 1)
      results.append((key, self._GetValue(key, subkey, tx)))
    return results

  def GetHistoricalValues(
      self,
      key: HypeStr,
      subkey: HypeStr,
      num_past_values: int,
      tx: Optional[RedisTransaction] = None) -> List[JsonType]:
    if tx:
      return self._GetHistoricalValues(key, subkey, num_past_values, tx)
    return self.RunInTransaction(self._GetHistoricalValues, key, subkey,
                                 num_past_values)

  def _GetHistoricalValues(self, key, subkey, num_past_values, tx):
    datatype, full_key = self._GetFullKey(key, subkey, tx)
    if not datatype or datatype == 'list':
      return [
          json.loads(x) for x in tx.lrange(full_key, 0, num_past_values - 1)
      ]
    elif datatype == 'string':
      return [json.loads(tx.get(full_key))]
    else:
      raise NotImplementedError(
          'RedisStore can\'t operate on redis type "%s" yet' % datatype)

  def PrependValue(self,
                   key: HypeStr,
                   subkey: HypeStr,
                   new_value: JsonType,
                   max_length: Optional[int] = None,
                   tx: Optional[RedisTransaction] = None) -> None:
    if tx:
      return self._PrependValue(key, subkey, new_value, max_length, tx)
    tx_name = 'PrependValue: %s/%s' % (key, subkey)
    return self.RunInTransaction(
        self._PrependValue, key, subkey, new_value, max_length, tx_name=tx_name)

  def _PrependValue(self, key: HypeStr, subkey: HypeStr, new_value: JsonType,
                    max_length: Optional[int], tx: RedisTransaction) -> None:
    """Internal version of PrependValue that requires a transaction."""
    datatype, full_key = self._GetFullKey(key, subkey)
    if not datatype or datatype == 'list':
      serialized_value = json.dumps(new_value)
      tx.lpush(full_key, serialized_value)
      if max_length:
        tx.ltrim(full_key, 0, max_length - 1)
    elif datatype == 'string':
      # This behavior is subject to change
      logging.error('PrependValue called on string')
      raise TypeError(
          'Tried to call PrependValue on a redis key of type %s' % datatype)
    else:
      raise NotImplementedError(
          'RedisStore can\'t operate on redis type "%s" yet' % datatype)

  def NewTransaction(self, tx_name: HypeStr) -> RedisTransaction:
    return RedisTransaction(self._redis.pipeline(), tx_name)

  def _GetFullKey(
      self,
      key: HypeStr,
      subkey: HypeStr,
      tx: Optional[RedisTransaction] = None) -> Tuple[
          Optional[HypeStr], HypeStr]:
    """Builds the full key for Redis from the key and subkey."""
    full_key = '%s:%s' % (subkey, key)
    datatype = tx.type(full_key) if tx else self._redis.type(full_key)
    if datatype == 'none':
      datatype = None
    return (datatype, full_key)
