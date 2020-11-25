#!/bin/bash

# bash script to install EnergyPlus releases from:
# https://github.com/NREL/docker-energyplus/blob/develop/Dockerfile

set -eu
# -e exit on first error
# -u exit when an undefined variable such as $FOO is accessed
# -o pipefail exit when | any |cmd | in | a | pipe has exitcode != 0
# -x print all commands (debug only)

function install_ep () {
  local _ENERGYPLUS_INSTALL_VERSION="${1}"
  local ENERGYPLUS_SHA="${2}"
  local _ENERGYPLUS_INSTALL_DIR="${3}"
  # this location is default for EnergyPlus and is hardcoded in some releases
  local DEFAULT_ENERGYPLUS_DIR="/usr/local"
  local ENERGYPLUS_VERSION=$( echo "${_ENERGYPLUS_INSTALL_VERSION}" | tr "-" ".")
  local ENERGYPLUS_TAG="v${ENERGYPLUS_VERSION}"
  local ENERGYPLUS_DOWNLOAD_BASE_URL="https://github.com/NREL/EnergyPlus/releases/download/${ENERGYPLUS_TAG}"
  
  # handle the different install script, manually force the install dir
  if [[ "${_ENERGYPLUS_INSTALL_VERSION}" == "9-1-0" ]]; then
    local ENERGYPLUS_DOWNLOAD_FILENAME="EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-x86_64.sh"
    local ENERGYPLUS_DOWNLOAD_URL="${ENERGYPLUS_DOWNLOAD_BASE_URL}/${ENERGYPLUS_DOWNLOAD_FILENAME}"
    curl -SLO "${ENERGYPLUS_DOWNLOAD_URL}"
    chmod +x "${ENERGYPLUS_DOWNLOAD_FILENAME}"
    mv "${DEFAULT_ENERGYPLUS_DIR}" "${DEFAULT_ENERGYPLUS_DIR}/../bkup"
    mkdir "${DEFAULT_ENERGYPLUS_DIR:?}"
    mkdir "${DEFAULT_ENERGYPLUS_DIR:?}/bin"
    echo -e "y\r" | "./${ENERGYPLUS_DOWNLOAD_FILENAME}"
    rm -rf "${DEFAULT_ENERGYPLUS_DIR:?}/bin"
    mv "${DEFAULT_ENERGYPLUS_DIR}" "$( dirname ${DEFAULT_ENERGYPLUS_DIR})/bkup/EnergyPlus-${_ENERGYPLUS_INSTALL_VERSION}"
    mv "$( dirname ${DEFAULT_ENERGYPLUS_DIR})/bkup" "${DEFAULT_ENERGYPLUS_DIR}"
  elif [[ "${_ENERGYPLUS_INSTALL_VERSION}" == "9-4-0" ]]; then
    local ENERGYPLUS_DOWNLOAD_FILENAME="EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-Ubuntu20.04-x86_64.sh"
    local ENERGYPLUS_DOWNLOAD_URL="${ENERGYPLUS_DOWNLOAD_BASE_URL}/${ENERGYPLUS_DOWNLOAD_FILENAME}"
    curl -SLO "${ENERGYPLUS_DOWNLOAD_URL}"
    chmod +x "${ENERGYPLUS_DOWNLOAD_FILENAME}"
    echo -e "y\r" | "./${ENERGYPLUS_DOWNLOAD_FILENAME}"
  else
    local ENERGYPLUS_DOWNLOAD_FILENAME="EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-x86_64.sh"
    local ENERGYPLUS_DOWNLOAD_URL="${ENERGYPLUS_DOWNLOAD_BASE_URL}/${ENERGYPLUS_DOWNLOAD_FILENAME}"
    curl -SLO "${ENERGYPLUS_DOWNLOAD_URL}"
    chmod +x "${ENERGYPLUS_DOWNLOAD_FILENAME}"
    echo -e "y\r" | "./${ENERGYPLUS_DOWNLOAD_FILENAME}"
  fi
  # remove all default symlinks
  find -L "${DEFAULT_ENERGYPLUS_DIR:?}/bin" -type l -delete
  # move to desired install directory
  mkdir -p "${_ENERGYPLUS_INSTALL_DIR}"
  mv "${DEFAULT_ENERGYPLUS_DIR}/EnergyPlus-${_ENERGYPLUS_INSTALL_VERSION}" "${_ENERGYPLUS_INSTALL_DIR}/EnergyPlus-${_ENERGYPLUS_INSTALL_VERSION}"
  rm "${ENERGYPLUS_DOWNLOAD_FILENAME:?}"
}

_ENERGYPLUS_INSTALL_DIR="${1}"

# versions and SHA numbers can be found at: https://github.com/NREL/EnergyPlus/releases
# example: https://github.com/NREL/docker-energyplus/blob/develop/Dockerfile
# comment/uncomment each version as desired, they all work entirely independently
# install_ep "8-9-0" "40101eaafd" "${_ENERGYPLUS_INSTALL_DIR}"
# install_ep "9-0-1" "bb7ca4f0da" "${_ENERGYPLUS_INSTALL_DIR}"
# install_ep "9-1-0" "08d2e308bb" "${_ENERGYPLUS_INSTALL_DIR}"
# install_ep "9-2-0" "921312fa1d" "${_ENERGYPLUS_INSTALL_DIR}"
# install_ep "9-3-0" "baff08990c" "${_ENERGYPLUS_INSTALL_DIR}"
install_ep "9-4-0" "998c4b761e" "${_ENERGYPLUS_INSTALL_DIR}"

exit 0
