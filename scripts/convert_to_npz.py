import gzip
import itertools
import numpy as np
import pickle
import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))


def convert_to_nbz(filename):
    with gzip.open(filename, 'rb') as f:
        sim = pickle.load(f)

    arrays = {}
    arrays['sim_time_ms'] = np.array([sim.simulation_run_time_ms])

    arrays['e2e_entries_t'] = np.array(
        [x[0] for x in itertools.chain(*sim.output.e2e_delays.values())],
        dtype='int32')
    arrays['e2e_entries_d'] = np.array(
        [x[1] for x in itertools.chain(*sim.output.e2e_delays.values())],
        dtype='int32')

    arrays['e2e_entries_online_t'] = np.array(
        [x[0] for x in itertools.chain(*sim.output.e2e_delays_online_only.values())],
        dtype='int32')
    arrays['e2e_entries_online_d'] = np.array(
        [x[1] for x in itertools.chain(*sim.output.e2e_delays_online_only.values())],
        dtype='int32')

    arrays['already_seen'] = np.array(sum([x for x in sim.output.already_seen.values()]))

    # arrays['payload_buffer_levels'] = np.array(
    #     [list(x) for _, x in sim.output.payload_buffer_levels.items()],
    #     dtype='int32')
    # arrays['payload_buffer_levels_t'] = np.array(
    #     [t for t, _ in sim.output.payload_buffer_levels.items()],
    #     dtype='int32')

    np.savez_compressed(filename, **arrays)


if __name__ == "__main__":
    convert_to_nbz(filename=sys.argv[1])
