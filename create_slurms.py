from simulation.utils import *

import pathlib

# Create SLURM scripts
header = """#!/bin/bash
#SBATCH --account !!REPLACEME!!
#SBATCH -J !!REPLACEME!!
#SBATCH --partition !!REPLACEME!!
#SBATCH --nodes 1
#SBATCH --ntasks=%d
#SBATCH --cpus-per-task=1
#SBATCH --time=11:59:59
"""

# smaller values lead to more jobs scheduled, but also
# prevents reserving many CPU just because one task is
# running long; 8 seems like a reasonable trade-off
cpu_per_node = 8

python_exec = "/home/!!REPLACEME!!/pypy3.6/bin/pypy3.6"

all_filenames = ['pickles/' + x.name for x in pathlib.Path('pickles').glob("*.input")]

print("Picked up *.input files:", len(all_filenames))

cmd_base = ['/bin/time', '-v', python_exec, 'parallelrunner.py', '--cpus', str(cpu_per_node)]
job_id = 1
for batch in chunkify(all_filenames, cpu_per_node):
    cmd = " ".join(cmd_base + batch)
    slurm_filename = 'slurm/job_%02d.slurm' % job_id
    with open(slurm_filename, 'w') as f:
        f.write(header % len(batch))
        f.write(cmd + ';\n')
    job_id += 1
    print("Wrote", slurm_filename, "containing", len(batch), "jobs")