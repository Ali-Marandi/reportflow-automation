import json
import tempfile
import unittest
from pathlib import Path

from reportflow.pipeline import run_pipeline
from reportflow.sources import load_file


class PipelineTests(unittest.TestCase):
    def test_csv_snapshot_has_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "data.csv"
            source.write_text("period,value\n2025,104.2\n", encoding="utf-8")
            snapshot = load_file("index", source, "csv")
            self.assertEqual(snapshot.rows[0]["period"], "2025")
            self.assertEqual(len(snapshot.sha256), 64)

    def test_end_to_end_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rates.csv").write_text("period,value\n2024,4.5\n2025,4.25\n", encoding="utf-8")
            (root / "commodities.json").write_text(
                json.dumps([{"period": "2025", "instrument": "Brent", "value": 82.4}]),
                encoding="utf-8",
            )
            config = {
                "title": "Macro report",
                "sources": [
                    {"name": "policy_rate", "type": "file", "format": "csv", "path": "rates.csv"},
                    {"name": "commodities", "type": "file", "format": "json", "path": "commodities.json"},
                ],
            }
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            outputs = run_pipeline(config_path, root / "out")
            self.assertTrue(Path(outputs["report.html"]).exists())
            payload = json.loads(Path(outputs["report.json"]).read_text(encoding="utf-8"))
            self.assertEqual(len(payload["records"]), 3)
            self.assertEqual(len(payload["provenance"]), 2)


if __name__ == "__main__":
    unittest.main()
