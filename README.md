# Building Control Simulator

Package for running control loop co-simulations and generation of building 
simulation models using EnergyPlus.

For more information on EnergyPlus simulation see [here](https://ecobee.atlassian.net/wiki/spaces/DAT/pages/810615819/EnergyPlus+Building+Simulation+for+Controller+Testing).

## Setup and Installation

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

# set EnergyPlus version with the included manager (it just changes env variables and symboli links)
. scripts/epvm.sh 9-2-0

# exit container shell
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
. scripts/run.sh -s

# in the container shell
. scripts/epvm.sh 9-2-0

# start a pipenv shell with the installed python development environment
pipenv shell
```

Once you've started the container you're away to the races! 
You can check everything is in good working order by running the tests as described
below or just start using the package and EnergyPlus environment via jupyter-lab.

### Run tests

```bash
python -m pytest tests/python
```

### Run Jupyter-Lab Server

Start a local jupyter-lab server over port 8888 and use it in the browser at
http://localhost:8888/lab.

```bash
jupyter-lab --ip="0.0.0.0" --allow-root --no-browser
```
