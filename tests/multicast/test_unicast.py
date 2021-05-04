import unittest
from unittest.mock import MagicMock

from simulation.apps import NoOperationApp
from simulation.multicast import *

from tests.utils import *


class TestUnicast(unittest.TestCase):

    def test_prepare_WHEN_given_x_users_THEN_x_messages_produced(self):
        sim = create_test_simulation()

        app = NoOperationApp("app", sim, Group("group", sim.users), SequentialUnicastStrategy)
        group = app.group

        sender = group.users[0]
        sender.multicast[group.id].send_to_group("payload")

        messages = sender.out_buffer
        self.assertEqual(len(messages), len(sim.users)-1)

        # check that every recipient receives a messages
        for u in group.users:
            if u == sender:
                continue
            has_match = any(m.recipient == u for m in messages for m in flatten_message(m))
            self.assertTrue(has_match)
