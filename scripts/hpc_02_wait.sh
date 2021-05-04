#!/bin/bash
set -e;
USER="!!REPLACEME!!"
IP="!!REPLACEME!!k"

ssh $USER@$IP -t "watch -n 1 'gstatement | grep -v COMPLETED'"
