#!/usr/bin/env bash
# Portable launcher: uses the bundled Python runtime under ./runtime/python
# so this app can be copied to another Mac and run without installing
# Python, pip, or any dependencies system-wide.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/runtime/python/bin/python3.12"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Runtime Python tidak ditemukan di $PYTHON_BIN"
    echo "Pastikan folder 'runtime/' ikut disalin bersama aplikasi ini."
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" -m streamlit run app.py "$@"
