#!/usr/bin/env python3
"""
Solar CRM - Database Backup Utility
Creates a timestamped PostgreSQL backup in the git-ignored backups/ directory.
"""

import datetime
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
BACKUPS_DIR = ROOT_DIR / "backups"


def parse_db_env():
    env_file = BACKEND_DIR / ".env"
    config = {
        "DB_NAME": "solar_crm",
        "DB_USER": "solar_user",
        "DB_PASSWORD": "",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
    }
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k in config:
                        config[k] = v
    return config


def find_pg_tool(tool_name):
    """Find pg_dump or pg_restore on PATH or standard install directories."""
    tool = shutil.which(tool_name)
    if tool:
        return tool

    if sys.platform == "win32":
        patterns = [
            f"C:\\Program Files\\PostgreSQL\\*\\bin\\{tool_name}.exe",
            f"C:\\Program Files (x86)\\PostgreSQL\\*\\bin\\{tool_name}.exe",
            f"C:\\PostgreSQL\\*\\bin\\{tool_name}.exe",
        ]
        candidates = []
        for pat in patterns:
            candidates.extend(glob.glob(pat))
        if candidates:
            # Sort by version number descending
            candidates.sort(reverse=True)
            return candidates[0]
    else:
        candidates = [
            f"/usr/bin/{tool_name}",
            f"/usr/local/bin/{tool_name}",
            f"/opt/homebrew/bin/{tool_name}",
        ]
        candidates.extend(glob.glob(f"/usr/lib/postgresql/*/bin/{tool_name}"))
        candidates.extend(glob.glob(f"/opt/homebrew/opt/postgresql*/bin/{tool_name}"))
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c

    return None


def main():
    print("=" * 65)
    print(" Solar CRM - Database Backup")
    print("=" * 65)

    pg_dump = find_pg_tool("pg_dump")
    if not pg_dump:
        print("\n[ERROR] 'pg_dump' utility could not be found.")
        print("Please ensure PostgreSQL client tools are installed and on your PATH.")
        if sys.platform == "win32":
            print("Expected location: C:\\Program Files\\PostgreSQL\\<version>\\bin\\pg_dump.exe")
        sys.exit(1)

    print(f"Using pg_dump: {pg_dump}")

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUPS_DIR / f"solar_crm_backup_{timestamp}.dump"

    cfg = parse_db_env()
    print(f"Connecting to database: '{cfg['DB_NAME']}' on {cfg['DB_HOST']}:{cfg['DB_PORT']} as '{cfg['DB_USER']}'...")

    env = os.environ.copy()
    if cfg["DB_PASSWORD"]:
        env["PGPASSWORD"] = cfg["DB_PASSWORD"]

    cmd = [
        pg_dump,
        "-h", cfg["DB_HOST"],
        "-p", cfg["DB_PORT"],
        "-U", cfg["DB_USER"],
        "-F", "c",          # Custom binary compressed format
        "-b",               # Include large objects / blobs
        "-f", str(backup_file),
        cfg["DB_NAME"],
    ]

    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"\n[ERROR] Backup failed (code {res.returncode}):\n{res.stderr}")
            sys.exit(res.returncode)

        size_bytes = backup_file.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        print("\n" + "=" * 65)
        print(" DATABASE BACKUP COMPLETED SUCCESSFULLY")
        print("=" * 65)
        print(f"  Backup File: {backup_file}")
        print(f"  File Size:   {size_mb:.2f} MB ({size_bytes:,} bytes)")
        print(f"  Timestamp:   {timestamp}")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to execute backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
