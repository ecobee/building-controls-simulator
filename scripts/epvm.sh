#! /usr/bin/env bash

function printUsage(){
  cat << EndOfMessage
================================================================================
EnergyPlus Version Manager: 
A bash CLI script to toggle between EnergyPlus versions.

usage: . epvm.sh <ENERGYPLUS-VERSION-NUMBER>

Supported versions: {8-9-0, 9-0-1, 9-1-0, 9-2-0, 9-3-0}

for example: . epvm.sh 8-9-0
================================================================================
EndOfMessage
}

TO_SET_VERSION="${1}"

if [[ -z "${TO_SET_VERSION}" ]]; then
  printUsage
elif [[ "${TO_SET_VERSION}" == "-h" ]]; then
  printUsage
elif [[ "${TO_SET_VERSION}" =~ ^("8-9-0"|"9-0-1"|"9-1-0"|"9-2-0"|"9-3-0")$ ]]; then
  
  # set -u
  _NEW_EPLUS_NAME="EnergyPlus-${TO_SET_VERSION}"
  _EPLUS_DIR="${ENERGYPLUS_INSTALL_DIR}/${_NEW_EPLUS_NAME}"
  # set +u

  if [[ -z "${EPLUS_DIR+x}" && -z "${ENERGYPLUS_INSTALL_VERSION+x}" ]]; then
    # initialize
    export EPLUS_DIR="${_EPLUS_DIR}"
    export PATH="${PATH}:${EPLUS_DIR}"
  else
    # swap versions
    _CUR_EPLUS_NAME="EnergyPlus-${ENERGYPLUS_INSTALL_VERSION}"
    export EPLUS_DIR="${ENERGYPLUS_INSTALL_DIR}/${_NEW_EPLUS_NAME}"
    export PATH="${PATH//${_CUR_EPLUS_NAME}/${_NEW_EPLUS_NAME}}"
  fi

  # set -u
  if [[ -d "${_EPLUS_DIR}" ]]; then
    export ENERGYPLUS_INSTALL_VERSION="${TO_SET_VERSION}"

    # setup idf dirs
    mkdir -p "${PACKAGE_DIR}/idf"  # make dir if it does not exist
    export IDF_DIR="${PACKAGE_DIR}/idf/v${ENERGYPLUS_INSTALL_VERSION}"
    mkdir -p "${IDF_DIR}"
    export IDF_PREPROCESSED_DIR="${PACKAGE_DIR}/idf/v${ENERGYPLUS_INSTALL_VERSION}/preprocessed"
    mkdir -p "${IDF_PREPROCESSED_DIR}"

    # setup fmu dirs
    mkdir -p "${PACKAGE_DIR}/fmu"
    export FMU_DIR="${PACKAGE_DIR}/fmu/v${ENERGYPLUS_INSTALL_VERSION}"
    mkdir -p "${FMU_DIR}"

    # setup weather dir
    export WEATHER_DIR="${PACKAGE_DIR}/weather"
    mkdir -p "${WEATHER_DIR}"
    
    # handle packaging for 9-0-1 being slightly different
    if [[ "${TO_SET_VERSION}" == "9-0-1" ]]; then
      export EPLUS_IDD="${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V9-0-0-Energy+.idd"
    else
      export EPLUS_IDD="${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V${ENERGYPLUS_INSTALL_VERSION}-Energy+.idd"
    fi

    # EnergyPlus uses symbolic links to define all runtime executables
    # we simply redefine these to hot-swap what version is currently used
    _LINK_DIR="/home/bcs/.local/bin"
    ln -sf "${EPLUS_DIR}/runenergyplus" "${_LINK_DIR}/runenergyplus"
    ln -sf "${EPLUS_DIR}/runepmacro" "${_LINK_DIR}/runepmacro"
    ln -sf "${EPLUS_DIR}/runreadvars" "${_LINK_DIR}/runreadvars"
    ln -sf "${EPLUS_DIR}/energyplus" "${_LINK_DIR}/energyplus"
    ln -sf "${EPLUS_DIR}/PreProcess/FMUParser/parser" "${_LINK_DIR}/parser"
    ln -sf "${EPLUS_DIR}/PreProcess/GrndTempCalc/Basement" "${_LINK_DIR}/Basement"
    ln -sf "${EPLUS_DIR}/PreProcess/GrndTempCalc/BasementGHT.idd" "${_LINK_DIR}/BasementGHT.idd"
    ln -sf "${EPLUS_DIR}/PostProcess/EP-Compare/EP-Compare" "${_LINK_DIR}/EP-Compare"
    ln -sf "${EPLUS_DIR}/EPMacro" "${_LINK_DIR}/EPMacro"
    ln -sf "${EPLUS_DIR}/Energy+.idd" "${_LINK_DIR}/Energy+.idd"
    ln -sf "${EPLUS_DIR}/Energy+.schema.epJSON" "${_LINK_DIR}/Energy+.schema.epJSON"
    ln -sf "${EPLUS_DIR}/ExpandObjects" "${_LINK_DIR}/ExpandObjects"
    ln -sf "${EPLUS_DIR}/PostProcess/HVAC-Diagram" "${_LINK_DIR}/HVAC-Diagram"
    ln -sf "${EPLUS_DIR}/PreProcess/IDFVersionUpdater/IDFVersionUpdater" "${_LINK_DIR}/IDFVersionUpdater"
    ln -sf "${EPLUS_DIR}/PostProcess/ReadVarsESO" "${_LINK_DIR}/ReadVarsESO"
    ln -sf "${EPLUS_DIR}/PreProcess/GrndTempCalc/Slab" "${_LINK_DIR}/Slab"
    ln -sf "${EPLUS_DIR}/PreProcess/GrndTempCalc/SlabGHT.idd" "${_LINK_DIR}/SlabGHT.idd"
    ln -sf "${EPLUS_DIR}/PreProcess/IDFVersionUpdater/Transition-V8-2-0-to-V8-3-0" "${_LINK_DIR}/Transition-V8-2-0-to-V8-3-0"
    ln -sf "${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V8-2-0-Energy+.idd" "${_LINK_DIR}/V8-2-0-Energy+.idd"
    ln -sf "${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V8-3-0-Energy+.idd" "${_LINK_DIR}/V8-3-0-Energy+.idd"
    ln -sf "${EPLUS_DIR}/PostProcess/convertESOMTRpgm/convertESOMTR" "${_LINK_DIR}/convertESOMTR"
    find -L . -type l -delete

    echo "EnergyPlus set to version: ${TO_SET_VERSION}"
  else
    echo "EnergyPlus *not* set to version: ${TO_SET_VERSION}"
    echo "Directory does *not* exist: ${_EPLUS_DIR}"
  fi
else
  echo "EnergyPlus version *not* supported: ${TO_SET_VERSION}"
  echo "EnergyPlus still version: ${ENERGYPLUS_INSTALL_VERSION}"
fi

# reset shell options so that sourcing script in current shell doesn't leave options on
