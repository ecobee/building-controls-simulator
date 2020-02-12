#! /usr/bin/env bash

# bash script to install EnergyPlus releases from:
# https://github.com/NREL/docker-energyplus/blob/develop/Dockerfile

set -u -o pipefail

function install_ep () {
  local _ENERGYPLUS_INSTALL_VERSION="${1}"
  local ENERGYPLUS_SHA="${2}"
  local _ENERGYPLUS_INSTALL_DIR="${3}"
  local ENERGYPLUS_VERSION=$( echo "${_ENERGYPLUS_INSTALL_VERSION}" | tr "-" ".")
  local ENERGYPLUS_TAG="v${ENERGYPLUS_VERSION}"
  local ENERGYPLUS_DOWNLOAD_BASE_URL="https://github.com/NREL/EnergyPlus/releases/download/${ENERGYPLUS_TAG}"
  local ENERGYPLUS_DOWNLOAD_FILENAME="EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-x86_64.sh"
  local ENERGYPLUS_DOWNLOAD_URL="${ENERGYPLUS_DOWNLOAD_BASE_URL}/${ENERGYPLUS_DOWNLOAD_FILENAME}"

  cd "${EXT_DIR}"
  curl -SLO "${ENERGYPLUS_DOWNLOAD_URL}"
  chmod +x "${ENERGYPLUS_DOWNLOAD_FILENAME}"
  # handle the bad install script, manually enter the install dir
  if [[ "${_ENERGYPLUS_INSTALL_VERSION}" == "9-1-0" ]]; then
    mv "${_ENERGYPLUS_INSTALL_DIR}" "${_ENERGYPLUS_INSTALL_DIR}/../bkup"
    mkdir "${_ENERGYPLUS_INSTALL_DIR}"
    mkdir "${_ENERGYPLUS_INSTALL_DIR}/bin"
    echo -e "y\r" | ./${ENERGYPLUS_DOWNLOAD_FILENAME}
    rm- "${_ENERGYPLUS_INSTALL_DIR}/bin"
    mv "${_ENERGYPLUS_INSTALL_DIR}" "$( dirname ${_ENERGYPLUS_INSTALL_DIR})/bkup/EnergyPlus-${_ENERGYPLUS_INSTALL_VERSION}"
    mv "$( dirname ${_ENERGYPLUS_INSTALL_DIR})/bkup" "${_ENERGYPLUS_INSTALL_DIR}"
  else
    echo -e "y\r" | ./${ENERGYPLUS_DOWNLOAD_FILENAME}
  fi
  find -L "${_ENERGYPLUS_INSTALL_DIR}/bin" -type l -delete
  rm "${ENERGYPLUS_DOWNLOAD_FILENAME}"
  cd -
}

install_ep "8-9-0" "40101eaafd" "${ENERGYPLUS_INSTALL_DIR}"
install_ep "9-0-1" "bb7ca4f0da" "${ENERGYPLUS_INSTALL_DIR}"
install_ep "9-1-0" "08d2e308bb" "${ENERGYPLUS_INSTALL_DIR}"
install_ep "9-2-0" "921312fa1d" "${ENERGYPLUS_INSTALL_DIR}"
