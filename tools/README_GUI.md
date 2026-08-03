# ReportFlow GUI Prototype

This script provides a graphical user interface (GUI) for the ReportFlow Automation tool, built with `CustomTkinter`.

## Features:
- **Modern UI**: Dark/Light theme support.
- **Config Management**: Load configuration files via a button or drag-and-drop.
- **Report Generation**: Trigger report generation with a single click.
- **Output Log**: View real-time output and errors from the ReportFlow CLI.
- **Open Output Folder**: Easily access generated reports.

## Prerequisites:
Install the required Python libraries:
```bash
pip install customtkinter tkdnd2
```

## Usage:
Run the script from the root of the repository:
```bash
python tools/reportflow_gui.py
```

**Note**: For drag-and-drop functionality, `tkdnd2` needs to be properly installed and configured for your Tkinter environment. On some systems, this might require additional steps or a specific Tkinter version.
