#! /bin/usr/env bash

# Downloads models for all climate zones into directories from:
# https://www.energycodes.gov/development/residential/iecc_models

set -ux -o pipefail

IECC_DIR="IECC_2018"

if [ ! -d "${IDF_DIR}/${IECC_DIR}" ]; then
    mkdir "${IDF_DIR}/${IECC_DIR}"
    cd "${IDF_DIR}/${IECC_DIR}" || exit
    for cz in "1A" "2A" "2B" "3A" "3B" "3C" "4A" "4B" "4C" "5A" "5B" "6A" "7" "8"; do
        mkdir "cz_${cz}"
        wget "https://www.energycodes.gov/sites/default/files/documents/EnergyPlus_${cz}_2018_IECC.zip"
        unzip -d "cz_${cz}" "EnergyPlus_${cz}_2018_IECC.zip"
        rm cz_${cz}/*.htm
        rm "EnergyPlus_${cz}_2018_IECC.zip"
    done
fi

set +ux