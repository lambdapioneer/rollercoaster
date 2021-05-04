from simulation.loopix import *
from simulation.messages import *
from simulation.simrandom import *
from simulation.simulation import *


class DummySimulationObject(SimulationObject):

    def __init__(self, name):
        super().__init__(name)
        self.inbox = []

    def deliver(self, sim, m):
        self.inbox.append(m)

    def tick(self, sim):
        # Dummy simulation does not perform any actions
        pass


def create_test_simulation(delta_ms=1, users=7, offline_ids=[], output=False):
    sim_output = SimulationOutput(log_level=1 if output else 999)

    num_entries_schedule = 24 * 60 * 60
    schedules = [
        ([True] if x not in offline_ids else [False]) * num_entries_schedule
        for x in range(users)
    ]

    sim = create_loopix_simulation(
        providers=1,
        users_per_provider=(users, users),
        delta_ms=delta_ms,
        output=sim_output,
        online_schedules=schedules,
    )

    # EXAMPLE: how to add new methods to the test object
    # import types
    # def get_users(self):
    #     return self.users
    # sim.get_users = types.MethodType(get_users, sim)

    return sim


def create_test_simulation_with(objects, delta_ms=1, output=False):
    sim = create_loopix_simulation(
        providers=0,
        users_per_provider=(0, 0),
        mix_layers=0,
        mix_scale=0,
        delta_ms=delta_ms,
        output=SimulationOutput(log_level=1 if output else 999),
    )
    sim.objects = objects
    return sim


def create_static_mobile_user(name, online=[True]):
    return User(
        name=name,
        provider=Provider("test_provider"),
        mix_network=None,
        config=LoopixConfiguration(),
        online_schedule=online * 24 * 3600
    )


def flatten_message(m):
    yield m
    while isinstance(m, WrappedMessage):
        m = m.unwrap()
        if isinstance(m, Message):
            yield m
