#!/bin/bash
set -e
VENV_DIR="venv"

# the venv's own python (not "activate", which keeps the folder's old path if the folder is ever moved)
cd "$(dirname "$0")"
pick() { if [ -x "$VENV_DIR/Scripts/python.exe" ]; then PY="$VENV_DIR/Scripts/python.exe"; else PY="$VENV_DIR/bin/python"; fi; }
pick
if [ ! -x "$PY" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    pick
    "$PY" -m pip install -r requirements.txt
fi

echo "Starting AetherCanvas AI on http://127.0.0.1:7870"
"$PY" app.py
