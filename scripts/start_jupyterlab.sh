#!/bin/bash

TIMESTAMP=$(date +"%Y_%m_%dT%H_%M_%S")
FNAME="jupyter_lab_output"
LOG_DIR="${HOME}/jupyter_lab_logs"
if [ ! -d "${LOG_DIR}" ]; then mkdir "${LOG_DIR}"; fi
jupyter-lab --allow-root --ip=0.0.0.0 &> "${LOG_DIR}/${FNAME}_${TIMESTAMP}" &
