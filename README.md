# Building Control Simulator

Package for running control loop co-simulations and generation of building 
simulation models using EnergyPlus.

For more information on EnergyPlus simulation see [here](https://ecobee.atlassian.net/wiki/spaces/DAT/pages/810615819/EnergyPlus+Building+Simulation+for+Controller+Testing).

## Installation and Setup

To setup this repo open up your bash terminal and follow along. Ideally use
your SSH key for gitlab. If you haven't set that up just use HTTPS.

```bash
git clone
cd building-control-simulator
```

## Local Docker Setup

You're going to need Docker already installed, if not see https://www.docker.com/.
The bash script `run.sh` provides a minimal CLI to manage the service.

```bash
# build container (only need to do this once!)
. scripts/run.sh -b

# enter container in interactive mode
. scripts/run.sh -i

# (optional) select the version of EnergyPlus to use, this can be done at any time
# EnergyPlus Version Manager (epvm) script changes env variables and symbolic links to hot-swap version
# by default .bashrc sets version to 9-2-0
. scripts/epvm.sh 9-2-0

# (optional) download IECC 2018 IDF files to start with
. scripts/setup/download_IECC_idfs.sh

# you're done with setup! now exit container shell or just stop the docker container
# docker container can now be reattched to, stopped, and restarted when you need it again (see below for usage)
# unless you specifically delete this docker container it can be restarted with the setup already done
# if you delete the container just go through the setup here again
exit
```

## Usage

### Start Container

You can pin the specific container to be restarted by editting the user variable 
`CONTAINER_ID` in `run.sh`. 
This allows you to make any edits to a specific container and not need to rebuild.
Some things are just easier to setup not using Docker, so this is a good place 
for those things.

```bash
# reattach shell to a pre-built container
. scripts/run.sh -s

# (optional) select the version of EnergyPlus to use, this can be done at any time
# EnergyPlus Version Manager (epvm) script changes env variables and symbolic links to hot-swap version
# by default .bashrc sets version to 9-2-0
. scripts/epvm.sh 9-2-0

# start a pipenv shell with the installed python development environment
pipenv shell
```

You can check everything is in good working order by running the tests as described
below or just start using the package and EnergyPlus environment using your favourite python IDE or jupyter-lab.

### Run tests

```bash
python -m pytest tests/python
```

### Jupyter-Lab Server

A jupyter-lab server is setup to run in `.bashrc` when the container starts.
This is accessible locally at: http://localhost:8888/lab

The PID is logged and the server can be stopped manually via:
```bash
kill -15 "$(cat ${JUPYTER_LOG_DIR}/JUPYTER_SERVER_PID.txt)"
```
