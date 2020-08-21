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

You're going to need Docker Desktop installed, if not see https://www.docker.com/. Docker Compose is used to manage the containers and is included by default in the desktop versions of docker for all systems.

### Using Docker-Compose

`docker-compose.yml` defines the Dockerfile and image to use, ports to map, and volumes to mount. It also defins the env file `.env` to inject environment variables that are needed both to build the container and to be used inside the container. As a user all you need to know is that any API keys or GCP variables are stored here (safely) the default EnergyPlus version is 8-9-0, and this can be changed later very easily. 

Edit `.env` for the following if you want to use these external services:
```bash
...
DYD_GCS_URI_BASE=<Donate your data Google Cloud Service bucket>
DYD_METADATA_URI=<Donate your data meta_data file Google Cloud Service URI>
NREL_DEV_API_KEY=<your key>
NREL_DEV_EMAIL=<your email>
...
```

#### Run with bash (recommended first time setup)

The `docker-compose run` command does most of the set up and can be used again 
to run the container after it is built. The `--service-ports` flag should be set 
to allow access on your host machine to jupyter-lab, see: https://docs.docker.com/compose/reference/run/

```bash
# this command runs the container and builds it if it cannot be found (only need to do this once!)
# this will take ~30 minutes, mostly to download all desired versions of EnergyPlus
# perfect opportunity for a coffee, water, or exercise break
docker-compose run --service-ports building-controls-simulator bash

# select the version of EnergyPlus to use in current environment, this can be changed at any time
# EnergyPlus Version Manager (epvm) script changes env variables and symbolic links to hot-swap version
# by default .bashrc sets version to 8-9-0.
. scripts/epvm.sh 8-9-0

# (optional) download IECC 2018 IDF files to start with
. scripts/setup/download_IECC_idfs.sh

# you're done with setup! now exit container shell or just stop the docker container
# the docker container can now be reattached to, stopped, and restarted when you need it again (see below for usage)
# unless you specifically delete this docker container it can be restarted with the setup already done
exit    # first exit to get out of pipenv shell
exit    # second exit to get out of container shell
```

If you delete the container just go through the setup here again to rebuild it.

##### Note: Docker images may use up to 12 GB of disk space - make sure you have this available before building.
The size of the container image can be reduced to roughly 5 GB by not installing
every EnergyPlus version in `scripts/setup/install_ep.sh` and not downloading 
all IECC 2018 IDF files in `scripts/setup/download_IECC_idfs.sh`. Simply comment
out the files you do not need.

##### Note: Docker build may fail if memory or network issues:
Some issues that have occurred on different machines are:
- `apt-get install` failing or other packages not being found by apt-get
    - Verify network connection and build container again
- `jupyter lab build` failing
    - try setting in Dockerfile command `jupyter lab build --dev-build=False --minimize=False`.

### Run Jupyter Lab Server

A jupyter-lab server is setup to run when the container is brought up by `dockef-compose up`.
This is accessible locally at: http://localhost:8888/lab

Stopping or exiting the container will also shutdown the jupyter server.

```bash
docker-compose up
```

`dockef-compose up` will also build the image if it does not exist already, and then run `scripts/setup/jupyter_lab.sh`.
The container can be shutdown using another terminal on the host via:

```bash
docker-compose down
```

There is also a background script `scripts/setup/jupyter_lab_bkgrnd.sh` if you would like
to keep your bash tty available.

```bash
docker-compose run --service-ports building-controls-simulator bash
# in container, enter virtual env
pipenv shell
# then start jupyter lab server in background
. scripts/setup/jupyter_lab_bkgrnd.sh
```

### Development setup - Using VS Code Remote Containers

Highly recommend VS Code IDE for development: https://code.visualstudio.com/download
If you're not familar with VS Code for Python develpoment check out this guide and [PyCon talk](https://youtu.be/WkUBx3g2QfQ) and guide at: https://pycon.switowski.com/01-vscode/

The Remote Containers extension adds the Remote Explorer tool bar. This can be used to inspect and connect to available Docker containers.
1. `docker-compose up` to run the `building-controls-simulator` container.
2. Right click on `building-controls-simulator` container (will be in "Other Containers" first time) and select "Attach to Container". This will install VS Code inside the container.
3. Install necessary extensions within container: e.g. "Python" extension. The container will be accessible now in "Dev Containers" section within Remote Explorer so the installation only occurs once per container.
4. Use the VS Code terminal to build and run tests, and edit files in VS code as you would on your host machine.

### Deleting and rebuilding the container

Should something go wrong with the container or it experience an issue during the build remove the broken containers and images with these docker commands:

```bash
# first list all containers
docker ps -a

# stop containers if they are still running and inaccessible
docker stop <container ID>

# remove containers related to failed build
docker rm <container ID>

# list docker images
docker images

# remove docker image
docker rmi <image ID>
```

## Weather Data

There are several data sources that can be used. The `WeatherSource` provides methods
to get weather data required for simulations and preprocess it for use in simulation.

The Energy Plus Weather (EPW) format is used and is described in the linked NREL 
technical report: https://www.nrel.gov/docs/fy08osti/43156.pdf

### EnergyPlus EPW Data

The simpliest data source for EPW formated TMY data is from the EnergyPlus website:
https://energyplus.net/weather.


### NSRDB 1991-2005 Archive Data

The archived data contains the most recent TMY3 data with the fields required by the EPW format.
Download the archive from: https://nsrdb.nrel.gov/data-sets/archives.html

Note: The archive is ~3 GB, but only the TMY data (~300MB compressed, 1.7 GB uncompressed) is required and the hourly data can be deleted after download.

Example bash commands to download and extract TMY3 data (if archive format changes these will need to change accordingly):
```bash
cd $WEATHER_DIR
wget https://gds-files.nrelcloud.org/rredc/1991-2005.zip
unzip 1991-2005.zip
cd 1991-2005
rm -rf hourly
cd tmy3
mkdir tmy3_data
mv allmy3a.zip tmy3_data
cd tmy3_data
# be careful, this archive dumps many TMY data files into current directory
unzip allmy3a.zip
cd $WEATHER_DIR
# rename tmy3 directory
mv 1991-2005/tmy3 archive_tmy3
```

your TMY3 cache should have the following structure:
```bash
~/lib/building-controls-simulator/weather/archive_tmy3$ ls
TMY3_StationsMeta.csv  tmy3_data

# and inside tmy3_data, the actual TMY3 data files
~/lib/building-controls-simulator/weather/archive_tmy3$ ls tmy3_data/
690150TYA.CSV  722435TYA.CSV  723540TYA.CSV  724675TYA.CSV  725520TYA.CSV  726685TYA.CSV
690190TYA.CSV  722436TYA.CSV  723544TYA.CSV  724676TYA.CSV  725524TYA.CSV  726686TYA.CSV
690230TYA.CSV  722445TYA.CSV  723545TYA.CSV  724677TYA.CSV  725525TYA.CSV  726700TYA.CSV
699604TYA.CSV  722446TYA.CSV  723546TYA.CSV  724695TYA.CSV  725526TYA.CSV  726770TYA.CSV
700197TYA.CSV  722448TYA.CSV  723550TYA.CSV  724698TYA.CSV  725527TYA.CSV  726776TYA.CSV
700260TYA.CSV  722470TYA.CSV  723560TYA.CSV  724699TYA.CSV  725530TYA.CSV  726785TYA.CSV
700637TYA.CSV  722480TYA.CSV  723565TYA.CSV  724723TYA.CSV  725533TYA.CSV  726797TYA.CSV
...
```

### NREL NSRDB: 

The current NSRDB has TMY and PSM3 data available through its developer API. 
This however does not contain all fields required by the EPW format so those fields
must be back filled with archive TMY3 data from the nearest weather station.

NSRDB PSM3: https://developer.nrel.gov/docs/solar/nsrdb/psm3-download/
NSRDB PSM3 TMY: https://developer.nrel.gov/docs/solar/nsrdb/psm3-tmy-download/

### CDO: https://www.ncdc.noaa.gov/cdo-web/

For potential future integration.

## Usage

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

### .env configuration within container

The environment variables used by this platform can be configured as mentioned above from a `.env` file and `.test.env`

These files can be sourced dynamically using bash:
```bash
set -a && source .env && set +a
```

## Run tests

Test files are found in src/python directory alongside source code, they are identified by the naming convention `test_*.py`.
The `pytest` framework used for testing, see https://docs.pytest.org/en/stable/ for details.

```bash
set -a && source .test.env && set +a && python -m pytest src/python
```

## Authentication with GCP

First authenticate normally to GCP, e.g. using ` gcloud auth`. Then copy `${GOOGLE_APPLICATION_CREDENTIALS}` into the container to access GCP resources with 
the same permissions.

```bash
# on local machine source .env and copy credentials to container
docker cp ${GOOGLE_APPLICATION_CREDENTIALS} <container ID>:/home/bcs/.config/application_default_credentials.json
```

```bash
# in container make sure bcs user can read credentials
sudo chown -R "bcs":"bcs" ~/.config/application_default_credentials.json
```



### Configuration

The .bashrc at `scripts/setup/.bashrc` can be configured similar to any .bashrc file.
It simply runs commands (rc) whenever an interactive bash shell is opened.

## Building the Documentation

To build documentation in various formats, you will need [Sphinx](http://www.sphinx-doc.org) and the
readthedocs theme.

```
cd docs/
make clean
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
