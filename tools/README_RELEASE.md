# Release Trigger Tool

This tool automates the process of bumping the project version, tagging the repository, and triggering the GitHub Actions CI/CD pipeline.

## How it works:
1.  **Reads** the current version from `pyproject.toml`.
2.  **Calculates** the next version based on your input (patch, minor, or major).
3.  **Updates** the version in the configuration.
4.  **Commits and Pushes** the changes to the `main` branch.
5.  **Creates and Pushes** a new Git tag (e.g., `v1.2.1`).

## Usage:
Run the script from the root of the repository:
```bash
python tools/trigger_release.py
```

Follow the interactive prompts to complete the release.
