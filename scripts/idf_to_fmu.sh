#!/bin/bash

set -u -o pipefail

unset INPUT_IDF
unset OUTPUT_IDF
unset PREP_ARGS
unset TIMESTEPS

# set defaults
WEATHER_PATH="${PACKAGE_DIR}/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
TIMESTEPS="60"

# TODO: add check for repo directory tree

# parse optional arguments
POSITIONAL=()
OPTIONAL_ARGS=" "
while [[ "$#" -gt "0" ]]; do
  key="$1"
  case $key in
  -i|--input)
      INPUT_IDF="$2"
      OUTPUT_IDF="${INPUT_IDF%.*}_preped.idf"
      ;;
  -w|--weather)
      WEATHER_PATH="$2"
      ;;
  -o|--output)
      OUTPUT_IDF="$2"
      ;;
  -t|--timesteps)
      TIMESTEPS="$2"
      ;;
  esac
  shift # past argument
  shift # past value
done

set -- "${POSITIONAL[@]}" # restore positional parameters

# run preprocessor
python ${SRC_DIR}/control_preprocessor.py \
-i "$INPUT_IDF" \
-o "$OUTPUT_IDF" \
-t "$TIMESTEPS"

# run FMU compiler and check FMU compliance
set -x
. ${BASH_DIR}/compile_fmu.sh -i "$OUTPUT_IDF" -w "$WEATHER_PATH" -t "$TIMESTEPS"
set +x
