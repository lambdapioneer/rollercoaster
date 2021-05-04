import unittest
from unittest.mock import MagicMock

from simulation.messages import *
from simulation.simrandom import *
from simulation.simulation import *


class TestSimulation(unittest.TestCase):

    def test_simulation_ticks_all_objects(self):
        o1, o2 = SimulationObject('o1'), SimulationObject('o2')
        o1.tick = MagicMock()
        o2.tick = MagicMock()

        sim = Simulation('', [o1, o2], SimulationOutput(log_level=None))
        sim.tick(sim)

        o1.tick.assert_called_once()
        o2.tick.assert_called_once()

    def test_simulation_WHEN_messages_send_THEN_delivered_and_locked(self):
        o1, o2 = SimulationObject('o1'), SimulationObject('o2')
        o1.deliver, o1.tick = MagicMock(), MagicMock()
        o2.deliver, o2.tick = MagicMock(), MagicMock()

        output = SimulationOutput(log_level=None)
        sim = Simulation('', [o1, o2], output)

        m = Message(o2, TAG_PAYLOAD, 'body')
        sim.send(o1, m)

        # Assert delivery is happening exactly one round afterwards
        o2.deliver.assert_not_called()
        sim.tick(sim)
        o2.deliver.assert_called_with(sim, m)

    def test_simulation_WHEN_app_messages_THEN_get_by_tag_correct(self):
        o1 = SimulationObject('o1')
        o1.deliver, o1.tick = MagicMock(), MagicMock()

        output = SimulationOutput(log_level=None)
        sim = Simulation('', [o1], output)

        sim.send(o1, Message(o1, TAG_LOOP, 'body'))
        sim.send(o1, Message(o1, TAG_DROP, 'body'))
        sim.send(o1, Message(o1, TAG_PAYLOAD, 'body'))
        sim.send(o1, Message(o1, TAG_DROP, 'body'))

        sim.tick(sim)

    def test_simulation_WHEN_run_THEN_correct_number_of_iterations(self):
        sim = Simulation('', [], SimulationOutput(log_level=None), delta_ms=20)
        sim._tick = MagicMock()
        sim.run(time_ms=3000)
        self.assertEqual(150, sim._tick.call_count)
