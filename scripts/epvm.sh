#! /usr/bin/env bash

function printUsage(){
  echo
  echo "EnergyPlus Version Manager"
  echo "=============================================================================="
  echo "A bash CLI script to toggle between EnergyPlus versions."
  echo
  echo " usage:"
  echo " $(basename ${0}) <ENERGYPLUS-VERSION-NUMBER>"
  echo 
  echo " for example:"
  echo " $(basename ${0}) 9-2-0"
  echo
}

TO_SET_VERSION=${1}

if [[ -z "${TO_SET_VERSION}" ]]; then
  printUsage
elif [[ "${TO_SET_VERSION}" == "-h" ]]; then
  printUsage
elif [[ "${TO_SET_VERSION}" =~ ^("8-9-0"|"9-0-1"|"9-1-0"|"9-2-0")$ ]]; then
  
  set -u
  _NEW_EPLUS_NAME="EnergyPlus-${TO_SET_VERSION}"
  _EPLUS_DIR="${ENERGYPLUS_INSTALL_DIR}/${_NEW_EPLUS_NAME}"
  set +u

  if [[ -z "${EPLUS_DIR}" && -z "${ENERGYPLUS_INSTALL_VERSION}" ]]; then
    # initialize
    export EPLUS_DIR="${_EPLUS_DIR}"
    export PATH="${PATH}:${EPLUS_DIR}"
  else
    # swap versions
    _CUR_EPLUS_NAME="EnergyPlus-${ENERGYPLUS_INSTALL_VERSION}"
    export EPLUS_DIR=
    export PATH="${PATH//${_CUR_EPLUS_NAME}/${_NEW_EPLUS_NAME}}"
  fi

  set -u
  if [[ -d "${_EPLUS_DIR}" ]]; then
    export ENERGYPLUS_INSTALL_VERSION="${TO_SET_VERSION}"
    export IDF_DIR="${PACKAGE_DIR}/idf/v${ENERGYPLUS_INSTALL_VERSION}"
    export IDF_PREPROCESSED_DIR="${PACKAGE_DIR}/idf/v${ENERGYPLUS_INSTALL_VERSION}/preprocessed"
    export FMU_DIR="${PACKAGE_DIR}/fmu/v${ENERGYPLUS_INSTALL_VERSION}"
    
    if [[ "${TO_SET_VERSION}" == "9-0-1" ]]; then
      export EPLUS_IDD="${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V9-0-0-Energy+.idd"
    else
      export EPLUS_IDD="${EPLUS_DIR}/PreProcess/IDFVersionUpdater/V${ENERGYPLUS_INSTALL_VERSION}-Energy+.idd"
    fi

    _LINK_DIR="/usr/local/bin"
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
    echo "EnergyPlus not installed version: ${TO_SET_VERSION}"
    echo "Directory does not exist: ${_EPLUS_DIR}"
  fi
else
  echo "EnergyPlus version not supported: ${TO_SET_VERSION}"
  echo "EnergyPlus still version: ${ENERGYPLUS_INSTALL_VERSION}"
fi
