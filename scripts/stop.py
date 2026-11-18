#!/usr/bin/env python3
"""
Solar CRM - Process Stopper
Terminates any running Solar CRM processes (ports 8000 and 5173).
"""

import os
import re
import subprocess
import sys


def stop_windows():
    print("[STOP] Searching for active Solar CRM processes on Windows...")
    ports = [8000, 5173]
    stopped_pids = set()

    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            line = line.strip()
            for port in ports:
                # Match patterns like :8000 or :5173 in LISTENING state
                if f":{port}" in line and "LISTENING" in line:
                    parts = re.split(r'\s+', line)
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 0 and pid not in stopped_pids:
                        print(f"  Stopping process on port {port} (PID: {pid})...")
                        subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True)
                        stopped_pids.add(pid)
    except Exception as e:
        print(f"  Error inspecting ports: {e}")

    # Also terminate any stray run_scheduler or runserver instances
    try:
        wmic_out = subprocess.run(
            ["wmic", "process", "where", "caption='python.exe'", "get", "commandline,processid"],
            capture_output=True, text=True
        ).stdout
        for line in wmic_out.splitlines():
            if "run_scheduler" in line or "runserver" in line:
                parts = re.split(r'\s+', line.strip())
                pid = parts[-1]
                if pid.isdigit() and pid not in stopped_pids:
                    print(f"  Stopping background Django task (PID: {pid})...")
                    subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True)
                    stopped_pids.add(pid)
    except Exception:
        pass

    if stopped_pids:
        print(f"[STOP] Terminated {len(stopped_pids)} process(es).")
    else:
        print("[STOP] No active Solar CRM processes found.")


def stop_unix():
    print("[STOP] Searching for active Solar CRM processes on Unix/macOS...")
    ports = [8000, 5173]
    stopped_pids = set()

    for port in ports:
        try:
            out = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True).stdout
            for pid in out.splitlines():
                pid = pid.strip()
                if pid.isdigit() and pid not in stopped_pids:
                    print(f"  Stopping process on port {port} (PID: {pid})...")
                    subprocess.run(["kill", "-9", pid], check=False)
                    stopped_pids.add(pid)
        except FileNotFoundError:
            try:
                subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
            except Exception:
                pass

    if stopped_pids:
        print(f"[STOP] Terminated {len(stopped_pids)} process(es).")
    else:
        print("[STOP] No active Solar CRM processes found.")


def main():
    if sys.platform == "win32":
        stop_windows()
    else:
        stop_unix()


if __name__ == "__main__":
    main()
