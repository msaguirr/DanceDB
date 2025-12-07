#!/usr/bin/env bash
# Helper to run the Dance Manager GUI using the project's virtualenv.
# This script is deprecated - use run_dance_gui.py or run_copperknob_gui.py instead

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  venv/bin/python -m pip install --upgrade pip
  if [ -f "requirements.txt" ]; then
    venv/bin/python -m pip install -r requirements.txt
  fi
fi

# Run Dance Manager GUI with the venv's python
venv/bin/python run_dance_gui.py
