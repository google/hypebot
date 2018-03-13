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
"""Library for scheduling things."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random

from absl import logging
from apscheduler.job import Job
from apscheduler.scheduler import Scheduler
import arrow
from typing import Callable


class HypeScheduler(object):
  """Wraps APScheduler with some conveniences."""

  def __init__(self, local_tz: str = None):
    """Constructor.

    Args:
      local_tz: The local timezone the scheduler is running in.
    """
    self._scheduler = Scheduler()
    self._local_tz = local_tz
    self.StartScheduler()

  def StartScheduler(self):
    if self._scheduler and not self._scheduler.running:
      self._scheduler.start()

  def InSeconds(self, seconds: int, fn: Callable, *args, **kwargs) -> Job:
    """Schedule function to run in given seconds.

    Args:
      seconds: How many seconds to wait before scheduling function.
      fn: Function to call.
      *args: Arguments to pass to function.
      **kwargs: Keyworded arguments to pass to function.

    Returns:
      APScheduler Job.
    """
    schedule_time = arrow.now().shift(seconds=seconds)
    # APScheduler 2.1.2 doesn't understand timezones.
    return self._scheduler.add_date_job(
        fn, schedule_time.naive,
        args=args, kwargs=kwargs)

  def DailyCallback(self,
                    schedule_time: arrow.Arrow,
                    fn: Callable, *args, **kwargs) -> Job:
    """Schedules fn to be run once a day at schedule_time.

    The actual scheduled time is perturbed randomly +/-30s unless the kwarg
    '_jitter' is set to False.

    Args:
      schedule_time: An Arrow object specifying when to run fn.
      fn: The function to be run.
      *args: Arguments to pass to fn.
      **kwargs: Keyworded arguments to pass to fn. Special kwargs listed below:
          _jitter - {int} How many seconds to perturb scheduling time by, in
                    both directions. Defaults to 30s.

    Returns:
      APScheduler Job.
    """
    if self._local_tz:
      schedule_time = schedule_time.to(self._local_tz)
    jitter = kwargs.get('_jitter', 30)
    if jitter:
      jitter_secs = random.randint(-jitter, jitter)
      schedule_time = schedule_time.shift(seconds=jitter_secs)
    kwargs.pop('_jitter', None)

    # APScheduler 2.1.2 doesn't understand timezones.
    return self._scheduler.add_interval_job(
        fn, args=args, kwargs=kwargs,
        start_date=schedule_time.naive, days=1)

  def FixedRate(self,
                initial_delay: int,
                period: int,
                fn: Callable, *args, **kwargs) -> Job:
    """Schedules a recurring task at a fixed rate.

    Args:
      initial_delay: Seconds to wait before scheduling first instance.
      period: Interval in seconds between subsequent instances.
      fn: The function to run.
      *args: Arguments to pass to fn.
      **kwargs: Keyworded arguments to pass to fn.

    Returns:
      APScheduler Job.
    """
    start_time = arrow.now().shift(seconds=initial_delay)
    # APScheduler 2.1.2 doesn't understand timezones.
    return self._scheduler.add_interval_job(
        fn, args=args, kwargs=kwargs,
        start_date=start_time.naive, seconds=period)

  def UnscheduleJob(self, job: Job) -> None:
    """Unschedules job from running in the future.

    Args:
      job: Job to unschedule.
    """
    try:
      self._scheduler.unschedule_job(job)
    except KeyError:
      logging.info('Job %s not scheduled.', job)

