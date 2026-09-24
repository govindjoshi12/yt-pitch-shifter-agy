#!/usr/bin/env bash
set -e

# YouTube to MP3 Pitch Shifter - Startup Script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"
fi

echo "=========================================================="
echo " Starting YouTube to MP3 Pitch Shifter"
echo " Web UI:  http://localhost:8000"
echo " API doc: http://localhost:8000/docs"
echo "=========================================================="

cd "$ROOT_DIR/backend"
exec "$VENV_DIR/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
