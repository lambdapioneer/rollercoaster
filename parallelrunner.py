import argparse
import gzip
import multiprocessing as mp
import pickle
import random
import sys

# Need to set recursion limit a bit higher for the pickleing operations :)
sys.setrecursionlimit(100_000)


def _run(args):
    try:
        filename = args
        output_filename = filename + '.output'

        with open(filename, 'rb') as f:
            sim = pickle.load(f)

        sim.run(sim.simulation_run_time_ms)
        sim.clean()

        with gzip.open(output_filename, 'wb') as f:
            pickle.dump(sim, f, protocol=-1)

    finally:
        sys.stdout.flush()
        sys.stderr.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'pickles',
        nargs='+',
        type=str,
        help="The pickle files that shall be part of the simulation"
    )
    parser.add_argument(
        '--cpus',
        type=int,
        default=mp.cpu_count(),
        help="The number of parallel processes (default: number of CPUs of the system)."
    )
    args = parser.parse_args()

    filenames = args.pickles
    print("Running with %d processes for %d jobs" %
          (args.cpus, len(filenames)))

    # balances the processing for better estimates of progress
    random.shuffle(filenames)

    process_pool = mp.Pool(args.cpus)
    for i, _ in enumerate(process_pool.imap_unordered(_run, filenames), 1):
        print("--- Finished %d of %d tasks ---" % (i, len(filenames)))
        sys.stdout.flush()

    sys.stdout.flush()
    sys.stderr.flush()
