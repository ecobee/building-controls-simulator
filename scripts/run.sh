#! /usr/bin/env bash

function printUsage(){
  cat << EndOfMessage
================================================================================
Building Control Simulator run manager: 
A bash script to manage Building Control Simulator docker containers.
Set user variables to define which container is used.

usage: 
  -b, --build-docker
    build docker container from Dockerfile and tag with {VERSION}.

  -r, --run
    start container {CONTAINER_NAME}:{VERSION} in interactive modewith bash 
    mount volumes
    open port 8888 to local host for jupyter server

  -s, --start
    start recently ran container by name "{CONTAINER_NAME}_v{VERSION}"

  --copy-creds
    copy GCP credentials into docker container

  --remove
    removes all exited containers

for example: . run.sh -b
================================================================================
EndOfMessage
}

# user variables
# ==============================================================================
PACKAGE_NAME="building-control-simulator"
VERSION="0.1.1"
CONTAINER_NAME="${PACKAGE_NAME}"
LOCAL_MNT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"
DOCKER_HOME_DIR="/home/bcs"
DOCKER_LIB_DIR="${DOCKER_HOME_DIR}/lib"
DOCKER_MNT_DIR="${DOCKER_LIB_DIR}/${PACKAGE_NAME}"
DOCKER_CREDS_DIR="${DOCKER_HOME_DIR}/.config/application_default_credentials.json"
# ==============================================================================

# run.sh only takes one (1) positional parameter
case "${1}" in
-b|--build-docker)
  # build docker container
  docker build "${LOCAL_MNT_DIR}" -t "${CONTAINER_NAME}:${VERSION}"
  ;;
-r|--run)
  # run docker container interactive with bash
  echo "mounting: ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw"
  docker run -it \
    --name "${CONTAINER_NAME}_v${VERSION}" \
    -v "${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw" \
    -p 127.0.0.1:8888:8888 \
    "${CONTAINER_NAME}:${VERSION}" \
    sh -c "bash"
  ;;
-s|--start)
  # start recently ran container
  docker start -i "${CONTAINER_NAME}_v${VERSION}"
  ;;
--copy-creds)
  # copy GCP credentials to docker container
  docker cp "${GOOGLE_APPLICATION_CREDENTIALS}" "${CONTAINER_NAME}_v${VERSION}:${DOCKER_CREDS_DIR}"
  ;;
--remove)
  # removes all exited containers
  docker ps -a -q | xargs docker rm
  ;;
-h|--help|""|*)
  # on -h, --help, empty param, or unimplemented option print usage help
  printUsage
  ;;
esac