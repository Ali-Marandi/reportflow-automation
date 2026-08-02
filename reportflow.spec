# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ReportFlow Windows executable.

Build command (run from repo root):
    pyinstaller reportflow.spec --clean

Output:
    dist/ReportFlow.exe   — single-file Windows executable
"""

import sys
from pathlib import Path

block_cipher = None

# Collect the built-in HTML template so it is bundled inside the .exe
datas = [
    (
        str(Path("src/reportflow/templates/report.html")),
        "reportflow/templates",
    ),
]

a = Analysis(
    ["src/reportflow/cli.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # APScheduler job stores / triggers / executors
        "apscheduler.schedulers.background",
        "apscheduler.triggers.cron",
        "apscheduler.triggers.interval",
        "apscheduler.triggers.date",
        "apscheduler.jobstores.sqlalchemy",
        "apscheduler.executors.pool",
        # SQLAlchemy dialects used by APScheduler SQLite store
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        # Pydantic internals
        "pydantic.v1.validators",
        "pydantic_core",
        # Pandas / numpy optional backends
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timestamps",
        # Jinja2
        "jinja2.ext",
        # Click
        "click",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "PIL",
        "IPython",
        "notebook",
        "pytest",
        "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ReportFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # keep console window so users see log output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows-specific metadata
    version=None,          # set via --version-file in CI if needed
    icon=None,             # set to "assets/icon.ico" if an icon is added
)
