import pickle
import unittest
from unittest.mock import MagicMock

from simulation.messages import *
from simulation.simrandom import *
from simulation.simulation import *

from tests.utils import *


class TestMessages(unittest.TestCase):

    def setUp(self):
        self.sim = create_test_simulation()

    def test_message_WHEN_pickling_THEN_callback_not_saved(self):
        m = Message('recipient', TAG_PAYLOAD, 'body', callback='callback')
        data = pickle.dumps(m)
        m2 = pickle.loads(data)
        self.assertEqual(m2.callback, nop)

    def test_create_wrapped_messages_WHEN_given_rate_THEN_sum_of_rates_match_excpected_value(self):
        n = 100_000
        chain = ["hop_%d" % x for x in range(n)]
        rate_delay = 2  # i.e. avg 500ms hops
        m = create_wrapped_message(TAG_PAYLOAD, "body", chain, rate_delay, self.sim)

        total_delay = 0.0
        while isinstance(m, Message):
            total_delay += m.delay
            m = m.body

        self.assertAlmostEqual(1/rate_delay, total_delay/1000/n, places=1)

    def test_create_wrapped_multi_message_multiple_WHEN_THEN_matches_expectations(self):
        m = create_wrapped_multi_message_multiple(
            chain_prefix=["p1", "m1", "m2"],
            chain_suffixes=[
                ["m3", "u2"],
                ["m5", "u4"],
            ],
            tags=[TAG_DROP, TAG_PAYLOAD],
            bodies=["body1", "body2"],
            rate_delay_per_seconds=1,
            sim=self.sim
        )

        self.assertEqual(m.recipient, 'p1')
        self.assertEqual(m.tag, TAG_MULTI)

        m1 = m.unwrap()
        self.assertEqual(m1.recipient, 'm1')
        self.assertEqual(m1.tag, TAG_MULTI)

        m2 = m1.unwrap()
        self.assertEqual(m2.recipient, 'm2')
        self.assertEqual(m2.tag, TAG_MULTI)

        m3, m5 = m2.unwrap()
        self.assertEqual(m3.recipient, 'm3')
        self.assertEqual(m3.tag, TAG_DROP)
        self.assertEqual(m5.recipient, 'm5')
        self.assertEqual(m5.tag, TAG_PAYLOAD)

        u2, u4 = m3.unwrap(), m5.unwrap()
        self.assertEqual(u2.recipient, 'u2')
        self.assertEqual(u2.tag, TAG_DROP)
        self.assertEqual(u2.body, 'body1')
        self.assertEqual(u4.recipient, 'u4')
        self.assertEqual(u4.tag, TAG_PAYLOAD)
        self.assertEqual(u4.body, 'body2')
