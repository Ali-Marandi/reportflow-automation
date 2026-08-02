#!/usr/bin/env python3
"""
ReportFlow Windows Build Script
================================
Automates the full Windows packaging pipeline:

1. Validates the environment (Python version, PyInstaller, required packages).
2. Runs the test suite — aborts if any test fails.
3. Builds a single-file ``ReportFlow.exe`` with PyInstaller.
4. Optionally generates a WiX-based MSI installer.
5. Prints a summary with file sizes and SHA-256 hashes.

Usage
-----
    python tools/build_windows.py [--skip-tests] [--msi] [--output-dir dist]

Requirements
------------
* Python 3.10+
* PyInstaller >= 6.0   (pip install pyinstaller)
* WiX Toolset v3 in PATH (optional, only needed for --msi)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.resolve()
SPEC_FILE = REPO_ROOT / "reportflow.spec"
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
EXE_NAME = "ReportFlow.exe"
MIN_PYTHON = (3, 10)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner(msg: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {msg}")
    print("=" * width)


def _run(cmd: list[str], cwd: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# Build steps
# ---------------------------------------------------------------------------

def check_environment() -> None:
    _banner("Checking build environment")

    # Python version
    if sys.version_info < MIN_PYTHON:
        print(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
              f"got {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"  Python: {sys.version}")

    # PyInstaller
    try:
        import PyInstaller  # noqa: F401
        import PyInstaller.__main__
        print(f"  PyInstaller: OK")
    except ImportError:
        print("ERROR: PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)

    # Required packages
    required = ["reportflow", "apscheduler", "sqlalchemy", "jinja2", "pandas", "click", "pydantic"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"ERROR: Missing packages: {', '.join(missing)}")
        print("Run: pip install -e .")
        sys.exit(1)
    print(f"  All required packages: OK")

    # Spec file
    if not SPEC_FILE.exists():
        print(f"ERROR: Spec file not found: {SPEC_FILE}")
        sys.exit(1)
    print(f"  Spec file: {SPEC_FILE}")


def run_tests() -> None:
    _banner("Running test suite")
    result = _run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        check=False,
    )
    if result.returncode != 0:
        print("\nERROR: Tests failed. Aborting build.")
        sys.exit(result.returncode)
    print("\n  All tests passed.")


def build_exe(output_dir: Path) -> Path:
    _banner("Building ReportFlow.exe with PyInstaller")

    # Clean previous build artefacts
    for d in (BUILD_DIR, output_dir):
        if d.exists():
            print(f"  Cleaning: {d}")
            shutil.rmtree(d)

    _run([
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
        f"--distpath={output_dir}",
        f"--workpath={BUILD_DIR}",
    ])

    exe_path = output_dir / EXE_NAME
    if not exe_path.exists():
        print(f"ERROR: Expected executable not found at {exe_path}")
        sys.exit(1)

    return exe_path


def generate_msi(exe_path: Path) -> None:
    """Generate a WiX-based MSI installer (requires WiX Toolset v3 in PATH)."""
    _banner("Generating MSI installer (WiX)")

    wix_script = REPO_ROOT / "tools" / "create_msi_installer.py"
    if not wix_script.exists():
        print(f"WARNING: WiX helper script not found: {wix_script}")
        return

    _run([sys.executable, str(wix_script), str(exe_path)], check=False)


def print_summary(exe_path: Path) -> None:
    _banner("Build Summary")
    print(f"  Executable : {exe_path}")
    print(f"  Size       : {_human_size(exe_path)}")
    print(f"  SHA-256    : {_sha256(exe_path)}")
    print()
    print("  To run on Windows:")
    print(f"    .\\{EXE_NAME} run config.json -o output\\")
    print(f"    .\\{EXE_NAME} schedule config.json --cron \"0 8 * * 1-5\" -o output\\")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build ReportFlow.exe for Windows distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip the test suite")
    parser.add_argument("--msi", action="store_true", help="Also generate an MSI installer")
    parser.add_argument(
        "--output-dir",
        default=str(DIST_DIR),
        help=f"Output directory for the executable (default: {DIST_DIR})",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()

    check_environment()

    if not args.skip_tests:
        run_tests()

    exe_path = build_exe(output_dir)

    if args.msi:
        generate_msi(exe_path)

    print_summary(exe_path)


if __name__ == "__main__":
    main()
