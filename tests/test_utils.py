from simulation.messages import TAG_PAYLOAD
from tests.utils import create_test_simulation
import unittest
from unittest.mock import call, MagicMock

from simulation.apps import *
from simulation.utils import *


class TestHelperMethods(unittest.TestCase):

    def test_chunkify(self):
        ll = list(range(10))
        chunks = chunkify(ll, 3)
        self.assertEqual(
            [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]],
            list(chunks)
        )

    def test_map_any_or_all_WHEN_non_iterable_THEN_func_called_once(self):
        func = MagicMock()
        map_any_or_all(func, 10)
        func.assert_called_with(10)

    def test_map_any_or_all_WHEN_iterable_THEN_func_called_many_times(self):
        func = MagicMock()
        map_any_or_all(func, [10, 11, 12])
        func.assert_has_calls([call(10), call(11), call(12)])


class TestHasSeenSet(unittest.TestCase):

    def test_WHEN_not_seen_THEN_false(self):
        s = HasSeenSet()
        self.assertFalse(s.check_and_insert("a"))
        self.assertFalse(s.check_and_insert("b"))

    def test_WHEN_seen_THEN_true(self):
        s = HasSeenSet()
        self.assertFalse(s.check_and_insert("b"))
        self.assertTrue(s.check_and_insert("b"))

    def test_WHEN_cleared_THEN_forgotten(self):
        s = HasSeenSet()
        self.assertFalse(s.check_and_insert("b"))
        s.clear()
        self.assertFalse(s.check_and_insert("b"))


class TestMessageDelayingBox(unittest.TestCase):

    def setUp(self):
        self.b = MessageDelayingBox()
        self.sim = create_test_simulation()

    def tick(self):
        self.b.tick(self.sim)
        self.sim.tick(self.sim)

    def test_WHEN_empty_THEN_returns_empty(self):
        self.assertListEqual([], self.b.pop_current_round(self.sim))
        self.assertListEqual([], self.b.pop_current_round(self.sim))

    def test_WHEN_given_messages_THEN_returned_in_delay_order(self):
        m3 = WrappedMessage(None, TAG_PAYLOAD, None, delay=3)
        m2a = WrappedMessage(None, TAG_PAYLOAD, None, delay=2)
        m5 = WrappedMessage(None, TAG_PAYLOAD, None, delay=5)
        m2b = WrappedMessage(None, TAG_PAYLOAD, None, delay=2)

        for m in (m3, m2a, m5, m2b):
            self.b.add(self.sim, m)

        self.tick()
        self.assertListEqual([], self.b.pop_current_round(self.sim))

        self.tick()
        self.assertListEqual([m2a, m2b], self.b.pop_current_round(self.sim))

        self.tick()
        self.assertListEqual([m3], self.b.pop_current_round(self.sim))

        self.tick()
        self.assertListEqual([], self.b.pop_current_round(self.sim))

        self.tick()
        self.assertListEqual([m5], self.b.pop_current_round(self.sim))


class TestReadWriteSchedules(unittest.TestCase):

    def get_filename(self):
        return "/tmp/python_test_for_loopix_test.tmp"

    def test_read_write_bool(self):
        schedules = [
            [False, False, False, False],
            [True, True, True, True],
            [True, True, True, False],
        ]

        write_compressed_bool_schedules(schedules, self.get_filename())
        actual = read_compressed_bool_schedules(self.get_filename())

        self.assertListEqual(schedules, actual)

    def test_read_write_int(self):
        schedules = [
            "0000",
            "1111",
            "1110",
        ]

        write_compressed_int_schedules(schedules, self.get_filename())
        actual = read_compressed_int_schedules(self.get_filename())

        self.assertListEqual(schedules, actual)

    def test_write_int_read_book(self):
        int_schedules = [
            "0000",
            "1111",
            "1110",
        ]
        bool_schedules = [
            [False, False, False, False],
            [True, True, True, True],
            [True, True, True, False],
        ]

        write_compressed_int_schedules(int_schedules, self.get_filename())
        actual = read_compressed_bool_schedules(self.get_filename())

        self.assertListEqual(bool_schedules, actual)
