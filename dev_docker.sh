#! /bin/bash

# --rm removes container on exit
# --service-ports causes defined ports to be mapped
# --volume maps volumes individually
source .env
docker-compose run \
    --rm \
    --service-ports \
    --volume=${LOCAL_PACKAGE_DIR}:${DOCKER_PACKAGE_DIR}:consistent\
building-controls-simulator bash
