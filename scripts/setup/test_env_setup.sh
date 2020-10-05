#!/bin/bash

# this script should be sources into current shell
. "${PACKAGE_DIR}/scripts/epvm.sh" "8-9-0"
echo "setting ${PACKAGE_DIR}/.test.env variables in shell"
set -a && . "${PACKAGE_DIR}/.test.env" && set +a
