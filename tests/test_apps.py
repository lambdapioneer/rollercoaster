import unittest
from unittest.mock import MagicMock

# pylint: disable=unused-wildcard-import
from simulation.apps import *
from simulation.loopix import *
from simulation.messages import *
from simulation.multicast.base import *
from simulation.simrandom import *
from simulation.simulation import *
from simulation.utils import *

from tests.utils import *


class TestAppPayload(unittest.TestCase):

    def test_WHEN_repr_THEN_contains_info(self):
        payload = App.Payload(nonce=42, created_at=11)
        self.assertIn("42", str(payload))
        self.assertIn("11", str(payload))


class TestApp(unittest.TestCase):

    def setUp(self):
        self.sim = create_test_simulation()
        self.group = Group("group", self.sim.users)
        self.multicast = MagicMock
        self.app = App("app", self.sim, self.group, self.multicast)

    def test_WHEN_get_payload_THEN_has_been_send_and_e2e_logged(self):
        payload = App.Payload(nonce=42, created_at=11)
        m = ApplicationMessage(self.group.users[0], TAG_PAYLOAD, payload, self.group.id)
        m.set_deliver_online_state(Message.DELIVERED_ONLINE)

        self.sim.time = 20
        self.app.on_payload(m.recipient, m, m.body)

        self.assertIn((m.recipient, payload.nonce), self.app.seen_deliveries.set)
        self.assertIn((20, 20-11), self.sim.output.e2e_delays[self.app])

    def test_WHEN_create_payload_THEN_new_nonce_every_time(self):
        self.sim.time = 1
        payload_1 = self.app._create_payload()
        self.sim.time = 2
        payload_2 = self.app._create_payload()

        self.assertEqual(1, payload_1.created_at)
        self.assertEqual(2, payload_2.created_at)
        self.assertGreater(payload_2.nonce, payload_1.nonce)


class TestInteractiveApp(unittest.TestCase):

    def create_app(self):
        self.sim = create_test_simulation()
        self.users = [
            create_static_mobile_user("U_a", online=[False]),
            create_static_mobile_user("U_b", online=[True]),
            create_static_mobile_user("U_c", online=[False]),
            create_static_mobile_user("U_d", online=[True]),
            create_static_mobile_user("U_e", online=[True]),
        ]
        return InteractiveApp(
            name="name", sim=self.sim,
            group=Group("group", self.users),
            multicast_factory=MagicMock,
            init_rate_per_second=0.2,
            heavy_user_percentage=40, heavy_user_weight=4
        )

    def test_WHEN_created_THEN_weights_set_correctly(self):
        app = self.create_app()

        self.assertDictEqual(
            {
                self.users[0]: 4,
                self.users[1]: 4,
                self.users[2]: 1,
                self.users[3]: 1,
                self.users[4]: 1,
            },
            app.user_to_weight
        )

    def test_WHEN_choosing_sender_and_recipient_THEN_close_to_expectations(self):
        app = self.create_app()
        n = 100_000

        sender_counts = {u: 0 for u in self.users}
        for _ in range(n):
            sender = app._choose_online_sender()
            sender_counts[sender] += 1

        self.assertEqual(sender_counts[self.users[0]], 0)  # offline
        self.assertEqual(sender_counts[self.users[2]], 0)  # offline

        self.assertAlmostEqual(sender_counts[self.users[1]], 4/6*n, delta=1000)  # heavy user

        self.assertAlmostEqual(sender_counts[self.users[3]], 1/6*n, delta=1000)  # normal user
        self.assertAlmostEqual(sender_counts[self.users[4]], 1/6*n, delta=1000)  # normal user


class TestInteractiveMultimessageApp(unittest.TestCase):

    def create_app(self):
        self.sim = create_test_simulation()
        self.users = [
            create_static_mobile_user("U_a", online=[True]),
            create_static_mobile_user("U_b", online=[True]),
        ]
        return InteractiveMultimessageApp(
            name="name", sim=self.sim,
            group=Group("group", self.users),
            multicast_factory=MagicMock,
            init_rate_per_second=0.2,
            multi_message=10,
            heavy_user_percentage=40, heavy_user_weight=4
        )

    def test_WHEN_sending_multimessages_THEN_close_to_expectations(self):
        app = self.create_app()
        app.send_payload_to_group = MagicMock()

        n = 10_000

        for _ in range(n):
            app.send_a_message(self.users[0])

        self.assertEqual(app.multi_message * n, app.send_payload_to_group.call_count)
