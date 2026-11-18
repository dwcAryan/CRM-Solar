#!/usr/bin/env python3
"""
Solar CRM - Database Restore Utility
Restores a chosen PostgreSQL backup from the backups/ directory after user confirmation.
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
    """Find pg_restore or psql on PATH or standard install directories."""
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
    print(" Solar CRM - Database Restore")
    print("=" * 65)

    if not BACKUPS_DIR.exists():
        print("\n[ERROR] No backups directory found at:", BACKUPS_DIR)
        sys.exit(1)

    backup_files = sorted(
        list(BACKUPS_DIR.glob("*.dump")) + list(BACKUPS_DIR.glob("*.sql")),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    if not backup_files:
        print("\n[ERROR] No backup files (.dump or .sql) found in:", BACKUPS_DIR)
        sys.exit(1)

    chosen_file = None
    if len(sys.argv) > 1 and sys.argv[1] != "-y":
        arg_path = Path(sys.argv[1])
        if arg_path.exists():
            chosen_file = arg_path
        else:
            cand = BACKUPS_DIR / sys.argv[1]
            if cand.exists():
                chosen_file = cand

    if not chosen_file:
        print("\nAvailable database backups:")
        for idx, f in enumerate(backup_files, 1):
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  [{idx}] {f.name:<40} ({size_mb:.2f} MB - {mtime})")

        while True:
            sel = input(f"\nSelect backup file to restore [1-{len(backup_files)}] (or 'q' to quit): ").strip()
            if sel.lower() in ('q', 'quit', 'exit'):
                print("Restore cancelled.")
                sys.exit(0)
            if sel.isdigit() and 1 <= int(sel) <= len(backup_files):
                chosen_file = backup_files[int(sel) - 1]
                break
            print(f"Invalid selection. Enter a number between 1 and {len(backup_files)}.")

    cfg = parse_db_env()

    # Safety Confirmation
    auto_yes = "-y" in sys.argv
    if not auto_yes:
        print("\n" + "!" * 65)
        print(" WARNING: RESTORING WILL OVERWRITE CURRENT DATABASE DATA!")
        print(f" Target Database: '{cfg['DB_NAME']}' on {cfg['DB_HOST']}:{cfg['DB_PORT']}")
        print(f" Source Backup:   {chosen_file.name}")
        print("!" * 65)
        confirm = input("\nAre you completely sure you want to proceed? Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("Restore cancelled by user.")
            sys.exit(0)

    env = os.environ.copy()
    if cfg["DB_PASSWORD"]:
        env["PGPASSWORD"] = cfg["DB_PASSWORD"]

    if chosen_file.suffix == ".dump":
        pg_restore = find_pg_tool("pg_restore")
        if not pg_restore:
            print("\n[ERROR] 'pg_restore' utility could not be found.")
            sys.exit(1)
        print(f"\nUsing pg_restore: {pg_restore}")
        cmd = [
            pg_restore,
            "-h", cfg["DB_HOST"],
            "-p", cfg["DB_PORT"],
            "-U", cfg["DB_USER"],
            "--clean",
            "--if-exists",
            "-d", cfg["DB_NAME"],
            str(chosen_file),
        ]
    else:
        psql = find_pg_tool("psql")
        if not psql:
            print("\n[ERROR] 'psql' utility could not be found.")
            sys.exit(1)
        print(f"\nUsing psql: {psql}")
        cmd = [
            psql,
            "-h", cfg["DB_HOST"],
            "-p", cfg["DB_PORT"],
            "-U", cfg["DB_USER"],
            "-d", cfg["DB_NAME"],
            "-f", str(chosen_file),
        ]

    print("Restoring database...")
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    # pg_restore often exits with code 1 for harmless warnings on clean/drop
    if res.returncode not in (0, 1):
        print(f"\n[ERROR] Restore failed with code {res.returncode}:\n{res.stderr}")
        sys.exit(res.returncode)

    print("\n" + "=" * 65)
    print(" DATABASE RESTORE COMPLETED SUCCESSFULLY")
    print("=" * 65)
    print(f"  Restored from: {chosen_file}")
    print(f"  Target DB:     {cfg['DB_NAME']}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
