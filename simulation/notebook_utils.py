from simulation.apps import InteractiveMultimessageApp
from simulation.loopix import create_provider_with_users, LoopixConfiguration, LayeredMixNetwork, LoopixSimulation, SimulationOutput
from simulation.multicast import create_factory, Group, SequentialUnicastStrategy, RollercoasterStrategy
from simulation.simrandom import SimRandom

import math
import os
import pickle


def create_strategy_factory(name):
    """Creates a new strategy factory following the name scheme:
     - unicast
     - rollercoaster-k2-p1
     - rollercoaster-k2-p2-timeout15x
     - rollercoaster-k2-p2-timeout15x-dropoffline
    """
    parts = name.split('-')
    if parts[0] == 'unicast':
        return SequentialUnicastStrategy

    elif parts[0] == 'rollercoaster':
        kwargs = {
            'timeouts_active': False,
            'drop_offline': False,
        }
        for arg in parts[1:]:
            if arg.startswith('k') or arg.startswith('p'):
                kwargs[arg[0]] = int(arg[1:])
            elif arg.startswith('timeout'):
                kwargs['timeouts_active'] = True
                kwargs['timeout_multiplier'] = float(arg[7:9]) / 10.0
            elif arg.startswith('notimeout'):
                kwargs['timeouts_active'] = False
            elif arg.startswith('dropoffline'):
                kwargs['drop_offline'] = True
            else:
                raise ValueError("Unknown parameter: %s" % arg)

        if 'timeouts_active' not in kwargs:
            raise ValueError("Timeout not specified")
        return create_factory(RollercoasterStrategy, **kwargs)

    else:
        raise ValueError("Unkown strategy name: %s" % parts[0])


class NotebookSimulationConfig(object):

    def __init__(self, loopix_kwargs=None, app_kwargs=None):
        self.loopix_kwargs = loopix_kwargs if loopix_kwargs else dict()
        self.app_kwargs = app_kwargs if app_kwargs else dict()

    def derive_new(self, delta_loopix_kwargs=None, delta_app_kwargs=None):
        return NotebookSimulationConfig(
            loopix_kwargs=dict(
                self.loopix_kwargs,
                **(delta_loopix_kwargs if delta_loopix_kwargs else dict())),
            app_kwargs=dict(
                self.app_kwargs,
                **(delta_app_kwargs if delta_app_kwargs else dict())),
        )

    def get_loopix_config(self):
        return LoopixConfiguration(**self.loopix_kwargs)


def create_app(sim, group, strategy_name, app_kwargs, app_name="app"):
    return InteractiveMultimessageApp(
        app_name, sim, group,
        multicast_factory=create_strategy_factory(strategy_name),
        **app_kwargs
    )


def create_simulation(m, config, online_schedules):
    # setup network
    network = LayeredMixNetwork(num_layers=3, mix_per_layer=3, config=config)

    # setup providers and users
    max_users_per_provider = 16

    providers, users = [], []
    for provider_idx in range(math.ceil(m / max_users_per_provider)):
        u_count = max_users_per_provider if m > max_users_per_provider else m
        m -= max_users_per_provider

        provider, provider_users = create_provider_with_users(
            "P%d" % provider_idx,
            network, u_count, config, online_schedules)
        providers.append(provider)
        users += provider_users

    return LoopixSimulation(
        network, providers, users,
        output=SimulationOutput(log_level=15),
        delta_ms=10,
        config=config)


def create_scenario(m, group_sizes, notebook_sim_config, strategy_name, time_ms, online_schedules=[]):
    sim = create_simulation(m, notebook_sim_config.get_loopix_config(), online_schedules)
    sim.simulation_run_time_ms = time_ms  # indicator for the parallelrunner.py

    r = SimRandom(sim=None, seed=0)
    for gid, gs in enumerate(group_sizes):
        users = r.sample(sim.users, gs)
        app = create_app(sim, Group("group_%d" % gid, users), strategy_name, notebook_sim_config.app_kwargs)
        sim.add_app(app)

    return sim


def get_name_for_sim(sim, config_name, offline_schedule_name, strategy_name):
    return get_name(
        m=len(sim.users),
        group_sizes=[len(app.group.users) for app in sim.apps],
        config_name=config_name,
        offline_schedule_name=offline_schedule_name,
        strategy_name=strategy_name,
    )


def get_name(m, group_sizes, config_name,  offline_schedule_name, strategy_name):
    gs_text = "-".join([str(gs) for gs in group_sizes])
    return ("SIM_M%03d_GS%s_%s_%s_%s.input" % (
        m,
        gs_text,
        config_name,
        offline_schedule_name,
        strategy_name
    )).lower()


def pickle_down(outputs):
    folder = 'pickles'
    for filename, sim in outputs.items():
        path = os.path.join(folder, filename)
        with open(path, 'wb') as f:
            pickle.dump(sim, f, protocol=-1)
