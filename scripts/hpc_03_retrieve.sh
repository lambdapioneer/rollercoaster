#!/bin/bash
set -e;
USER="!!REPLACEME!!"
IP="!!REPLACEME!!"
FOLDER="mix_sim"

rsync -rv $USER@$IP:$FOLDER/slurm-*.out slurm/;
rsync -rv $USER@$IP:$FOLDER/pickles/* pickles/;