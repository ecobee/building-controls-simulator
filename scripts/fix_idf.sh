#!/usr/bin/env bash

#!/bin/bash

unset INPUT_IDF

# set defaults
SRC_PATH="$(dirname ${BASH_SOURCE[0]})"
EPLUS_PATH=$(dirname $(which energyplus))
ORIGIN_PATH=$(pwd)
# parse optional arguments
POSITIONAL=()
OPTIONAL_ARGS=" "
while [[ "$#" -gt "0" ]]; do
    key="$1"
    case $key in
    -i|--input)
        INPUT_IDF="$2"
        OUTPUT_IDF="${INPUT_IDF%.*}_expanded.idf"
        ;;
    -o|--output)
        OUTPUT_IDF="$2"
        ;;
    esac
    shift # past argument
    shift # past value
done
set -- "${POSITIONAL[@]}" # restore positional parameters

# ExpandObjects

cp $INPUT_IDF "${EPLUS_PATH}/in.idf"
cd $EPLUS_PATH
ExpandObjects
echo "EXPANDED"
cp "expanded.idf" "${ORIGIN_PATH}/${OUTPUT_IDF}"
cd $ORIGIN_PATH

OUTPUT_IDF="${INPUT_IDF%.*}_fixed.idf"

echo "Running: python ${SRC_PATH}/idf_preprocessor.py \
-i $INPUT_IDF \
-o $OUTPUT_IDF"
python ${SRC_PATH}/idf_preprocessor.py \
-i "$INPUT_IDF" \
-o "$OUTPUT_IDF"
