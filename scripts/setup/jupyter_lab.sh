#!/bin/bash

set -eu -o pipefail
source "${PACKAGE_DIR}/.env" 

if [ ! -d "${DOCKER_HOME_DIR}/.jupyter" ]; then mkdir "${DOCKER_HOME_DIR}/.jupyter"; fi
if [ ! -f "${DOCKER_HOME_DIR}/.jupyter/jupyter_notebook_config.py" ]; then
    # this will create jupyter_notebook_config and add a dummy token so it can be accessed without password
    touch "${DOCKER_HOME_DIR}/.jupyter/jupyter_notebook_config.py"
    echo "c.NotebookApp.token = u''" >> "${DOCKER_HOME_DIR}/.jupyter/jupyter_notebook_config.py"
else
    echo "${DOCKER_HOME_DIR}/.jupyter/jupyter_notebook_config.py already exists. Not overriden."
    echo "If jupyter server is inaccessible without password delete this file and re-run."
fi

# set energyplus env variables, this is not built into the container and can
# be modified more readily than .bashrc

. "${PACKAGE_DIR:?}/scripts/epvm.sh" "9-4-0"
echo "jupyter-lab accessable at: http://localhost:8888/lab"

cd "${LIB_DIR}"
. "${LIB_DIR}/${VENV_NAME}/bin/activate"

jupyter-lab --ip="0.0.0.0" --no-browser 

set +eu +o pipefail
