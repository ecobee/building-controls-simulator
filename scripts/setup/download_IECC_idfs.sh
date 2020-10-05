#!/bin/bash

cat << EndOfMessage
================================================================================
EnergyPlus Version Manager: 
Downloads IECC 2018 building models for all climate zones into directories from:
https://www.energycodes.gov/development/residential/iecc_models

If the links are broken update them in this script.
================================================================================
EndOfMessage

set -eu -o pipefail
# -e exit on first error
# -u exit when an undefined variable such as $FOO is accessed
# -o pipefail exit when | any |cmd | in | a | pipe has exitcode != 0
# -x print all commands (debug only)

IECC_DIR="IECC_2018"

if [ -d "${IDF_DIR}" ]; then
    mkdir -p "${IDF_DIR}/${IECC_DIR}"  # make dir if doesn't exist
    cd "${IDF_DIR}/${IECC_DIR}"
    for cz in "1A" "2A" "2B" "3A" "3B" "3C" "4A" "4B" "4C" "5A" "5B" "6A" "7" "8"; do
        mkdir "cz_${cz}"
        wget "https://www.energycodes.gov/sites/default/files/documents/EnergyPlus_${cz}_2018_IECC.zip"
        unzip -d "cz_${cz}" "EnergyPlus_${cz}_2018_IECC.zip"
        rm cz_${cz}/*.htm
        rm "EnergyPlus_${cz}_2018_IECC.zip"
    done
    cd -
else
    echo "IDF_DIR=${IDF_DIR} does not exists. Run epvm.sh to set EnergyPlus environment."
fi

# reset shell options so that sourcing script in current shell doesn't leave options on
set +eu +o pipefail
