#!/usr/bin/env python3
"""
Solar CRM - Unified Runner Script
Runs the entire Solar CRM application (Backend, Frontend, and APScheduler) with one command.
Works cross-platform on Windows, macOS, and Linux.
"""

import argparse
import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DOCS_DIR = ROOT_DIR / "docs"
VENV_DIR = BACKEND_DIR / "venv"
VENV_PYTHON = VENV_DIR / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")

# ANSI color codes
CYAN = "\033[36m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Enable VT100 ANSI sequences on Windows console
if sys.platform == "win32":
    os.system("")


def log_step(title):
    print(f"\n{BOLD}{CYAN}==>{RESET} {BOLD}{title}{RESET}")


def log_info(msg):
    print(f"    {GREEN}* {RESET}{msg}")


def log_warn(msg):
    print(f"    {YELLOW}! {RESET}{msg}")


def log_error(msg):
    print(f"    {RED}[ERROR] {RESET}{msg}")


def check_prerequisites():
    """Verify Python, Node, npm and system requirements."""
    log_step("Checking system prerequisites...")

    # Python version check (3.12+)
    if sys.version_info < (3, 12):
        print("\n" + "=" * 68)
        log_error("Python 3.12 or higher is required.")
        print(f"    Current detected version: Python {sys.version.split()[0]}")
        print("    Download and install Python 3.12+ from: https://www.python.org/downloads/")
        print("=" * 68 + "\n")
        sys.exit(1)
    log_info(f"Python: {sys.version.split()[0]} (OK)")

    # Node.js check
    node_bin = shutil.which("node")
    if not node_bin:
        print("\n" + "=" * 68)
        log_error("Node.js was not found on your system PATH.")
        print("    Please install Node.js (v18+ or LTS) from: https://nodejs.org/")
        print("=" * 68 + "\n")
        sys.exit(1)
    try:
        node_v = subprocess.run([node_bin, "-v"], capture_output=True, text=True, check=True).stdout.strip()
        log_info(f"Node.js: {node_v} (OK)")
    except Exception:
        log_info("Node.js: detected (OK)")

    # npm check
    npm_bin = shutil.which("npm.cmd") if sys.platform == "win32" else shutil.which("npm")
    if not npm_bin:
        print("\n" + "=" * 68)
        log_error("npm was not found on your system PATH.")
        print("    Please ensure Node.js and npm are installed: https://nodejs.org/")
        print("=" * 68 + "\n")
        sys.exit(1)
    try:
        npm_v = subprocess.run([npm_bin, "-v"], capture_output=True, text=True, check=True).stdout.strip()
        log_info(f"npm: {npm_v} (OK)")
    except Exception:
        log_info("npm: detected (OK)")

    return npm_bin


def ensure_backend_env():
    """Ensure backend/.env exists, creating it from .env.example if missing."""
    log_step("Checking backend environment configuration...")
    env_file = BACKEND_DIR / ".env"
    example_file = BACKEND_DIR / ".env.example"

    if not env_file.exists():
        if example_file.exists():
            shutil.copyfile(example_file, env_file)
            log_warn("Created backend/.env from backend/.env.example")
            log_warn("Please review database settings (DB_NAME, DB_USER, DB_PASSWORD) in backend/.env if needed.")
        else:
            log_error("Neither backend/.env nor backend/.env.example found!")
            sys.exit(1)
    else:
        log_info("backend/.env is present.")

    # Parse DB settings from backend/.env
    db_config = {"host": "localhost", "port": 5432, "name": "solar_crm"}
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DB_HOST="):
                    db_config["host"] = line.split("=", 1)[1].strip() or "localhost"
                elif line.startswith("DB_PORT="):
                    val = line.split("=", 1)[1].strip()
                    if val.isdigit():
                        db_config["port"] = int(val)
                elif line.startswith("DB_NAME="):
                    db_config["name"] = line.split("=", 1)[1].strip() or "solar_crm"
    except Exception as e:
        log_warn(f"Could not parse DB settings from .env: {e}")

    return db_config


def check_postgres_reachable(db_config):
    """Verify PostgreSQL server socket is reachable."""
    log_step(f"Verifying PostgreSQL database at {db_config['host']}:{db_config['port']}...")
    try:
        with socket.create_connection((db_config["host"], db_config["port"]), timeout=3.0):
            log_info(f"PostgreSQL service is reachable on {db_config['host']}:{db_config['port']}.")
    except OSError:
        print("\n" + "=" * 68)
        log_error(f"Cannot connect to PostgreSQL at {db_config['host']}:{db_config['port']}.")
        print("    Solar CRM requires a running PostgreSQL instance.")
        print("\n    Troubleshooting steps:")
        print("      - Windows: Open Services (services.msc) and start 'postgresql-x64-*'")
        print("                 or in Admin prompt: net start postgresql-x64-16")
        print("      - macOS:   brew services start postgresql")
        print("      - Linux:   sudo systemctl start postgresql")
        print(f"      - Verify host and port in {BACKEND_DIR / '.env'}")
        print("=" * 68 + "\n")
        sys.exit(1)


def compute_file_hash(path):
    """Compute sha256 hash of a file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def setup_backend_venv(skip_install=False):
    """Create backend/venv if missing and install requirements based on hash."""
    log_step("Checking backend Python environment...")

    if not VENV_DIR.exists():
        log_info("Creating virtual environment at backend/venv...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        log_info("Virtual environment created.")

    if not VENV_PYTHON.exists():
        log_error(f"Python executable not found at {VENV_PYTHON}")
        sys.exit(1)

    req_file = BACKEND_DIR / "requirements.txt"
    hash_file = VENV_DIR / ".requirements.hash"
    current_hash = compute_file_hash(req_file)
    stored_hash = hash_file.read_text().strip() if hash_file.exists() else ""

    if not skip_install and (current_hash != stored_hash):
        log_info("Installing/updating Python dependencies (requirements.txt)...")
        # Upgrade pip first
        subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], cwd=str(BACKEND_DIR), check=False)
        res = subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(req_file)], cwd=str(BACKEND_DIR))
        if res.returncode != 0:
            log_error("Python dependencies installation failed.")
            sys.exit(res.returncode)
        hash_file.write_text(current_hash)
        log_info("Python dependencies installed successfully.")
    else:
        log_info("Python requirements up to date (cached).")

    # Verify critical multi-country packages
    test_res = subprocess.run(
        [str(VENV_PYTHON), "-c", "import phonenumbers, tzdata; print('OK')"],
        capture_output=True, text=True
    )
    if test_res.returncode != 0:
        log_error(f"Critical packages (phonenumbers, tzdata) failed to load:\n{test_res.stderr}")
        sys.exit(1)
    log_info("Confirmed phonenumbers and tzdata import correctly.")


def setup_frontend_npm(npm_bin, skip_install=False):
    """Run npm install only when package.json or lock file changed."""
    log_step("Checking frontend dependencies...")
    pkg_file = FRONTEND_DIR / "package.json"
    lock_file = FRONTEND_DIR / "package-lock.json"
    node_modules = FRONTEND_DIR / "node_modules"
    hash_file = FRONTEND_DIR / ".install.hash"

    h = hashlib.sha256()
    if pkg_file.exists():
        h.update(pkg_file.read_bytes())
    if lock_file.exists():
        h.update(lock_file.read_bytes())
    current_hash = h.hexdigest()
    stored_hash = hash_file.read_text().strip() if hash_file.exists() else ""

    if not skip_install and (not node_modules.exists() or current_hash != stored_hash):
        log_info("Installing frontend npm dependencies...")
        res = subprocess.run([npm_bin, "install"], cwd=str(FRONTEND_DIR))
        if res.returncode != 0:
            log_error("npm install failed.")
            sys.exit(res.returncode)
        hash_file.write_text(current_hash)
        log_info("Frontend packages installed successfully.")
    else:
        log_info("Frontend packages up to date (cached).")


def run_database_tasks(reset_demo=False, auto_yes=False):
    """Run migrations, seed_masters, and seed_demo if needed."""
    log_step("Preparing database schema and masters...")

    # Migrations
    res = subprocess.run([str(VENV_PYTHON), "manage.py", "migrate"], cwd=str(BACKEND_DIR))
    if res.returncode != 0:
        log_error("Database migration failed.")
        sys.exit(res.returncode)
    log_info("Database migrations applied.")

    # Idempotent seed_masters
    res = subprocess.run([str(VENV_PYTHON), "manage.py", "seed_masters"], cwd=str(BACKEND_DIR))
    if res.returncode != 0:
        log_error("seed_masters failed.")
        sys.exit(res.returncode)
    log_info("Master data verified and seeded.")

    # Check lead count
    leads_count = 0
    try:
        out = subprocess.run(
            [str(VENV_PYTHON), "manage.py", "shell", "-c", "from leads.models import Lead; print(Lead.objects.count())"],
            cwd=str(BACKEND_DIR), capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines():
            if line.strip().isdigit():
                leads_count = int(line.strip())
                break
    except Exception as e:
        log_warn(f"Could not count leads: {e}")

    if reset_demo:
        confirm = "y" if auto_yes else input("\n[WARNING] --reset-demo requested. This will clear existing leads and regenerate all demo accounts. Proceed? (y/N): ").strip().lower()
        if confirm in ("y", "yes"):
            log_info("Re-seeding demo data with fresh randomized credentials...")
            subprocess.run([str(VENV_PYTHON), "manage.py", "seed_demo", "--reset"], cwd=str(BACKEND_DIR), check=True)
        else:
            log_info("Demo reset skipped.")
    elif leads_count == 0:
        should_seed = auto_yes
        if not should_seed:
            if sys.stdin.isatty():
                prompt = input("\n[DATABASE] Database contains 0 leads. Seed demo accounts and sample leads? (Y/n): ").strip().lower()
                should_seed = prompt in ("", "y", "yes")
            else:
                should_seed = True

        if should_seed:
            log_info("Seeding demo accounts and leads...")
            subprocess.run([str(VENV_PYTHON), "manage.py", "seed_demo"], cwd=str(BACKEND_DIR), check=True)
    else:
        log_info(f"Database currently contains {leads_count} lead(s).")


def kill_proc_tree(proc):
    """Cleanly terminate a process and its child processes."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def pipe_logger(pipe, prefix, color):
    """Read pipe line-by-line and print with colored prefix."""
    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break
            clean = line.rstrip()
            if clean:
                print(f"{color}[{prefix}]{RESET} {clean}", flush=True)
    except (ValueError, OSError):
        pass


def main():
    parser = argparse.ArgumentParser(description="Solar CRM Unified Runner")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically.")
    parser.add_argument("--skip-install", action="store_true", help="Skip checking and installing dependencies.")
    parser.add_argument("--backend-only", action="store_true", help="Start backend server only (no frontend/scheduler).")
    parser.add_argument("--reset-demo", action="store_true", help="Reset and regenerate all demo accounts and sample leads.")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically accept confirmation prompts.")
    args = parser.parse_args()

    npm_bin = check_prerequisites()
    db_config = ensure_backend_env()
    check_postgres_reachable(db_config)
    setup_backend_venv(skip_install=args.skip_install)

    if not args.backend_only:
        setup_frontend_npm(npm_bin, skip_install=args.skip_install)

    run_database_tasks(reset_demo=args.reset_demo, auto_yes=args.yes)

    # Print Access Banner
    demo_doc = DOCS_DIR / "DEMO_ACCOUNTS.md"
    print("\n" + "=" * 70)
    print(f" {BOLD}SOLAR CRM IS STARTING UP{RESET}")
    print("=" * 70)
    if not args.backend_only:
        print(f"  {BOLD}Frontend Web App:{RESET}  http://localhost:5173")
    print(f"  {BOLD}Backend REST API:{RESET}  http://localhost:8000/api/")
    print(f"  {BOLD}Interactive Docs:{RESET}  http://localhost:8000/api/schema/swagger-ui/")
    print(f"  {BOLD}Django Admin:{RESET}      http://localhost:8000/admin/")
    if demo_doc.exists():
        print(f"  {BOLD}Demo Logins:{RESET}       docs/DEMO_ACCOUNTS.md (git-ignored)")
    print("=" * 70)
    print("  Combined live logs streaming below. Press Ctrl+C to shut down cleanly.\n")

    # Start child processes
    processes = []
    threads = []

    # 1. Backend Server
    py_env = os.environ.copy()
    py_env["PYTHONUNBUFFERED"] = "1"
    backend_proc = subprocess.Popen(
        [str(VENV_PYTHON), "manage.py", "runserver", "8000"],
        cwd=str(BACKEND_DIR),
        env=py_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(("BACKEND", backend_proc))
    t_back = threading.Thread(target=pipe_logger, args=(backend_proc.stdout, "BACKEND  ", CYAN), daemon=True)
    t_back.start()
    threads.append(t_back)

    # 2. Frontend & Scheduler (if not backend-only)
    if not args.backend_only:
        # Scheduler
        sched_proc = subprocess.Popen(
            [str(VENV_PYTHON), "manage.py", "run_scheduler"],
            cwd=str(BACKEND_DIR),
            env=py_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(("SCHEDULER", sched_proc))
        t_sched = threading.Thread(target=pipe_logger, args=(sched_proc.stdout, "SCHEDULER", MAGENTA), daemon=True)
        t_sched.start()
        threads.append(t_sched)

        # Frontend Vite
        front_proc = subprocess.Popen(
            [npm_bin, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(("FRONTEND", front_proc))
        t_front = threading.Thread(target=pipe_logger, args=(front_proc.stdout, "FRONTEND ", GREEN), daemon=True)
        t_front.start()
        threads.append(t_front)

        # Open Browser
        if not args.no_browser:
            def open_browser():
                time.sleep(2.5)
                webbrowser.open("http://localhost:5173")
            t_browse = threading.Thread(target=open_browser, daemon=True)
            t_browse.start()

    # Wait for Ctrl+C or process exit
    try:
        while True:
            time.sleep(0.5)
            # Check if any process died unexpectedly
            for name, proc in processes:
                if proc.poll() is not None:
                    log_warn(f"{name} exited unexpectedly with code {proc.returncode}.")
                    raise KeyboardInterrupt
    except (KeyboardInterrupt, SystemExit):
        print(f"\n{BOLD}{YELLOW}[SHUTDOWN]{RESET} Shutting down all Solar CRM services cleanly...")
        for name, proc in processes:
            kill_proc_tree(proc)
        print(f"{BOLD}{GREEN}[SHUTDOWN]{RESET} All services stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
