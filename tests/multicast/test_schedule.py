import unittest
from simulation.multicast.schedule import *

_U = [0, 1, 2, 3, 4, 5, 6]


class TestSchedule(unittest.TestCase):

    def test_gen_schedule_WHEN_k1_THEN_matches_expectations(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        self.assertEqual(
            schedule.S,
            [
                (0, [(0, 1), ]),
                (1, [(0, 2), (1, 3), ]),
                (2, [(0, 4), (1, 5), (2, 6), ]),
            ]
        )

    def test_gen_schedule_WHEN_k2_THEN_matches_expectations(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=2)
        self.assertEqual(
            schedule.S,
            [
                (0, [(0, 1), (0, 2), ]),
                (1, [(0, 3), (0, 4), (1, 5), (1, 6), ]),
            ]
        )

    def test_gen_schedule_WHEN_seed_not_zero_THEN_result_different(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=2, nonce=1)
        self.assertEqual(
            schedule.S,
            [
                (0, [(0, 3), (0, 4), ]),
                (1, [(0, 6), (0, 1), (3, 5), (3, 2), ]),
            ]
        )

    def test_next_receiver_WHEN_has_following_recipient_THEN_that_one_is_returned(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=2)
        self.assertEqual(schedule.get_next_receiver(1), 2)
        self.assertEqual(schedule.get_next_receiver(2), 3)
        self.assertEqual(schedule.get_next_receiver(3), 4)
        self.assertEqual(schedule.get_next_receiver(4), 5)
        self.assertEqual(schedule.get_next_receiver(5), 6)

    def test_next_receiver_WHEN_has_no_following_recipient_THEN_source_returned(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=2)
        self.assertEqual(schedule.get_next_receiver(6), 0)


class TestGraph(unittest.TestCase):

    def test_graph_traversal_WHEN_given_schedule_THEN_contains_entire_subtree(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        in_order = schedule.get_recursive_children(0)
        self.assertSetEqual(set(in_order), {1, 2, 3, 4, 5, 6})

    def test_graph_parents_WHEN_given_schedule_THEN_contains_parents_in_up_going_order(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        self.assertListEqual(schedule.get_parents(6), [2, 0])

    def test_graph_hops_between_WHEN_given_schedule_THEN_matches_number_of_links(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        self.assertEqual(schedule.get_hops_between(6, 6), 0)
        self.assertEqual(schedule.get_hops_between(2, 6), 1)
        self.assertEqual(schedule.get_hops_between(0, 2), 1)
        self.assertEqual(schedule.get_hops_between(0, 6), 2)

    def test_get_esimated_rtt_WHEN_to_direct_of_source_THEN_matches_twice_round_trip(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        estimate = schedule.get_estimated_rtt(4, 4, t_message=10, t_queue=1)
        self.assertEqual(estimate, 10 + 1 + 10)

    def test_get_esimated_rtt_WHEN_to_child_of_other_node_THEN_matches_our_information(self):
        schedule = Schedule(source=_U[0], all_users=_U, k=1)
        estimate = schedule.get_estimated_rtt(2, 6, t_message=10, t_queue=1)
        self.assertEqual(estimate, 10 + 2 + 10 + 1 + 10)
