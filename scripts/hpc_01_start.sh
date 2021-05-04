#!/bin/bash
set -e;
USER="!!REPLACEME!!"
IP="!!REPLACEME!!"
FOLDER="mix_sim"

# Create slurms
echo "[ ] Creating slurm files..."
rm -f slurm/*
python3 create_slurms.py;

# Clearing previous
echo "";
echo "[ ] Clearing folder on cluster..."
ssh -t $USER@$IP "rm -fr /home/$USER/$FOLDER/*";

# Upload
echo "";
echo "[ ] Uploading..."
./scripts/clean.sh;
rsync -rv simulation *.py slurm scripts $USER@$IP:$FOLDER;
rsync -rv pickles/*input $USER@$IP:$FOLDER/pickles --progress;
rsync -rv input/schedules* $USER@$IP:$FOLDER/input --progress;

# Start running
echo "";
echo "[ ] Starting jobs..."
ssh -t $USER@$IP "cd $FOLDER; ls slurm/* | xargs -n 1 sbatch";
echo "";
echo "[+] All done"