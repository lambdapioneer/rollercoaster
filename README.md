# Mix Network Simulator (Rollercoaster Paper) 🎢

This repository contains a Loopix mix network simulator that accompanies the paper accepted at USENIX Security 2021: "Rollercoaster: An Efficient Group-Multicast Scheme for Mix Networks".

The simulator and tooling allow:
 - Creating new simulation configurations via a Jupyter Notebook.
 - Running these configurations via a deterministic simulator.
 - (Re-)Creating the graphs presented in the paper.

The software in this repository is licensed under the MIT license as described in the `LICENSE` file.

Optionally: For large simulation configurations it contains helper scripts for scheduling the simulator jobs on a computing cluster that can execute slurm files.


## 1) Requirements

Making effective use of this repository requires at least the following:
 - Basic usage of standard developer tools: command line, git, text editor
 - Basic understanding of Python
 - Starting and editing Jupyter Notebooks
 - Creating and running Docker images

The artefact runs on UNIX like systems with a recent version of Docker installed.
The simulations and the resulting data can be large - especially when loaded in Jupyter Notebooks.
I suggest using a machine with at least 16 GiB RAM (preferably more) and 10 GiB of free disk space.
The code has been tested on Ubuntu 20.04 and Mac OS 11.3.

**NOTE FOR AEC: If you do not have access to a Unix-like system with 16GiB, I can provide you with remote access to a server with such capabilities.**


## 2) Documentation

Please read the files within the `docs/` folder before starting experimenting with the code. The walkthrough guide is the main document for the artefact evaluation.

 - [architecture.md](docs/architecture.md) file explains the high-level view of this artefact. This provides understanding of its structure and provides orientation if you are getting lost.
 - [walkthrough.md](docs/walkthrough.md) is a tutorial with a detailed step-by-step description for reproducing the figures from the paper.