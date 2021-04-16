#!/bin/bash
# this script installs:
# https://github.com/giaf/hpipm
# https://github.com/giaf/blasfeo

if [ -z "${BLASFEO_MAIN_FOLDER}" ]; then; 
    BLASFEO_MAIN_FOLDER="${EXT_DIR}/blasfeo"
fi

if [ -z "${HPIPM_MAIN_FOLDER}" ]; then; 
    HPIPM_MAIN_FOLDER="${EXT_DIR}/hpipm"
fi

cd "${EXT_DIR}"
git clone https://github.com/giaf/blasfeo.git
cd "${BLASFEO_MAIN_FOLDER}"
# see https://blasfeo.syscop.de/docs/install/
# Makefile.rule has flags
make shared_library -j4 && sudo make install_shared

cd "${EXT_DIR}"
git clone https://github.com/giaf/hpipm.git
cd "${HPIPM_MAIN_FOLDER}"
make shared_library -j4 && sudo make install_shared
cd "${HPIPM_MAIN_FOLDER}/interfaces/python/hpipm_python"
pip install .

# if hpipm folder not specified assume parent of this folder
export HPIPM_MAIN_FOLDER
echo "HPIPM_MAIN_FOLDER=$HPIPM_MAIN_FOLDER"

# if blasfeo folder not specified assume alongside the parent of this folder
export BLASFEO_MAIN_FOLDER
echo "BLASFEO_MAIN_FOLDER=$BLASFEO_MAIN_FOLDER"

# export LD_LIBRARY_PATH
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${HPIPM_MAIN_FOLDER}/lib:${BLASFEO_MAIN_FOLDER}/lib"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
