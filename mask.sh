#!/usr/bin/env bash
# Mask for Mac and Linux.
#   ./mask          opens Mask in your browser (the installer adds this shortcut to mask.sh)
#   ./mask help     see all commands
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$KIT/envs/mask/bin/python"
if [ ! -x "$PY" ]; then
  echo "Mask isn't installed yet. In this folder, run:  bash install.sh"
  exit 1
fi
unset PYTHONHOME PYTHONPATH
export PYTHONUTF8=1
exec "$PY" "$KIT/app/mask.py" "$@"
