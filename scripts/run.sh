#! /usr/bin/env bash

set -o pipefail

# user variables
# ==============================================================================
CONTAINER_ID="c3dd7717bb6f"
# ==============================================================================

PACKAGE_NAME="building-control-simulator"
VERSION="0.1.1"
CONTAINER_NAME="${PACKAGE_NAME}"
LOCAL_MNT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"
DOCKER_LIB_DIR="/root/home/lib"
DOCKER_MNT_DIR="${DOCKER_LIB_DIR}/${PACKAGE_NAME}"

while [[ "$#" -gt "0" ]]; do
  code="$1"
  case $code in
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
    docker run -it \
      -v "${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw" \
      -p 127.0.0.1:8888:8888 \
      "${CONTAINER_NAME}:${VERSION}" \
      sh -c "bash"
    ;;
  -j|--jupyter)
    # run jupyter-lab server 
    docker run -it \
      -v "${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw" \
      -p 127.0.0.1:8888:8888 \
      "${CONTAINER_NAME}:${VERSION}" \
      sh -c 'pipenv run jupyter-lab --ip="0.0.0.0" --allow-root --no-browser'
    ;;
  -s|--start)
    # start a specific container
    docker start -i "${CONTAINER_ID}"
    ;;
  --remove)
    # removes all quited containers
    docker ps -a -q | xargs docker rm
    ;;
  esac
  shift # past argument
  shift # past value
done
