#!/usr/bin/env python3
"""
scripts/capture_manual_screens.py
Automated screenshot harness for the Solar CRM User Manual.
Seeds demo accounts and data, then captures 1440px desktop and 390px mobile screens
in both English and Hindi into docs/manual_assets/.
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def seed_demo_data():
    print("[1/2] Seeding demo database for manual captures...")
    python_bin = BASE_DIR / "backend" / "venv" / "Scripts" / "python.exe"
    if not python_bin.exists():
        python_bin = Path(sys.executable)

    cmd = [str(python_bin), "backend/manage.py", "seed_demo"]
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Warning: seed_demo exited with {res.returncode}: {res.stderr}")
    else:
        print("Demo database seeded successfully.")


def run_capture_worker():
    print("[2/2] Running Playwright capture worker...")
    worker_script = BASE_DIR / "scripts" / "capture_screens_worker.mjs"
    cmd = ["node", str(worker_script)]
    res = subprocess.run(cmd, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"Error: Screenshot capture failed with code {res.returncode}")
        sys.exit(res.returncode)
    print("Screenshot capture completed successfully.")


def main():
    seed_demo_data()
    run_capture_worker()


if __name__ == "__main__":
    main()
