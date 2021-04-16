#! /bin/bash

# --rm removes container on exit
# --service-ports causes defined ports to be mapped
# --volume maps volumes individually
source .env
docker-compose run \
    --rm \
    --service-ports \
    --volume=${LOCAL_PACKAGE_DIR}:${DOCKER_PACKAGE_DIR}:consistent\
    --volume=${LOCAL_CONTROLLER_DIR}:${DOCKER_CONTROLLER_DIR}:consistent \
    --volume=${LOCAL_THERMAL_DIR}:${DOCKER_THERMAL_DIR}:consistent \
    --volume=/Users/tom.s/.config/gcloud:${DOCKER_HOME_DIR}/.config/gcloud:ro \
building-controls-simulator bash
