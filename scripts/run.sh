#! /usr/bin/env bash

set -o pipefail

# user variables
# ==============================================================================
PACKAGE_NAME="building-control-simulator"
VERSION="0.1.3"
CONTAINER_NAME="${PACKAGE_NAME}"
LOCAL_MNT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"
DOCKER_HOME_DIR="/home/bcs"
DOCKER_LIB_DIR="${DOCKER_HOME_DIR}/lib"
DOCKER_MNT_DIR="${DOCKER_LIB_DIR}/${PACKAGE_NAME}"
DOCKER_CREDS_DIR="${DOCKER_HOME_DIR}/.config/application_default_credentials.json"
# ==============================================================================

while [[ "$#" -gt "0" ]]; do
  case "${1}" in
  -b|--build-docker)
    # build docker container
    docker build "${LOCAL_MNT_DIR}" -t "${CONTAINER_NAME}:${VERSION}"
    ;;
  -l|--install-local)
    # build docker container
    echo "NOT IMPLEMENTED"
    ;;
  -i|--interactive)
    # run docker container interactive bash
    echo "mounting: ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw"
    docker run -it \
      --name "${CONTAINER_NAME}_v${VERSION}" \
      -v "${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw" \
      -p 127.0.0.1:8888:8888 \
      "${CONTAINER_NAME}:${VERSION}" \
      sh -c "bash"
    ;;
  -j|--jupyter)
    # run jupyter-lab server 
    docker run -it \
      --name "${CONTAINER_NAME}_v${VERSION}" \
      -v "${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw" \
      -p 127.0.0.1:8888:8888 \
      "${CONTAINER_NAME}:${VERSION}" \
      sh -c 'pipenv run jupyter-lab --ip="0.0.0.0" --allow-root --no-browser'
    ;;
  -s|--start)
    # start a specific container
    docker start -i "${CONTAINER_NAME}:${VERSION}"
    ;;
  --copy-creds)
    # copy GCP credentials to docker container
    docker cp "$GOOGLE_APPLICATION_CREDENTIALS" "${CONTAINER_NAME}_v${VERSION}:${DOCKER_CREDS_DIR}"
    ;;
  --remove)
    # removes all quited containers
    docker ps -a -q | xargs docker rm
    ;;
  esac
  shift # past argument
  shift # past value
done
