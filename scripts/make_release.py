#!/usr/bin/env python3
"""
scripts/make_release.py
Builds the final production release package dist/solar-crm-v1.0.zip from a strict allowlist.
Verifies that no secrets, demo credentials, test evidence, manual assets, venvs,
node_modules, or development caches are included.
Generates SHA-256 checksum file.
"""

import hashlib
import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist"
RELEASE_ZIP = DIST_DIR / "solar-crm-v1.0.zip"
CHECKSUM_FILE = DIST_DIR / "solar-crm-v1.0.zip.sha256"

# Forbidden patterns that must NEVER appear in the production release zip
FORBIDDEN_PATTERNS = [
    "demo_accounts",
    "manual_assets",
    "uat_evidence",
    "old_tour_and_help_content",
    ".env", # except .env.example
    "venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    ".sqlite3",
    ".dump",
    ".bak",
    "playwright/.auth",
    "playwright-report",
    "test-results",
    "dist/",
    ".log",
]

def is_forbidden(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").lower()
    if normalized.endswith(".env.example"):
        return False
    for pat in FORBIDDEN_PATTERNS:
        if pat in normalized:
            return True
    return False

def build_release_zip():
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if RELEASE_ZIP.exists():
        RELEASE_ZIP.unlink()
    if CHECKSUM_FILE.exists():
        CHECKSUM_FILE.unlink()

    print(f"Building production release package: {RELEASE_ZIP.name}...")

    # Exact files and directories to include
    included_files = []

    # 1. Root files
    root_allowlist = [
        "README.md",
        "HOW_TO_RUN.md",
        "TECH_STACK.md",
        "ARCHITECTURE.md",
        "SECURITY_REPORT.md",
        "CHANGELOG.md",
        "run.py",
        ".env.example",
    ]
    for rf in root_allowlist:
        p = BASE_DIR / rf
        if p.exists():
            included_files.append((p, rf))

    # 2. Docs allowlist
    docs_allowlist = [
        "docs/ARCHITECTURE.md",
        "docs/COMPLIANCE_NOTES.md",
        "docs/ROLES_AND_PERMISSIONS.md",
        "docs/GO_LIVE_CHECKLIST.md",
        "docs/TRANSLATION_GUIDE.md",
        "docs/REGRESSION_MATRIX.md",
        "docs/Solar_CRM_User_Manual_v1.0.pdf",
        "docs/Solar_CRM_User_Manual_v1.0_hi.pdf",
    ]
    for df in docs_allowlist:
        p = BASE_DIR / df
        if p.exists():
            included_files.append((p, df))

    # 3. Backend sources
    backend_dir = BASE_DIR / "backend"
    for p in backend_dir.rglob("*"):
        if p.is_file():
            rel = p.relative_to(BASE_DIR).as_posix()
            if not is_forbidden(rel):
                # Don't include sqlite databases, test sqlite files, or auth tokens
                if not rel.endswith((".pyc", ".pyo", ".log", ".dump")):
                    included_files.append((p, rel))

    # 4. Frontend sources
    frontend_dir = BASE_DIR / "frontend"
    for p in frontend_dir.rglob("*"):
        if p.is_file():
            rel = p.relative_to(BASE_DIR).as_posix()
            if not is_forbidden(rel):
                # Exclude dist and auth directories
                if not rel.startswith("frontend/dist") and not rel.startswith("frontend/dev-dist"):
                    included_files.append((p, rel))

    # 5. Locales & scripts
    for folder in ["locales", "scripts"]:
        f_dir = BASE_DIR / folder
        if f_dir.exists():
            for p in f_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(BASE_DIR).as_posix()
                    if not is_forbidden(rel):
                        included_files.append((p, rel))

    # Package into ZIP
    total_added = 0
    with zipfile.ZipFile(RELEASE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath, arcname in sorted(included_files, key=lambda x: x[1]):
            # Secondary assertion check
            if is_forbidden(arcname):
                print(f"CRITICAL: Attempted to package forbidden file: {arcname}")
                sys.exit(1)
            zf.write(fpath, arcname=arcname)
            total_added += 1

    # Verify contents of created zip
    with zipfile.ZipFile(RELEASE_ZIP, "r") as zf:
        namelist = zf.namelist()
        for name in namelist:
            if is_forbidden(name):
                raise ValueError(f"Security Violation: Release zip contains forbidden file {name}!")

    # Calculate SHA256
    hasher = hashlib.sha256()
    with open(RELEASE_ZIP, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_hash = hasher.hexdigest()

    CHECKSUM_FILE.write_text(f"{sha256_hash}  {RELEASE_ZIP.name}\n", encoding="utf-8")

    zip_size_mb = RELEASE_ZIP.stat().st_size / (1024 * 1024)
    print("=" * 60)
    print("Solar CRM Release Package Created Successfully!")
    print(f"- Archive:  {RELEASE_ZIP}")
    print(f"- Size:     {zip_size_mb:.2f} MB")
    print(f"- Files:    {total_added} files packaged")
    print(f"- SHA256:   {sha256_hash}")
    print(f"- Checksum: {CHECKSUM_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    build_release_zip()
