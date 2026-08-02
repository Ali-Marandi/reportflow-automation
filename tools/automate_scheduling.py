import time
import schedule
import subprocess
from datetime import datetime

def run_report(config_path, output_dir):
    """
    Executes the reportflow CLI command.
    """
    print(f"[{datetime.now()}] Running scheduled report...")
    try:
        result = subprocess.run(
            ["reportflow", config_path, "--output", output_dir],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Success.")
        else:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed: {e}")

def start_scheduler(config_path, output_dir, interval_seconds=60):
    """
    Starts the scheduler loop.
    """
    schedule.every(interval_seconds).seconds.do(run_report, config_path, output_dir)
    
    print(f"Scheduler started. Running every {interval_seconds} seconds.")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Note: Requires 'pip install schedule'
    # start_scheduler("config.json", "output")
    pass
