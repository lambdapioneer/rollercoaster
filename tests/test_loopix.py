import unittest
from unittest.mock import MagicMock

from simulation.loopix import *
from simulation.messages import *
from simulation.simrandom import *
from simulation.simulation import *
from simulation.utils import *

from tests.utils import *


class TestLoopixMixNode(unittest.TestCase):

    def test_WHEN_message_with_delay_in_inbox_THEN_forwarded_exactly_after_delay(self):
        mix = MixNode('MIX', 0, LoopixConfiguration())
        mix._send_loop = MagicMock()

        node = DummySimulationObject('NODE')
        sim = create_test_simulation_with(objects=[mix, node], delta_ms=2)

        inner_message = WrappedMessage(node, TAG_PAYLOAD, "")
        outer_message = WrappedMessage(mix, TAG_PAYLOAD, inner_message, delay=100)
        sim.send(node, outer_message)

        for _ in range(100 // 2):
            sim.tick(sim)
            self.assertEqual(1, len(mix.inbox.pq))
            self.assertListEqual(node.inbox, [])

        sim.tick(sim) # T=102 at end of `tick`
        sim.tick(sim) # T=102 at beginning of tick -> message will be sent
        self.assertEqual(0, len(mix.inbox.pq))
        self.assertListEqual(node.inbox, [inner_message])

    def test_WHEN_multi_message_in_inbox_THEN_forwarded_to_recipients(self):
        mix = MixNode('MIX', 0, LoopixConfiguration())
        mix._send_loop = MagicMock()

        node_a = DummySimulationObject('A')
        node_b = DummySimulationObject('B')
        sim = create_test_simulation_with(objects=[mix, node_a, node_b])

        inner_message_a = WrappedMessage(node_a, TAG_PAYLOAD, "")
        inner_message_b = WrappedMessage(node_b, TAG_PAYLOAD, "")
        outer_message = WrappedMultiMessage(mix, TAG_MULTI, [inner_message_a, inner_message_b])

        sim.send(node_a, outer_message)
        sim.tick(sim)
        self.assertEqual(1, len(mix.inbox.pq))
        self.assertListEqual(node_a.inbox, [])
        self.assertListEqual(node_b.inbox, [])

        sim.tick(sim)
        self.assertEqual(0, len(mix.inbox.pq))
        self.assertListEqual(node_a.inbox, [inner_message_a])
        self.assertListEqual(node_b.inbox, [inner_message_b])


class TestLoopixUserNode(unittest.TestCase):

    def test_WHEN_has_k_messages_THEN_sends_one_multi_message(self):
        sim = create_test_simulation(users=1)
        provider = DummySimulationObject('PROVIDER')

        user = sim.users[0]
        user.split = 2
        user._send_loop, user._send_payload, user._send_drop = MagicMock(), MagicMock(), MagicMock()
        user.provider = provider

        sim.tick(sim)
        self.assertListEqual(provider.inbox, [])

        # Give user a single message
        m1 = Message(user, TAG_PAYLOAD, "m1")
        user.waiting_for_split.append(m1)

        sim.tick(sim)
        self.assertEqual(len(user.waiting_for_split), 1)
        self.assertEqual(len(provider.inbox), 0)

        # Give user two more messages
        m2 = Message(user, TAG_PAYLOAD, "m2")
        user.waiting_for_split.append(m2)
        m3 = Message(user, TAG_PAYLOAD, "m3")
        user.waiting_for_split.append(m3)

        sim.tick(sim)
        self.assertEqual(len(user.waiting_for_split), 1)
        self.assertEqual(len(provider.inbox), 1)
        multi_message = list(traverse_message(provider.inbox.pop(0)))

        self.assertIn(m1, multi_message)
        self.assertIn(m2, multi_message)
        self.assertNotIn(m3, multi_message)

        # Give user three more messages
        m4 = Message(user, TAG_PAYLOAD, "m4")
        user.waiting_for_split.append(m4)
        m5 = Message(user, TAG_PAYLOAD, "m5")
        user.waiting_for_split.append(m5)
        m6 = Message(user, TAG_PAYLOAD, "m6")
        user.waiting_for_split.append(m6)

        sim.tick(sim)  # only the first pair to be sent
        self.assertEqual(len(user.waiting_for_split), 2)
        self.assertEqual(len(provider.inbox), 1)
        multi_message = list(traverse_message(provider.inbox.pop(0)))

        self.assertIn(m3, multi_message)
        self.assertIn(m4, multi_message)
        self.assertNotIn(m5, multi_message)
        self.assertNotIn(m6, multi_message)

        sim.tick(sim)
        self.assertEqual(len(user.waiting_for_split), 0)
        self.assertEqual(len(provider.inbox), 1)
        multi_message = list(traverse_message(provider.inbox.pop(0)))

        self.assertIn(m5, multi_message)
        self.assertIn(m6, multi_message)

        sim.tick(sim)
        self.assertEqual(len(user.waiting_for_split), 0)
        self.assertEqual(len(provider.inbox), 0)
