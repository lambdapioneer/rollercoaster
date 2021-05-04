from simulation.messages import VALID_TAGS, Message
from simulation.simrandom import SimRandom

from collections.abc import Iterable


class SimulationObject():

    def __init__(self, name):
        self.name = name

    def deliver(self, sim, m):  # pragma: no cover
        raise NotImplementedError("deliver() must be implemented when receiving messages")

    def tick(self, sim):  # pragma: no cover
        raise NotImplementedError("tick() must be implemented")

    def __repr__(self):
        return self.name.upper()


class RecursiveSimulationObject(SimulationObject):

    def __init__(self, name, objects=None):
        super().__init__(name)
        self.objects = objects if objects else []


class SimulationOutput():

    def __init__(self, log_level=0):
        self.log_level = log_level if log_level else 999

        self.e2e_delays = {}  # app -> [(int, int)]
        self.e2e_delays_online_only = {}  # app -> [(int, int)]

        self.already_seen = {}  # app -> count

    def log(self, sim, who, what, level):
        if level >= self.log_level:
            t = "%06d %10s: %s" % (sim.time, who, what)
            print(t)

    def log_e2e_delay(self, sim, msg, app, delay):
        """Called from the `App` whenever a payload is received for the first time by 
        a recipient. It will log tuples of `(sim_time, e2e_delay)` with key `app`.
        """
        if app not in self.e2e_delays:
            self.e2e_delays[app] = []
            self.e2e_delays_online_only[app] = []

        self.e2e_delays[app].append((sim.time, delay))

        if msg.get_delivery_online_state() == Message.DELIVERED_ONLINE:
            self.e2e_delays_online_only[app].append((sim.time, delay))

    def log_already_seen(self, app):
        """Called from the `App` whenever a payload was already seen (i.e. when a recipient
        receives a re-transmission). For every delivered payload message either `log_e2e_delay`
        or `log_already_seen` is being called.
        """
        if app not in self.already_seen:
            self.already_seen[app] = 0

        self.already_seen[app] += 1


class Simulation(RecursiveSimulationObject):

    def __init__(self, name, objects, output, delta_ms=1, seed=0):
        super().__init__(name, objects)
        self.time = 0  # Total time passed in ms
        self.messages_in_transit = []
        self.output = output
        self.users = []

        # Global random generator for this simulation
        self.rnd = SimRandom(self, seed=seed)

        # Delta time steps in ms
        self.delta_ms = delta_ms

        # Perf tweak: precompute float for simrandom
        self.delta_seconds = delta_ms / 1000.0

    def log(self, who, what, level=1):
        self.output.log(self, who, what, level)

    def send(self, sender, m):
        # Commented-out as optimization
        # self.log(self, "Sending message '%s' -> '%s'" % (sender, m.recipient), level=1)

        self.messages_in_transit.append(m)

    def clean(self):
        for o in filter(lambda v: hasattr(v, 'clean'), self.objects):
            o.clean()

    def after_round(self):
        for m in self.messages_in_transit:
            m.recipient.deliver(self, m)
        self.messages_in_transit = []

    def tick(self, sim):
        """The simulation will evaluate for the current time and then
        increase by delta_ms."""
        #opt assert self == sim
        self._tick()

    def _tick(self):
        for o in self.objects:
            o.tick(self)
        self.time += self.delta_ms
        self.after_round()

    def run(self, time_ms):
        iterations = time_ms // self.delta_ms
        for _ in range(iterations):
            self._tick()

            if self.time % 100_000 == 0:
                self.log(
                    who=self,
                    what="progress %.2f%%" % (100 * self.time / time_ms),
                    level=20
                )
