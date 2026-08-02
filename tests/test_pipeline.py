import unittest
import json
import shutil
import sys
import os
from pathlib import Path

# Add src to sys.path to allow importing reportflow
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportflow.pipeline import run_pipeline

class TestReportFlow(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_output")
        self.data_dir = Path("test_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Create dummy data
        self.csv_file = self.data_dir / "test.csv"
        self.csv_file.write_text("period,value\n2023,1000\n2024,1200", encoding="utf-8")
        
        self.config_file = self.data_dir / "config.json"
        self.config = {
            "title": "Test Report",
            "sources": [
                {
                    "name": "LocalCSV",
                    "type": "file",
                    "path": "test.csv",
                    "format": "csv"
                }
            ],
            "output_formats": ["json", "csv", "html"]
        }
        self.config_file.write_text(json.dumps(self.config), encoding="utf-8")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)

    def test_end_to_end_pipeline(self):
        results = run_pipeline(self.config_file, self.test_dir)
        
        self.assertIn("json", results)
        self.assertIn("csv", results)
        self.assertIn("html", results)
        
        # Verify JSON content
        with open(results["json"], "r") as f:
            data = json.load(f)
            self.assertEqual(data["title"], "Test Report")
            self.assertEqual(len(data["records"]), 2)
            # In our new pipeline, numeric values are converted to floats
            self.assertEqual(float(data["records"][0]["value"]), 1000.0)

if __name__ == "__main__":
    unittest.main()
