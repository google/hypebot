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
from typing import Any, AnyStr, List, Optional, Tuple

from absl import logging
import redis
from redis.exceptions import WatchError

from hypebot.core import cache_lib
from hypebot.core import params_lib
from hypebot.storage import storage_lib
from hypebot.types import JsonType


class RedisTransaction(storage_lib.HypeTransaction):
  """Redis implementation of HypeTransaction.

  All lowercase methods (e.g. get, set, ltrim, etc.) are merely pass-through
  methods that ensure we're watching the key we're trying to operate on. This
  class has built-in protection for bad transaction construction (trying to read
  a value you've already written to, etc.).
  """

  def __init__(self, redis_pipeline: redis.client.StrictPipeline, *args,
               **kwargs):
    super(RedisTransaction, self).__init__(*args, **kwargs)  # pytype: disable=wrong-arg-count
    self._pipe = redis_pipeline
    self._command_buffer = []

  def watch(self, full_key: AnyStr) -> None:
    self._pipe.watch(full_key)

  def get(self, full_key: AnyStr) -> Optional[AnyStr]:
    self._WatchKey(full_key)
    return self._pipe.get(full_key)

  def set(self, full_key: AnyStr, value: AnyStr) -> bool:
    if self._TryBuffer(full_key, partial(self.set, full_key, value)):
      return True
    return self._pipe.set(full_key, value)

  def delete(self, full_key: AnyStr) -> None:
    if self._TryBuffer(full_key, partial(self.delete, full_key)):
      return
    self._pipe.delete(full_key)

  def type(self, full_key: AnyStr) -> AnyStr:
    self._WatchKey(full_key)
    return self._pipe.type(full_key)

  def lindex(self, full_key: AnyStr, index: int) -> Optional[AnyStr]:
    self._WatchKey(full_key)
    return self._pipe.lindex(full_key, index)

  def lpush(self, full_key: AnyStr, value: AnyStr) -> int:
    if self._TryBuffer(full_key, partial(self.lpush, full_key, value)):
      return 1
    return self._pipe.lpush(full_key, value)

  def lrange(self, full_key: AnyStr, start: int, end: int) -> List[AnyStr]:
    self._WatchKey(full_key)
    return self._pipe.lrange(full_key, start, end)

  def ltrim(self, full_key: AnyStr, start: int, end: int) -> bool:
    if self._TryBuffer(full_key, partial(self.ltrim, full_key, start, end)):
      return True
    return self._pipe.ltrim(full_key, start, end)

  def _ApplyBufferedCommands(self) -> bool:
    if self._command_buffer:
      logging.info('%s Draining command buffer of %s command(s)', self,
                   len(self._command_buffer))
      self._pipe.multi()
      if not all(cmd() for cmd in self._command_buffer):
        raise storage_lib.CommitAbortError(
            '%s Failed to set a value, commit aborting' % self)

  def _TryBuffer(self, full_key: AnyStr, command: partial) -> bool:
    """Returns if a mutating command was buffered for future execution."""
    if not self._pipe.explicit_transaction:
      self._command_buffer.append(command)
      return True
    # This means we're already in a MULTI block for this transaction, so calling
    # a mutating command is ok.
    return False

  def _WatchKey(self, full_key: AnyStr) -> bool:
    """Adds full_key to transaction if no pending write for full_key exist."""
    if full_key in (cmd.args for cmd in self._command_buffer):
      raise ValueError(
          'Key %s already has a pending write in %s.' % (full_key, self))
    self.watch(full_key)

  def Commit(self):
    self._ApplyBufferedCommands()
    try:
      status = self._pipe.execute()
      self._pipe.reset()
      # status is a list of return values from the redis server. It's possible
      # one of them actually demonstrates a failure, but most failures either
      # raise or end up with an empty status, so we just return that.
      return status is not None
    except WatchError:
      logging.info('%s Commit failed due to watch failure, retrying', self)
      return False


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
          'port': 6379,
          'auth_key': None
      })

  def __init__(self, params: Any, *args, **kwargs):
    super(RedisStore, self).__init__(params, *args, **kwargs)
    self._redis = redis.StrictRedis(
        self._params.host,
        self._params.port,
        password=self._params.auth_key,
        decode_responses=True)

  @property
  def engine(self) -> AnyStr:
    return 'redis'

  def GetValue(self, key, subkey, tx=None) -> AnyStr:
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

  def SetValue(self,
               key: AnyStr,
               subkey: AnyStr,
               value,
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

  def Delete(self, key: AnyStr, tx: Optional[RedisTransaction] = None) -> None:
    if not tx:
      self.RunInTransaction(self.Delete, key)
      return
    datatype, full_key = self._GetFullKey(key, '', tx)
    if not datatype:
      # full_key doesn't exist, do nothing
      return
    tx.delete(full_key)

  def GetSubkey(self, subkey, tx=None):
    if tx:
      return self._GetSubkey(subkey, tx)
    return self.RunInTransaction(self._GetSubkey, subkey)

  def _GetSubkey(self, subkey: AnyStr,
                 tx: RedisTransaction) -> List[Tuple[AnyStr, AnyStr]]:
    results = []
    for full_key in self._redis.scan_iter('%s:*' % subkey):
      key = full_key.replace('%s:' % subkey, '', 1)
      results.append((key, self._GetValue(key, subkey, tx)))
    return results

  def GetHistoricalValues(
      self,
      key: AnyStr,
      subkey: AnyStr,
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
                   key: AnyStr,
                   subkey: AnyStr,
                   new_value: JsonType,
                   max_length: Optional[int] = None,
                   tx: Optional[RedisTransaction] = None) -> None:
    if tx:
      self._PrependValue(key, subkey, new_value, max_length, tx)
      return
    tx_name = 'PrependValue: %s/%s' % (key, subkey)
    self.RunInTransaction(
        self._PrependValue, key, subkey, new_value, max_length, tx_name=tx_name)

  def _PrependValue(self, key: AnyStr, subkey: AnyStr, new_value: JsonType,
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

  def NewTransaction(self, tx_name: AnyStr) -> RedisTransaction:
    return RedisTransaction(self._redis.pipeline(), tx_name)

  def _GetFullKey(self,
                  key: AnyStr,
                  subkey: AnyStr,
                  tx: Optional[RedisTransaction] = None
                 ) -> Tuple[Optional[AnyStr], AnyStr]:
    """Builds the full key for Redis from the key and subkey.

    Note, this function either adds a type lookup to the transaction, or makes
    a call to the redis server to fetch type information for the key. This is
    done to ensure other operations (such as a GetValue on a key that stores
    historic values) can be delegated to the right underlying calls to redis (in
    this example, an lindex).

    Args:
      key: The primary key used to build the full_key.
      subkey: The subkey used to build the full_key.
      tx: Optional transaction to run the type lookup within.

    Returns:
      A (key_type, full_key) tuple, where key_type is None if the full_key
      doesn't exist in the database.
    """
    full_key = '%s:%s' % (subkey, key)
    key_type = tx.type(full_key) if tx else self._redis.type(full_key)
    if key_type == 'none':
      key_type = None
    return (key_type, full_key)


class ReadCacheRedisStore(RedisStore):
  """A version of RedisStore which maintains a cache for lookups.

  Note the cache is not kept coherent between bots (writes for a cached key are
  not propagated to other caches), and as such this class should only be used
  when QPS to redis is of concern.
  """

  def __init__(self, params, cache_max_age=30, cache_max_items=128):
    super(ReadCacheRedisStore, self).__init__(params)
    self._cache = cache_lib.LRUCache(
        cache_max_items, max_age_secs=cache_max_age)
    logging.info('RCRedisStore params =>\n%s', self._params.AsDict())

  def SetValue(self, key, subkey, value, tx=None):
    full_key = '%s:%s' % (subkey, key)
    # Short-circut if we try to store the same value again
    if self._cache.Get(full_key) == value:
      return
    self._cache.Put(full_key, value)
    super(ReadCacheRedisStore, self).SetValue(key, subkey, value, tx)

  def GetValue(self, key, subkey, tx=None):
    # Check the cache before delegating to the base class
    full_key = '%s:%s' % (subkey, key)
    value = self._cache.Get(full_key)
    if value is None:
      value = super(ReadCacheRedisStore, self).GetValue(key, subkey, tx)
      self._cache.Put(full_key, value)
    return value
