# Building Controls Simulator

Package for running control loop co-simulations and generation of building 
models using EnergyPlus.

For more information on EnergyPlus whole building simulation see [here](https://energyplus.net/).

## Installation and Setup

To setup this repo open up your bash terminal and follow the commands below. 
Ideally use SSH for git access. If you haven't set that up you can use HTTPS.

```bash
git clone
cd building-controls-simulator
```

### Local Docker Setup

You're going to need Docker installed, if not see https://www.docker.com/.
The bash script `run.sh` provides a minimal CLI to manage the service.

#### Note: Docker images may use up to 8 GB of disk space - make sure you have this available before building.
The size of the container image can be reduced by roughly 3 GB by not installing
every EnergyPlus version in `scripts/setup/install_ep.sh` and not downloading 
all IECC 2018 IDF files in `scripts/setup/download_IECC_idfs.sh`. Simply comment 
out the files you do not need if the extra 3GB is not available.

```bash
# build container (only need to do this once!)
# this will take ~40 minutes, mostly to download all desired versions of EnergyPlus
make build-docker

# run container in interactive mode for first time to set it up with mounted volumes
make run

# select the version of EnergyPlus to use in current environment, this can be changed at any time
# EnergyPlus Version Manager (epvm) script changes env variables and symbolic links to hot-swap version
# by default .bashrc sets version to 8-9-0.
. scripts/epvm.sh 8-9-0

# (optional) download IECC 2018 IDF files to start with
. scripts/setup/download_IECC_idfs.sh

# you're done with setup! now exit container shell or just stop the docker container
# the docker container can now be reattched to, stopped, and restarted when you need it again (see below for usage)
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
# restart a pre-built container with interactive bash shell
make start
```

The default `.bashrc` file should start a jupyter lab server in background and 
then start a pipenv shell with the installed python development environment.

You can check everything is in good working order by running the hello world notebook 
and the tests below or just start using the package and EnergyPlus environment 
using your favourite python IDE or jupyter-lab.

### Example Notebook (Hello World)

This requires that you downloaded the IECC .idf files or have some preexisting building model to work with.
First move the .idf file to the IDR_DIR.

```bash
cp "idf/IECC_2018/cz_2B/SF+CZ2B+USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780+gasfurnace+crawlspace+IECC_2018.idf" "${IDF_DIR}"
```

Next, download the weather file for that geography using https://energyplus.net/weather.
Other weather data can be used as long as it is put into the .epw format.

```bash
EPLUS_WEATHER_URL_USA="https://energyplus.net/weather-download/north_and_central_america_wmo_region_4/USA"
WEATHER_FILE="AZ/USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3/USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.epw"
wget "${EPLUS_WEATHER_URL_USA}/${WEATHER_FILE}" -P "${WEATHER_DIR}"
```

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

Stopping or exitting the container will also shutdown the jupyter server.

### Configuration

The .bashrc at `scripts/setup/.bashrc` can be configured similar to any .bashrc file.
It simply runs commands (rc) whenever an interctive bash shell is opened.

For example removing the line `pipenv run jupyter_lab_bkgrnd` will cause the jupyter
server to not be start in the background.

## Building the Documentation

To build documentation in various formats, you will need [Sphinx](http://www.sphinx-doc.org) and the
readthedocs theme.

```
cd docs/
make html
```

The html files are then available in `docs/build/html`. Open the root file `index.html` 
in a web browser to view them locally.

## Dependendcies

- EnergyPlus: https://github.com/NREL/EnergyPlus
- PyFMI: https://github.com/modelon-community/PyFMI
- EnergyPlusToFMU: https://github.com/lbl-srg/EnergyPlusToFMU
- Eppy: https://github.com/santoshphilip/eppy
- fmi-library: https://github.com/modelon-community/fmi-library
- FMUComplianceChecker: https://github.com/modelica-tools/FMUComplianceChecker

## Contributing

See notes on how to develop this project in [CONTRIBUTING.md](CONTRIBUTING.md)

## Communication

GitHub issues: bug reports, feature requests, install issues, RFCs, thoughts, etc.

## License

Building Controls Simulator is licensed under a BSD-3-clause style license found in the [LICENSE](LICENSE) file.
