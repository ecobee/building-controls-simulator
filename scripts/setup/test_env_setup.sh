#!/bin/bash

# this script should be sources into current shell
echo "setting ${PACKAGE_DIR}/.test.env variables in shell"
set -a && . "${PACKAGE_DIR}/.test.env" && set +a
. "${PACKAGE_DIR}/scripts/epvm.sh" "9-4-0"
