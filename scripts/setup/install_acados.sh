#!/bin/bash
# this script installs:
# acados

[[ ! -z "${ACADOS_DIR}" ]] && echo "ACADOS_DIR=${ACADOS_DIR}" || echo "ACADOS_DIR is empty."

# install acados
# see https://github.com/acados/acados/blob/master/README.md#installation
git clone https://github.com/acados/acados.git "${ACADOS_DIR}" && cd "${ACADOS_DIR}" || exit
git submodule update --recursive --init

# Set the BLASFEO_TARGET in <acados_root>/CMakeLists.txt. 
# aupported targets: https://github.com/giaf/blasfeo/blob/master/README.md
# the default is X64_AUTOMATIC, if you want something else set it in the 

mkdir -p "${ACADOS_DIR}/build" && cd "${ACADOS_DIR}/build" || exit
cmake -DACADOS_WITH_QPOASES=ON "${ACADOS_DIR}"
# add more optional arguments e.g. -DACADOS_WITH_OSQP=OFF/ON -DACADOS_INSTALL_DIR=<path_to_acados_installation_folder> above
make install -j4

# see https://github.com/acados/acados/tree/master/interfaces/acados_template
cd "${ACADOS_DIR}"
pip install -e "${ACADOS_DIR}/interfaces/acados_template"
