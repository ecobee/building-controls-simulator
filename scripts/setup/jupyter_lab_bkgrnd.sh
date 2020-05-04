#!/bin/bash
TIMESTAMP=$(date +"%Y_%m_%dT%H_%M_%S")
FNAME="jupyter_lab_logs_${TIMESTAMP}"

if [ ! -d "${JUPYTER_LOG_DIR}" ]; then mkdir "${JUPYTER_LOG_DIR}"; fi
nohup jupyter-lab --ip="0.0.0.0" --no-browser > "${JUPYTER_LOG_DIR}/${FNAME}" &
echo "$!" > "${JUPYTER_LOG_DIR}/JUPYTER_SERVER_PID.txt"
cat << EndOfMessage
================================================================================
jupyter-lab server running in background at PID=$(cat ${JUPYTER_LOG_DIR}/JUPYTER_SERVER_PID.txt)
accessable at: http://localhost:8888/lab
jupyter-lab logs are being stored in: ${JUPYTER_LOG_DIR}/${FNAME}
================================================================================
EndOfMessage
