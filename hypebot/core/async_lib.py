# coding=utf-8
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
"""Utils for making async calls."""

# In general, we want to catch all exceptions, so ignore lint errors for e.g.
# catching Exception
# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from concurrent import futures
from functools import partial
from threading import RLock
from typing import Any, Callable

from absl import logging


class AsyncRunner(object):
  """Wrapper around python's futures.

  Besides just running callables on separate threads, AsyncRunner also keeps a
  count of running or scheduled callables, and supports attaching functions to
  be called one time when the count of active callables drops to 0.
  """

  def __init__(self, executor: futures.Executor) -> None:
    self._executor = executor
    self._active_count = 0
    self._completion_callbacks = []
    self._state_lock = RLock()

  def IsIdle(self) -> bool:
    """Returns True if there are no scheduled or active callables running."""
    with self._state_lock:
      return self._active_count == 0

  def RunAsync(self,
               func: Callable, *args: Any, **kwargs: Any) -> futures.Future:
    """Submits func for execution, incrementing active_count."""
    with self._state_lock:
      self._active_count += 1
      return self._executor.submit(self._RunAndRecord, func, *args, **kwargs)

  def OnCompletion(self, func: Callable, *args: Any, **kwargs: Any) -> None:
    """Attaches func to be called when this AsyncRunner becomes idle.

    If the runner is currently idle, func will be executed immediately on this
    thread.

    Args:
      func: Function to run when AsyncRunner becomes idle.
      *args: Positional args passed to func.
      **kwargs: Keyword args passed to func.
    Returns:
      None.
    """
    with self._state_lock:
      # We do this while holding the lock so that adding a completion callback
      # can't race with executing the callbacks.
      self._completion_callbacks.append(partial(func, *args, **kwargs))
      if self._active_count == 0:
        self._OnCompletion()

  def _RunAndRecord(self, func: Callable, *args: Any, **kwargs: Any) -> None:
    """Calls func, decrements count, and execution of completion_callbacks.

    Args:
      func: Function to execute. Runs synchronously on this thread.
      *args: Positional args passed to func.
      **kwargs: Keyword args passed to func.
    Returns:
      None.
    """
    func(*args, **kwargs)
    with self._state_lock:
      self._active_count -= 1
      if self._active_count == 0:
        self._OnCompletion()

  def _OnCompletion(self) -> None:
    """Runs all previously attached completion callbacks in order.

    All callbacks are run serially on the current thread. If the callback raises
    an otherwise unhandled exception, we catch it and log the exception. After
    running, callbacks are removed.

    Returns:
      None.
    """
    with self._state_lock:
      logging.info('AsyncRunner: Triggering run of %s OnCompletion callbacks',
                   len(self._completion_callbacks))
      for bound_fn in self._completion_callbacks:
        try:
          bound_fn()
        except Exception as e:
          logging.error('%s raised an unhandled exception:\n%s',
                        bound_fn.func.__name__, e)
        finally:
          self._completion_callbacks = self._completion_callbacks[1:]
