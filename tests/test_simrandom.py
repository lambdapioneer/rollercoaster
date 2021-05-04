import statistics
import unittest

from simulation.simrandom import *

class SimulationMock:
    
    def __init__(self, delta_seconds=0.001):
        self.delta_seconds = delta_seconds


class TestSimrandom(unittest.TestCase):

    def _test_poisson_event(self, rate, n=500_000):
        sim = SimulationMock(delta_seconds=0.002)  # 2ms
        r = SimRandom(sim)

        cnt = 0
        for _ in range(n):
            cnt += 1 if r.poisson_event(rate) else 0

        self.assertAlmostEqual(
            first=cnt/(sim.delta_seconds*n),
            second=rate,
            delta=0.15*rate  # allow 15% error
        )

    def test_poisson_event_WHEN_rate_less_one_THEN_matches_excpected_value(self):
        self._test_poisson_event(0.1)

    def test_poisson_event_WHEN_rate_equal_one_THEN_matches_excpected_value(self):
        self._test_poisson_event(1)

    def test_poisson_event_WHEN_rate_greater_one_THEN_matches_excpected_value(self):
        self._test_poisson_event(10)

    def test_poisson_delay_WHEN_rate_THEN_matches_expected_value(self):
        r = SimRandom(SimulationMock())

        rate, n = 2, 100_000
        delays = [r.poisson_delay(rate) for _ in range(n)]
        self.assertAlmostEqual(
            first=statistics.mean(delays),
            second=1000/rate,
            delta=10,
        )
        self.assertAlmostEqual(
            first=statistics.stdev(delays),
            second=1000*math.sqrt(1/(rate*rate)),
            delta=10,
        )

    def test_random_shuffle_WHEN_given_list_THEN_original_list_not_modified(self):
        r = SimRandom(SimulationMock())

        l = [0, 1, 2, 3, 4]
        l2 = r.shuffle(l)
        self.assertEqual(l, [0, 1, 2, 3, 4])
        self.assertNotEqual(l, l2)

    def test_coin_WHEN_given_fair_coin_THEN_50_50(self):
        r, n = SimRandom(SimulationMock()), 10_000

        throws = [r.coin(p=0.5) for _ in range(n)]
        num_heads = sum(1 if c else 0 for c in throws)

        self.assertAlmostEqual(num_heads, n/2, delta=100)

    def test_sample_WHEN_given_numbers_THEN_average_close_to_average(self):
        r, n, k = SimRandom(SimulationMock()), 100_000, 2

        arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        s = sum([sum(r.sample(arr, k)) for _ in range(n)])

        self.assertAlmostEqual(s/k, n*statistics.mean(arr), delta=1000)

    def test_choice_with_weights_WHEN_weights_same_THEN_average_is_average(self):
        r, n = SimRandom(SimulationMock()), 100_000

        arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        avg = statistics.mean([r.choice_with_weights(arr, weights) for _ in range(n)])

        self.assertAlmostEqual(avg, statistics.mean(arr), delta=0.01)

    def test_choice_with_weights_WHEN_one_item_higher_THEN_average_is_average_of_representative_arr(self):
        r, n = SimRandom(SimulationMock()), 100_000

        arr = [1, 2, 3]
        weights = [1, 1, 3]

        avg = statistics.mean([r.choice_with_weights(arr, weights) for _ in range(n)])

        actual_arr = [1, 2, 3, 3, 3]
        self.assertAlmostEqual(avg, statistics.mean(actual_arr), delta=0.01)

