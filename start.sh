#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    python3 run.py "$@"
elif command -v python >/dev/null 2>&1; then
    python run.py "$@"
else
    echo "ERROR: Python is not installed or not on PATH."
    exit 1
fi
