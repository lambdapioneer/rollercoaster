#!/bin/bash
set -e;
cat slurm/*out | grep "User time (seconds)" | tr -dc '0-9.\n' > slurm/runtime-cpu-user-seconds.txt;
find ./pickles -type f -name "*output" | parallel --bar -P 4 nice python3 ./scripts/convert_to_npz.py;
