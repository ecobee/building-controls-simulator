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

#### Note: Docker build may fail if memory or network issues:
Some issues that have occurred on different machines are:
- `apt-get install sudo` failing or other packages not being found by apt-get
    - Verify network connection and build container again
- ` jupyter lab build` failing
    - try setting in Dockerfile command `jupyter lab build --dev-build=False --minimize=False`

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
# the docker container can now be reattached to, stopped, and restarted when you need it again (see below for usage)
# unless you specifically delete this docker container it can be restarted with the setup already done
# if you delete the container just go through the setup here again
exit
```
#### Rebuilding the container

Should something go wrong with the container or it experience an issue during the build
remove the broken containers and images with these docker commands:

```bash
# first list all containers
docker ps -a

#remove containers related to failed build
docker rm <container ID>

# list docker images
docker image ls

# remove docker image
docker rmi <image ID>
```

## Usage

### Start Container

You can pin the specific container to be restarted by editing the user variable 
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

Test files are found in src/python directory alongside source code, they are identified by the naming convention `test_*.py`.
The `pytest` framework used for testing, see https://docs.pytest.org/en/stable/ for details.

```bash
python -m pytest src/python
```

### Authentication with GCP

Copy ${GOOGLE_APPLICATION_CREDENTIALS} into container.

```bash
# on local machine copy credentials to container
make copy-creds
```

```bash
# in container make sure bcs user can read credentials
sudo chown -R "bcs":"bcs" ~/.config/application_default_credentials.json
```

### Jupyter-Lab Server

A jupyter-lab server is setup to run in `.bashrc` when the container starts.
This is accessible locally at: http://localhost:8888/lab

The PID is logged and the server can be stopped manually via:
```bash
kill -15 "$(cat ${JUPYTER_LOG_DIR}/JUPYTER_SERVER_PID.txt)"
```

Stopping or exiting the container will also shutdown the jupyter server.

### Configuration

The .bashrc at `scripts/setup/.bashrc` can be configured similar to any .bashrc file.
It simply runs commands (rc) whenever an interactive bash shell is opened.

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

## External Tools

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
