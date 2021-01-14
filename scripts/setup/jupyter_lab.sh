#!/bin/bash

set -eu -o pipefail

TIMESTAMP=$(date +"%Y_%m_%dT%H_%M_%S")
FNAME="jupyter_lab_logs_${TIMESTAMP}"

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

if [ ! -d "${JUPYTER_LOG_DIR}" ]; then mkdir "${JUPYTER_LOG_DIR}"; fi
echo "jupyter-lab accessable at: http://localhost:8888/lab"
echo "jupyter-lab logs are being stored in: ${JUPYTER_LOG_DIR}/${FNAME}"

. "${LIB_DIR}/${VENV_NAME}/bin/activate"
jupyter-lab --ip="0.0.0.0" --no-browser > "${JUPYTER_LOG_DIR}/${FNAME}"

echo "$!" > "${JUPYTER_LOG_DIR}/JUPYTER_SERVER_PID.txt"

set +eu +o pipefail
