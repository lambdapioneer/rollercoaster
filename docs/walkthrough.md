# Walkthrough Step-by-Step Guide

This document walks you (the reader) through the process of running all parts of this artefact.
It explains how to create the figures shown in the paper.
However, to reduce the total compute time for the simulation, I suggest to use a smaller simulated time span (1 hour instead of 24 hours).
It is clearly marked how you can change this and what discrepancies to expect.
I also explain how to download pre-baked simulation results for the full time span.

I suggest that you read [`architecture.md`](architecture.md) before going through this file.

The total expected time required is:
 - <4h human time (active work by you)
 - <12h compute time (wall time on a modern computer)


## 1) Setup (25min human time; 1h compute time)

The following steps only need to be executed once for the initial setup.

### 1.1) Ensuring Docker is available (10min human time)

Run:
```
docker --version
```

If you receive a version number, Docker is installed.
We tested this guide with Docker version 20.10.2.
If you get an error, please install Docker on your system.

Run:
```
docker ps
```

If it outputs a (possibly empty) table, you have the correct Docker permissions.
If you get a "permission denied" error message, you are missing access rights.
You can either (a) run the following commands as `root` or (b) follow the [Docker instructions for adding yourself to the docker group](https://docs.docker.com/engine/install/linux-postinstall/).

**For Mac OS users:** On Macs some Docker installations by default do not allow Docker to access all CPU cores and RAM.
You can change these in the [advanced settings as explained here](https://docs.docker.com/docker-for-mac/).
This is highly recommended as the simulation is computationally intensive.


### 1.2) Downloading this repository (5min human time)

Clone this repository and make it the current working folder.

Run:
```
git clone https://github.com/lambdapioneer/rollercoaster.git
cd rollercoaster
```


### 1.3) Building Docker image (5min human time; 15min-1h compute time)

Form inside the repository build the Docker images with a Python environment.
One is based on CPython (for Jupyter Notebooks) and one is using PyPy (for running the simulations).

Run:
```
./scripts/docker_01_build.sh
```

You should see the output from Docker building the images.

The reason for having two is that PyPy currently has some incompatibles with numpy which is used for creating graphs.
On the other hand, the simulation runs up to 300% faster in PyPy.


### 1.4) Verifying Setup by running unit tests (5min human time)

Run:
```
./scripts/docker_02_tests.sh
```

You should see the Python tests being executed twice (once for each Docker image).
Each executions contains a coverage report similar to the following:

```
[...]
Ran 59 tests in 6.753s

OK
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
simulation/__init__.py                      0      0   100%
simulation/apps.py                         67      9    87%
[...]
simulation/simulation.py                   67      5    93%
simulation/utils.py                        72      0   100%
-----------------------------------------------------------
TOTAL                                     865     61    93%
```


## 2) Creating simulations (5min human time; 5min compute time)

The following step starts Jupyter within the Docker container and makes the port 8888 available to localhost.
It also mounts the folder `pickles/` so it is accessible within the Docker container (for saving the configurations).

Run:
```
./scripts/docker_03_jupyter_notebook.sh
```

Open the link starting with `http://127.0.0.1:8888/?token=` shown in the console to access Jupyter in your browser.
Click on `create_simulations` to open the respective notebook.

**CHANGE SIMULATED TIMESPAN:** Change `SIM_TIME_MS = 24 * 3_600 * 1_000` to `SIM_TIME_MS = 1 * 3_600 * 1_000` in the second cell for running shorter simulations (recommended).
You can later download the pre-baked results for the full 24h simulation results.

Click on `Kernel` in the top menu and then `Restart & Run All`.
The entire execution can take up to 5 minutes.

In a new terminal navigate to the Rollercoaster folder and run `ls pickles/*input | wc -l` to confirm that 276 new configuration files have been created.
Close the new terminal.

To stop the Jupyter server, press `CTRL+C` within the terminal running Docker.
Confirm with `y`.


## 3) Running simulations (5min human time; 8h compute time)

The following step starts the `parallelrunner.py` for all created simulation configurations.
If you have chosen a simulated time span of `1h`, this can take up to 8h of wall time on a modern computer.
In our test runs (recent i7 CPUs, 8 cores) this step took about two hours.
It is safe to run this in the background.
However, it has no mechanism to resume once cancelled.

Run:
```
./scripts/docker_04_run_parallelrunner.sh
```

During the executing you will see updates of the individual tasks in a format like: `$SIMTIME $SIMNAME: progress 13.37%`.
For every completed simulation it outputs a line in the format: `--- Finished 38 of 276 tasks ---`.
Use this for an educated guess how long this will run on your machine.

Once finished, run `ls pickles/*output | wc -l` to confirm that 276 new simulation result files have been created.

**Optional:** If the simulation is aborted for any reason, you can use `scripts/list_missing_outputs.py` to generate a list of simulations that have to be re-run.


## 4) Pre-processing results (5min human time; 10min compute time)

The following step converts the simulation results from the pickle format into a compressed numpy array format that is more efficient to load.

Run:
```
./scripts/docker_05_process_results.sh
```

This will not output any information and will run for up to 10 minutes (for the simulated time span of 1h).
You can use your system's process monitor (e.g. `htop`) or simply `ls pickles/*npz` to observe progress.

Once finished, run `ls pickles/*npz | wc -l` to confirm that 276 new compressed numpy array files have been created.


## 5) Creating graphs (5min human time; 10min compute time)

The following step starts Jupyter within the Docker container and makes the port 8888 available to localhost.
It also mounts the folders `pickles/` and `output/` so they are accessible within the Docker container (for reading the simulation results and saving the generated graphs).

Run:
```
# [!] This is different from the *_03_*.sh script
./scripts/docker_06_jupyter_notebook.sh
```

Open the link starting with `http://127.0.0.1:8888/?token=` shown in the console to access Jupyter in your browser.
Click on `create_all_graphs` to open the respective notebook.

**CHANGE CODE:** Change `DEFAULT_MS = 24 * 3_600 * 1_000` to `DEFAULT_MS = 1 * 3_600 * 1_000` in the third cell for running shorter simulations.
You can later download the pre-baked results for the full 24h simulation results.

Click on `Kernel` in the top menu and then `Restart & Run All`.
The entire execution can take up to 10 minutes.

You should be able to see all graphs from the paper within the Notebook and as .png/.pdf files within the `output/` folder.
If running with just 1h of simulated time (as recommended), you will see the following discrepancies:
 - The errors are larger in all figures
 - The Y-Axis for histograms are mislabelled.
 - The results for offline simulations are different.
   - In particular, in Figure 6 *Rollercoaster without fault-tolerance* (green) appears to perform better than it actually does. This is because some of the inner nodes tasked with forwarding messages have not come online at all yet.

The comments in the notebook file and the table in [`output/file_to_figure_mapping.md`](../output/file_to_figure_mapping.md) explain the mapping between the created output and the figures in the paper.

To stop the Jupyter server, press `CTRL+C` within the terminal running Docker.
Confirm with `y`.


## 6): Downloading and plotting the pre-baked results

This step downloads and extracts pre-backed results for a 24h simulation time span.
**This will override existing .npz files** - please copy them to a save location beforehand.

Use the following link for the download: [https://drive.google.com/file/d/1LKofvxmd9YioWdx2vF2LYDa6xf4Fo0Kj/view](https://drive.google.com/file/d/1LKofvxmd9YioWdx2vF2LYDa6xf4Fo0Kj/view).
The download is started using the icon with the downward arrow in the top-right corner.

Run:
```
# copying the file to the root folder of this repo
cp ../your/location/24h_results.zip .
unzip 24h_results.zip
```

Alternatively, you can extract the archive manually.

Afterwards, re-run step "5) Creating Graphs" while making sure to change the code back to `DEFAULT_MS = 24 * 3_600 * 1_000`.

The resulting graphs should be (almost) identical with the ones from the paper.


## Optional: Running the simulation on a computing cluster

This section provides a quick overview of the tooling that I used for running larger simulation configurations on the [Cambridge High Performance Computing cluster](https://www.hpc.cam.ac.uk/high-performance-computing).
If you have access to a system that is managed via `slurm`, then the following steps might help you.
Unfortunately, I cannot provide detailed instructions as all systems are slightly differently.

- Get access to the HPC service (obvious, but might take some time).
- Install PyPy on the HPC and all required dependencies.
- Inspect the scripts `scripts/hpc_{01_start,02_wait,03_retrieve,04_preprocess}.sh` and `create_slurms.py`.
  - Update all paths, usernames, hostnames to match your configuration.
- Clear your `pickles/` folder.
- Create the simulation configurations as before.
- Run in `scripts/hpc_01_start.sh` and observe the jobs in the HPC scheduler (or wait until its your turn).
- Once finished run `scripts/hpc_03_retrieve.sh` and `scripts/hpc_04_preprocess.sh` to download and pre-process the results.
- Create graphs as usual.


## Optional: Remove the docker images from your machine

You can clean most of the disk space used by the Docker image using the following command:

Run:
```
docker image rm -f rollercoaster
docker image rm -f rollercoaster-pypy
```
