#!/bin/bash
set -eo pipefail

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" >&2
   exit 1
fi

LOG_DIR="/var/log/patch-manager"
LOCK_FILE="/var/run/vm_patch_manager.lock"
VENV_DIR="/opt/patch-manager/venv"
SCRIPT_PATH="/opt/patch-manager/vm_patch_manager.py"
ALERT_EMAIL="ops-alerts@enterprise.com"

mkdir -p "${LOG_DIR}"
exec 9> "${LOCK_FILE}"
if ! flock -n 9; then
    echo "Another instance of vm_patch_manager is already running." >&2
    exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Virtualenv not found at ${VENV_DIR}" >&2
    exit 1
fi

source "${VENV_DIR}/bin/activate"

# Rotate logs older than 30 days
find "${LOG_DIR}" -name 'report-*.json' -type f -mtime +30 -delete
find "${LOG_DIR}" -name 'patch.log*' -type f -mtime +30 -delete

if ! python3 "${SCRIPT_PATH}"; then
    echo "Subject: CRITICAL: VM Patch Manager Failed on $(hostname)" | sendmail -v "${ALERT_EMAIL}"
    exit 1
fi

deactivate
