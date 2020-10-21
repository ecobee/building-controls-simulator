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

`docker-compose.yml` defines the Dockerfile and image to use, ports to map, and volumes to mount. It also specifies the env file `.env` to inject environment variables that are needed both to build the container and to be used inside the container. As a user all you need to know is that any API keys or GCP variables are stored here (safely) the default EnergyPlus version is 8-9-0, and this can be changed later very easily. 

Copy the template files and fill in the variables mentioned below:
```bash
cp .env.template .env
cp docker-compose.yml.template docker-compose.yml
```
Note: `docker-compose` behaviour may be slightly different on your host OS 
(Windows, Mac OS, Linux) with respect to how the expansion of environment 
variables works. If the base `docker-compose.yml` file fails on interpreting 
variables, try inlining those specific variables, e.g. replacing `${LOCAL_PACKAGE_DIR}` 
with `<where you cloned the repo to>/building-controls-simulator`.

Edit in `.env.template`:
```bash
...
LOCAL_PACKAGE_DIR=<where you cloned repo>
...
DYD_GCS_URI_BASE=<Donate your data Google Cloud Service bucket>
DYD_METADATA_URI=<Donate your data meta_data file Google Cloud Service URI>
NREL_DEV_API_KEY=<your key>
NREL_DEV_EMAIL=<your email>
...
```

Now you're ready to build and launch the container!
If you delete the docker image just go through the setup here again to rebuild it.

##### Note: Docker images may use up to 12 GB of disk space - make sure you have this available before building.
The size of the container image can be reduced to roughly 5 GB by not installing
every EnergyPlus version in `scripts/setup/install_ep.sh` and not downloading 
all IECC 2018 IDF files in `scripts/setup/download_IECC_idfs.sh`. Simply comment
out the files you do not need.

## Run BCS with Jupyter Lab Server (option 1)

A jupyter-lab server is setup to run when the container is brought up by `docker-compose up`. This is accessible locally at: http://localhost:8888/lab. 

`docker-compose up` will also build the image if it does not exist already, and then run `scripts/setup/jupyter_lab.sh`.

Stopping or exiting the container will also shutdown the jupyter-lab server.

```bash
docker-compose up
```

The container can be shutdown using another terminal on the host via:

```bash
docker-compose down
```

#### Configure EnergyPlus version

Using this flow of `docker-compose up` and `docker-compose down` you can 
modify the `scripts/setup/.bashrc` file line that targets the EnergyPlus
version, by default this is "8-9-0" which is the minimum version supported.

```bash
. "${PACKAGE_DIR:?}/scripts/epvm.sh" "<x-x-x>"
```

## Run BCS with interactive bash shell (option 2)

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

# you're done with container setup! now exit container shell or just stop the docker container
# unless you specifically delete this docker container it can be restarted with the setup already done
exit    # first exit to get out of pipenv shell
exit    # second exit to get out of container shell
```

There is also a background script `scripts/setup/jupyter_lab_bkgrnd.sh` 
if you would like to run the jupyter-lab server from bash tty and keep your 
prompt available.

```bash
docker-compose run --service-ports building-controls-simulator bash
# in container, enter virtual env
pipenv shell
# then start jupyter lab server in background
. scripts/setup/jupyter_lab_bkgrnd.sh
```

### Open bash shell in running container

If you've run the container with `docker-compose up` or `docker-compose run` 
and need an interactive bash shell inside, lookup the container id with 
`docker ps` then run:

```bash
docker exec -it <running container id> bash
```

## Authentication with GCP

GCP credentials are not required to use the BCS but make accessing data much
easier. If you do not have credentials but have local access to data see 
section below.

First authenticate normally to GCP, e.g. using `gcloud auth`. Then copy `${GOOGLE_APPLICATION_CREDENTIALS}` into the container to access GCP resources with 
the same permissions.

On host machine:
```bash
# on local machine copy credentials to container
docker cp ${GOOGLE_APPLICATION_CREDENTIALS} <container ID>:/home/bcs/.config/application_default_credentials.json
```

Within container:
```bash
# in container make sure bcs user can read credentials
sudo chown "bcs":"bcs" ~/.config/application_default_credentials.json
```

## Using locally cached data

Instead of using GCS access to download data you can use a locally cached
DYD files following the format: `data/cache/GCSDYD/<hashed ID>.csv.zip`.

Simply save the files using this format and you can use them in local simulations.

## Docker Issues

Some issues that have occurred on different machines are:

### Build issues

- `apt-get install` failing or other packages not being found by apt-get
    - Verify network connection and build container again
- `jupyter lab build` failing
    - try setting in Dockerfile command `jupyter lab build --dev-build=False --minimize=False`.

### File permissions issues

1. After switching branches on host machine mounted volumes give permissions
errors when access is attempted within docker container.
    - on Mac OS permissions for Full Disk Access must be given to Docker App. 
    This is found in Settings > Security & Privacy > Full Disk Access. See answer 1 in https://stackoverflow.com/questions/64319987/docker-compose-volume-started-acting-weird-no-permissions-on-files-after-switch


## Usage

### Example Notebook (Hello World)

First move the test .idf file to the `$IDF_DIR`.

```bash
cp "test/idf/v8-9-0/AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles.idf" "${IDF_DIR}"
```

Next, download the weather file for that geography using https://energyplus.net/weather.
Other weather data can be used as long as it is put into the .epw format.

```bash
EPLUS_WEATHER_URL_USA="https://energyplus.net/weather-download/north_and_central_america_wmo_region_4/USA"
WEATHER_FILE="AZ/USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3/USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.epw"
wget "${EPLUS_WEATHER_URL_USA}/${WEATHER_FILE}" -P "${WEATHER_DIR}"
```

### Example Notebook with Donate Your Data (DYD)

Support for ecobee Donate Your Data (DYD) is included with the GCSDYDSource. 
For example usage see `notebooks/demo_GCSDYDSource.ipynb`.
The `GCSDYDSource` supports using a local cache of the data files. Simply copy them using 
format `data/cache/GCSDYD/<hash ID>.csv.zip`, for example:

```bash
$ ls data/cache/GCSDYD
2df6959cdf502c23f04f3155758d7b678af0c631.csv.zip
6e63291da5427ae87d34bb75022ee54ee3b1fc1a.csv.zip
4cea487023a11f3bc16cc66c6ca8a919fc6d6144.csv.zip
f2254479e14daf04089082d1cd9df53948f98f1e.csv.zip
...
```

For information about the ecobee DYD program please see: https://www.ecobee.com/donate-your-data/.

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

### Run the tests

Test files are found in src/python directory alongside source code, they are identified by the naming convention `test_*.py`.
The `pytest` framework used for testing, see https://docs.pytest.org/en/stable/ for details.

Similarly to the `.env` file, you can set up `.test.env` from `.test.env.template`.
Then simply run the `test_env_setup.sh` script to set up the test environment.

```bash
. scripts/setup/test_env_setup.sh
```

This just runs the following commands in your terminal to test up the test env vars:
```bash
set -a && source .test.env && set +a
. scripts/epvm.sh 8-9-0
```

Finally, run all the tests:
```bash
python -m pytest src/python
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
