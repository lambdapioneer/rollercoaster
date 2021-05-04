import math
import random as python_random


class SimRandom():
    """The only random source to be used by the simulation. It's wrapping around an internal
    Random() object with defined seed ensures that runs can are reproducible."""

    def __init__(self, sim, seed=0):
        self._sim = sim
        self._random = python_random.Random()
        self._random.seed(0)
        self._cached_f = {}

    def choice(self, l):
        return self._random.choice(l)

    def choice_with_weights(self, l, weights):
        #opt assert len(l) == len(weights)

        r = self._random.random() * sum(weights)
        for idx, w in enumerate(weights):
            r -= w
            if r <= 0:
                return l[idx]

        #opt assert False, "unreachable" # pragma: no cover

    def sample(self, population, k):
        return self._random.sample(population, k)

    def shuffle(self, l):
        result = l[:]
        self._random.shuffle(result)
        return result

    def coin(self, p):
        return self._random.random() < p

    def poisson_event(self, rate_in_seconds):
        # perf tweak: surprisingly the cache is >10% faster (sim.delta_seconds will not change
        # during the course of our simulations)
        F = self._cached_f.get(rate_in_seconds)
        if not F:
            F = 1.0 - math.exp(-rate_in_seconds * self._sim.delta_seconds)
            self._cached_f[rate_in_seconds] = F
        return self._random.random() < F

    def poisson_delay(self, rate_in_seconds):
        return int(1000 * self._random.expovariate(rate_in_seconds))
