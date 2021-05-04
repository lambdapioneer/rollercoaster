import unittest
from unittest.mock import call, MagicMock

from simulation.notebook_utils import *


class TestNotebookUtils(unittest.TestCase):

    def test_notebook_sim_config_WHEN_create_scenario_THEN_overrides_sets(self):
        notebook_sim_config = NotebookSimulationConfig(
            loopix_kwargs={'user_rate_pull': 1337},
            app_kwargs={'init_rate_per_second': 1338},
        )

        sim = create_scenario(16, [16], notebook_sim_config, 'unicast', 1_000)
        self.assertEqual(1337, sim.config.user_rate_pull)
        self.assertEqual(1338, sim.apps[0].init_rate_per_second)

    def test_get_name_WHEN_create_scenario_THEN_information_in_name(self):
        notebook_sim_config = NotebookSimulationConfig(app_kwargs={'init_rate_per_second': 1338},)
        sim = create_scenario(16, [16, 8, 4], notebook_sim_config, 'unicast', 1_000)

        name = get_name_for_sim(sim, 'test-config-name', 'schedule-name', 'strategy-name')

        self.assertIn('m016', name)
        self.assertIn('gs16-8-4', name)
        self.assertIn('test-config-name', name)
        self.assertIn('schedule-name', name)
        self.assertIn('strategy-name', name)

    def test_create_strategy_factory_WHEN_given_args_THEN_strategy_parameters_set(self):
        sim = create_simulation(16, NotebookSimulationConfig().get_loopix_config(), [])

        strategy = create_strategy_factory('rollercoaster-k2-p3-timeout15x-dropoffline')(
            sim, sim.users[0], None, None
        )

        self.assertEqual(strategy.k, 2)
        self.assertEqual(strategy.user.split, 3)
        self.assertEqual(strategy.timeouts_active, True)
        self.assertEqual(strategy.timeout_multiplier, 1.5)
        self.assertEqual(strategy.drop_offline, True)

    def test_create_strategy_factory_WHEN_no_given_args_THEN_default_parameters(self):
        sim = create_simulation(16, NotebookSimulationConfig().get_loopix_config(), [])

        strategy = create_strategy_factory('rollercoaster-k1-notimeout')(
            sim, sim.users[0], None, None
        )

        self.assertEqual(strategy.k, 1)
        self.assertEqual(strategy.user.split, 1)
        self.assertEqual(strategy.timeouts_active, False)
        self.assertEqual(strategy.drop_offline, False)
