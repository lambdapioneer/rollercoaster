import unittest
from unittest.mock import MagicMock

from simulation.apps import *
from simulation.multicast.base import *
from simulation.multicast.rollercoaster import *

from tests.utils import *


class TestRollercoasterMessage(unittest.TestCase):

    def test_WHEN_copied_THEN_string_representation_identical(self):
        m = RollercoasterMessage("recipient", "body", "group_id", "source", 1, "role", "sender")
        m2 = m.copy()

        self.assertEqual(str(m), str(m2))


class TestMessagingSession(unittest.TestCase):

    def setUp(self):
        self.sim = create_test_simulation()
        self.group = Group("group", self.sim.users)

        self.multicast_mock = MagicMock()
        self.multicast_mock.group = self.group
        self.multicast_mock.sim = self.sim
        self.multicast_mock.k = 1

        self.session = MessagingSession(self.multicast_mock, self.group.users[0], 0, "")

    def test_init_WHEN_created_THEN_states_set(self):
        self.assertIsNotNone(self.session.schedule.S)
        self.assertIsNotNone(self.session.schedule.G)

        self.assertSetEqual(set(self.group.users[1:]), set(self.session.state.keys()))
        self.assertListEqual(
            [MessagingSession.STATE_IN_PROGRESS] * (len(self.group.users)-1),
            list(self.session.state.values()))

    def test_timeouts_WHEN_set_and_fails_THEN_returns_accordingly(self):
        sim, session, group = self.sim, self.session, self.group
        sim.time = 0

        session.set_timeout(10, group.users[1], "role_1")

        sim.time = 9
        self.assertListEqual([], session.get_failed_timeouts(remove=True))

        sim.time = 10
        self.assertListEqual(
            [MessagingSession.TimeoutEntry(10, group.users[1], "role_1")],
            session.get_failed_timeouts(remove=False))
        self.assertListEqual(
            [MessagingSession.TimeoutEntry(10, group.users[1], "role_1")],
            session.get_failed_timeouts(remove=True))
        self.assertListEqual([], session.get_failed_timeouts(remove=False))

    def test_timeouts_WHEN_set_and_updated_THEN_returns_accordingly(self):
        sim, session, group = self.sim, self.session, self.group
        sim.time = 0

        session.set_timeout(10, group.users[1], "role_1")

        sim.time = 9
        self.assertListEqual([], session.get_failed_timeouts(remove=True))

        session.update_timeout(group.users[1], "role_1", 6)  # extend by new offset (6+9==15)

        sim.time = 10
        self.assertListEqual([], session.get_failed_timeouts(remove=False))

        sim.time = 15
        self.assertListEqual(
            [MessagingSession.TimeoutEntry(15, group.users[1], "role_1")],
            session.get_failed_timeouts(remove=True))
        self.assertListEqual([], session.get_failed_timeouts(remove=False))

    def test_timeouts_WHEN_set_and_removed_THEN_returns_accordingly(self):
        sim, session, group = self.sim, self.session, self.group
        sim.time = 0

        session.set_timeout(10, group.users[1], "role_1")
        session.set_timeout(10, group.users[1], "role_2")

        session.remove_timeout_of_node(group.users[2], "role_1")  # wrong node
        self.assertEqual(2, len(session.timeouts))

        session.remove_timeout_of_node(group.users[1], "role_2")  # only one timeout matches role
        self.assertEqual(1, len(session.timeouts))

        session.remove_timeout_of_node(group.users[1], "role_1")
        self.assertEqual(0, len(session.timeouts))

    def test_acked_WHEN_acked_THEN_state_updated_and_removed(self):
        sim, session, group = self.sim, self.session, self.group
        sim.time = 0

        session.set_timeout(10, group.users[1], "role_1")

        session.mark_acked(group.users[1], "role_1")
        self.assertEqual(0, len(session.timeouts))
        self.assertEqual(MessagingSession.STATE_DELIVERED, session.state[group.users[1]])


class TestRollercoasterStrategyIntegration(unittest.TestCase):

    def test_WHEN_timeouts_turned_off_THEN_delivered_to_all_except_childs_of_offline(self):
        sim = create_test_simulation(delta_ms=10, offline_ids=[1])
        rc_factory = create_factory(RollercoasterStrategy, k=1, timeouts_active=False)
        app = App("app", sim, Group("group", sim.users), rc_factory)

        payload = app._create_payload()
        app.send_payload_to_group(sim.users[0], payload)
        sim.run(50_000)

        for u in [sim.users[i] for i in (2, 4, 6)]:
            self.assertIn((u, payload.nonce), app.seen_deliveries.set)
        for u in [sim.users[i] for i in (1, 3, 5)]:
            self.assertNotIn((u, payload.nonce), app.seen_deliveries.set)

    def test_WHEN_timeouts_turned_on_THEN_delivered_to_all_except_offline_node_itself(self):
        sim = create_test_simulation(delta_ms=10, offline_ids=[1])
        rc_factory = create_factory(RollercoasterStrategy, k=1, timeouts_active=True)
        app = App("app", sim, Group("group", sim.users), rc_factory)

        payload = app._create_payload()
        app.send_payload_to_group(sim.users[0], payload)
        sim.run(50_000)

        for u in [sim.users[i] for i in (2, 3, 4, 5, 6)]:
            self.assertIn((u, payload.nonce), app.seen_deliveries.set)
        for u in [sim.users[i] for i in (1,)]:
            self.assertNotIn((u, payload.nonce), app.seen_deliveries.set)
