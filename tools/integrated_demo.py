import os
import time
from customize_template import create_custom_template
from manage_data_sources import add_data_source
from automate_scheduling import run_report

def run_integrated_demo():
    print("--- Starting Integrated ReportFlow Demo ---")
    
    project_root = "demo_project"
    os.makedirs(project_root, exist_ok=True)
    config_path = os.path.join(project_root, "config.json")
    output_dir = os.path.join(project_root, "output")
    
    # 1. Customize Template
    print("[Step 1] Customizing report theme...")
    create_custom_template(project_root, theme_color="#8e44ad", company_name="Manus Global Systems")
    
    # 2. Manage Data Sources
    print("[Step 2] Adding data sources...")
    # Add a dummy local CSV for the demo
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_file = os.path.join(data_dir, "market_stats.csv")
    with open(csv_file, "w") as f:
        f.write("asset,price,change\nBTC,65000,+2%\nETH,3500,-1%\nSOL,150,+5%")
    
    add_data_source(config_path, "Crypto Market", "file", "data/market_stats.csv", "csv")
    
    # 3. Run Report (Simulating one execution of the scheduler)
    print("[Step 3] Running the automated report...")
    run_report(config_path, output_dir)
    
    print("\n--- Demo Completed ---")
    print(f"Project created at: {os.path.abspath(project_root)}")
    print(f"Check the report at: {os.path.join(output_dir, 'report.html')}")

if __name__ == "__main__":
    run_integrated_demo()
