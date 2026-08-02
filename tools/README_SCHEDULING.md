# Automation & Scheduling Tool

Automate your report generation using a simple scheduling mechanism.

## Prerequisites
Install the `schedule` library:
```bash
pip install schedule
```

## Usage
Define your interval and let the scheduler handle the rest.

```python
from automate_scheduling import start_scheduler

start_scheduler(
    config_path="config.json", 
    output_dir="reports/daily", 
    interval_seconds=3600  # Every hour
)
```
