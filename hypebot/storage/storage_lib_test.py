# Lint as: python3
"""Tests for hypebot.storage.storage_lib."""

import unittest
from unittest import mock

from hypebot.core import params_lib
from hypebot.storage import memstore_lib
from hypebot.storage import storage_lib


class HypeQueueTest(unittest.TestCase):

  def setUp(self):
    super(HypeQueueTest, self).setUp()
    self._store = memstore_lib.MemStore(params_lib.HypeParams())
    self._scheduler = mock.MagicMock()
    self.queue = storage_lib.HypeQueue(self._store, 'test', self._scheduler,
                                       lambda _: True)

  def test_init_sets_name(self):
    expected_name = 'my-queue'
    queue = storage_lib.HypeQueue(self._store, expected_name, self._scheduler,
                                  lambda _: True)

    self.assertTrue(queue._queue_name.startswith(expected_name))

  def test_enqueue_stores_payload(self):
    expected_payload = 'abc'
    self.queue.Enqueue(expected_payload)

    queue = self._get_queue_state()
    self.assertEqual(len(queue), 1)
    self.assertEqual(queue[0], expected_payload)

  def test_enqueue_none_is_a_valid_payload(self):
    self.queue.Enqueue(None)

    queue = self._get_queue_state()
    self.assertCountEqual(queue, [None])

  def test_enqueue_order_is_fifo(self):
    payloads = [1, '2', 5.0, {'a': 2}]
    for payload in payloads:
      self.queue.Enqueue(payload)

    queue = self._get_queue_state()
    self.assertCountEqual(queue, payloads)

    process_ran = self.queue.ProcessQueue(2)

    self.assertTrue(process_ran)
    queue = self._get_queue_state()
    self.assertCountEqual(queue, payloads[2:])

  def test_process_handles_every_payload(self):
    process_calls = 0
    def _count(_):
      nonlocal process_calls
      process_calls += 1
      return True

    self.queue._process_fn = _count
    num_payloads = 7
    for i in range(num_payloads):
      self.queue.Enqueue(i)

    process_ran = self.queue.ProcessQueue(num_payloads)

    self.assertTrue(process_ran)
    self.assertEqual(self._get_queue_state(), [])
    self.assertEqual(num_payloads, process_calls)

  def test_process_propagates_exceptions(self):
    def throws(_):
      raise RuntimeError('oops')
    self.queue._process_fn = throws
    self.queue.Enqueue(1)

    with self.assertRaises(RuntimeError):
      self.queue.ProcessQueue()

  def test_process_batch_size_limits_payloads_processed(self):
    payloads = [1, 2]
    self.queue.Enqueue(payloads[0])
    self.queue.Enqueue(payloads[1])

    process_ran = self.queue.ProcessQueue(1)

    self.assertTrue(process_ran)
    self.assertCountEqual(self._get_queue_state(), payloads[1:])

  def test_process_multiple_calls_clears_queue(self):
    payloads = list(range(10))
    for p in payloads:
      self.queue.Enqueue(p)

    process_ran = self.queue.ProcessQueue(5)

    self.assertTrue(process_ran)
    queue = self._get_queue_state()
    self.assertCountEqual(queue, payloads[5:])

    process_ran = self.queue.ProcessQueue(5)

    self.assertTrue(process_ran)
    queue = self._get_queue_state()
    self.assertEqual(queue, [])

  def test_process_nacking_keeps_payload_in_queue(self):
    def nack_odds(payload):
      return payload % 2 == 0

    self.queue._process_fn = nack_odds
    payloads = list(range(10))
    for p in payloads:
      self.queue.Enqueue(p)

    process_ran = self.queue.ProcessQueue(len(payloads))

    self.assertTrue(process_ran)
    queue = self._get_queue_state()
    self.assertEqual(len(queue), 5)
    self.assertCountEqual(queue, [x for x in payloads if x % 2 != 0])

  def _get_queue_state(self):
    return self._store.GetJsonValue(self.queue._queue_name, self.queue._SUBKEY)


if __name__ == '__main__':
  unittest.main()
