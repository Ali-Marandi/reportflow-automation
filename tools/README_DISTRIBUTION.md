# Windows Distribution Tools

These tools help you distribute ReportFlow to Windows users in a professional manner.

## 1. Auto-Downloader (`download_and_run_rf.py`)
This script is useful for users who always want the latest version.
- **What it does**: Connects to GitHub API, finds the latest `.exe` in the releases, downloads it, and optionally runs it.
- **Dependencies**: `pip install requests`

## 2. MSI Installer Builder (`create_msi_installer.py`)
Standard Windows Installer (MSI) support.
- **What it does**: Generates a WiX Toolset configuration (`.wxs`) that packages your `.exe` into a professional installer.
- **Features**: 
    - Installs to `C:\Program Files\ReportFlow`.
    - Adds a Start Menu shortcut.
    - Supports clean uninstallation.
- **How to Build**: 
    1. Run the script to get `reportflow.wxs`.
    2. Install [WiX Toolset](https://wixtoolset.org/) on Windows.
    3. Run `candle` and `light` as shown in the script output.

---
These scripts make your Python tool feel like a native Windows application.
