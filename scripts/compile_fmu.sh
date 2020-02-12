#!/bin/bash

set -u -o pipefail

unset INPUT_IDF
unset OUTPUT_FMU
unset PREP_ARGS
unset TIMESTEPS

# set default vars
WEATHER_PATH="${PACKAGE_DIR}/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
EPLUSTOFMU_PATH="${EXT_DIR}/EnergyPlusToFMU/Scripts"
# parse optional arguments
POSITIONAL=()
while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
    -i|--input)
    INPUT_IDF="$2"

    shift # past argument
    shift # past value
    ;;
    -w|--weather)
    WEATHER_PATH="$2"
    shift # past argument
    shift # past value
    ;;
    -o|--output)
    OUTPUT_FMU="$2"
    shift # past argument
    shift # past value
    ;;
    -t|--timesteps)
    TIMESTEPS="$2"
    shift # past argument
    shift # past value
    ;;
  esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

# add output fmu dir
[ -d "${FMU_DIR}" ] || mkdir "${FMU_DIR}"

# add OUTPUT_FMU if not provided
set +u
if [[ -z ${OUTPUT_FMU} ]]; then
  FNAME="${INPUT_IDF%.*}"
  BASENAME=${FNAME##*/}
  OUTPUT_FMU_NAME="${BASENAME//-/_}"
  OUTPUT_FMU_NAME="${OUTPUT_FMU_NAME//./_}.fmu"
  OUTPUT_FMU_PATH="${FMU_DIR}/${OUTPUT_FMU_NAME}"
fi
set -u


# compile EnergyPlus .fmu
echo "Compiling EnergyPlus $INPUT_IDF to $OUTPUT_FMU_PATH"
echo "Input file: ${PACKAGE_DIR}/$INPUT_IDF"
echo "Output file: $OUTPUT_FMU_PATH"
echo "================================================================================"
set -x

python2.7 "${EPLUSTOFMU_PATH}/EnergyPlusToFMU.py" \
  -i "${EPLUS_IDD}" \
  -w "$WEATHER_PATH" \
  "${PACKAGE_DIR}/$INPUT_IDF"

mv "${PACKAGE_DIR}/${OUTPUT_FMU_NAME}" "${OUTPUT_FMU_PATH}"
# check FMI compliance
# -h specifies the step size in seconds, -s is the stop time in seconds. 
# Stop time must be a multiple of 86400. 
# The step size needs to be the same as the .idf file specifies
yes | ${EXT_DIR}/FMUComplianceChecker/fmuCheck.linux64 -h "$TIMESTEPS" \
  -s 172800 "${OUTPUT_FMU_PATH}"

# rm -rf "$(dirname ${BASH_SOURCE[0]})/Output_EPExport_Slave/"
# rm -rf "${PWD}/Output_EPExport_Test\ FMI\ 1.0\ CS/"

set +x

# clean up
echo "cleaning output files and log .txt files:"

