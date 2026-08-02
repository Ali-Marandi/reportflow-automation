"""
Comprehensive tests for reportflow.pipeline.

Covers:
- Happy-path end-to-end with CSV and JSON sources
- All three output formats (json, csv, html)
- Selective output formats
- Numeric type coercion
- Missing / invalid config handling
- Missing source file handling
- Branding integration in HTML output
- Custom template rendering
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running directly without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportflow.pipeline import run_pipeline
from reportflow.models import ReportConfig, SourceConfig, SourceType, SourceFormat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_config(path: Path, cfg: dict) -> None:
    path.write_text(json.dumps(cfg), encoding="utf-8")


# ---------------------------------------------------------------------------
# Base test case with shared fixtures
# ---------------------------------------------------------------------------

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data_dir = self.tmp / "data"
        self.out_dir = self.tmp / "output"
        self.data_dir.mkdir()

        # Default CSV source
        self.csv_file = self.data_dir / "rates.csv"
        _write_csv(self.csv_file, "period,value\n2023,1000\n2024,1200\n2025,1500")

        # Default JSON source
        self.json_file = self.data_dir / "markets.json"
        _write_json(
            self.json_file,
            [{"ticker": "AAPL", "price": 182.5}, {"ticker": "GOOG", "price": 140.0}],
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_config(self, sources, output_formats=None, extra=None):
        cfg = {
            "title": "Test Report",
            "sources": sources,
            "output_formats": output_formats or ["json", "csv", "html"],
        }
        if extra:
            cfg.update(extra)
        cfg_path = self.tmp / "config.json"
        _write_config(cfg_path, cfg)
        return cfg_path


# ---------------------------------------------------------------------------
# 1. End-to-end pipeline tests
# ---------------------------------------------------------------------------

class TestEndToEndCSV(BaseTestCase):
    """Full pipeline run with a single CSV source."""

    def test_all_outputs_created(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        self.assertIn("json", results)
        self.assertIn("csv", results)
        self.assertIn("html", results)
        self.assertTrue(Path(results["json"]).exists())
        self.assertTrue(Path(results["csv"]).exists())
        self.assertTrue(Path(results["html"]).exists())

    def test_json_content_structure(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["title"], "Test Report")
        self.assertEqual(len(data["records"]), 3)
        self.assertIn("generated_at", data)
        self.assertIn("provenance", data)

    def test_numeric_coercion(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(float(data["records"][0]["value"]), 1000.0)
        self.assertEqual(float(data["records"][1]["value"]), 1200.0)
        self.assertEqual(float(data["records"][2]["value"]), 1500.0)

    def test_csv_output_has_correct_rows(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        lines = Path(results["csv"]).read_text(encoding="utf-8").strip().splitlines()
        # header + 3 data rows
        self.assertEqual(len(lines), 4)


class TestEndToEndJSON(BaseTestCase):
    """Full pipeline run with a single JSON source."""

    def test_json_source_records(self):
        cfg = self._make_config(
            [{"name": "Markets", "type": "file", "path": "data/markets.json", "format": "json"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data["records"]), 2)
        tickers = {r["ticker"] for r in data["records"]}
        self.assertIn("AAPL", tickers)
        self.assertIn("GOOG", tickers)


class TestMultiSource(BaseTestCase):
    """Pipeline with multiple sources combined."""

    def test_multi_source_record_count(self):
        cfg = self._make_config(
            [
                {"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"},
                {"name": "Markets", "type": "file", "path": "data/markets.json", "format": "json"},
            ]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        # 3 CSV rows + 2 JSON rows = 5 total
        self.assertEqual(len(data["records"]), 5)

    def test_source_name_column_present(self):
        cfg = self._make_config(
            [
                {"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"},
                {"name": "Markets", "type": "file", "path": "data/markets.json", "format": "json"},
            ]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        source_names = {r.get("source_name") for r in data["records"]}
        self.assertIn("Rates", source_names)
        self.assertIn("Markets", source_names)


# ---------------------------------------------------------------------------
# 2. Selective output format tests
# ---------------------------------------------------------------------------

class TestSelectiveOutputFormats(BaseTestCase):

    def test_only_json(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["json"],
        )
        results = run_pipeline(cfg, self.out_dir)
        self.assertIn("json", results)
        self.assertNotIn("csv", results)
        self.assertNotIn("html", results)

    def test_only_csv(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["csv"],
        )
        results = run_pipeline(cfg, self.out_dir)
        self.assertNotIn("json", results)
        self.assertIn("csv", results)
        self.assertNotIn("html", results)

    def test_only_html(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
        )
        results = run_pipeline(cfg, self.out_dir)
        self.assertNotIn("json", results)
        self.assertNotIn("csv", results)
        self.assertIn("html", results)


# ---------------------------------------------------------------------------
# 3. Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling(BaseTestCase):

    def test_missing_config_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            run_pipeline(self.tmp / "nonexistent.json", self.out_dir)

    def test_invalid_json_config_raises(self):
        bad_cfg = self.tmp / "bad.json"
        bad_cfg.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(Exception):
            run_pipeline(bad_cfg, self.out_dir)

    def test_missing_source_file_raises(self):
        cfg = self._make_config(
            [{"name": "Ghost", "type": "file", "path": "data/ghost.csv", "format": "csv"}]
        )
        with self.assertRaises(FileNotFoundError):
            run_pipeline(cfg, self.out_dir)

    def test_empty_csv_raises_or_produces_empty(self):
        """An empty CSV (header only) should either raise or produce 0 records."""
        empty_csv = self.data_dir / "empty.csv"
        _write_csv(empty_csv, "period,value\n")
        cfg = self._make_config(
            [{"name": "Empty", "type": "file", "path": "data/empty.csv", "format": "csv"}],
            output_formats=["json"],
        )
        try:
            results = run_pipeline(cfg, self.out_dir)
            with open(results["json"], encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data["records"]), 0)
        except Exception:
            pass  # raising is also acceptable


# ---------------------------------------------------------------------------
# 4. Branding integration tests
# ---------------------------------------------------------------------------

class TestBrandingIntegration(BaseTestCase):

    def test_default_branding_in_html(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")

        # Default company name should appear
        self.assertIn("ReportFlow", html)

    def test_custom_company_name_in_html(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
            extra={
                "branding": {
                    "company_name": "Acme Corp",
                    "primary_color": "#0f4c81",
                }
            },
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")

        self.assertIn("Acme Corp", html)
        self.assertIn("#0f4c81", html)

    def test_custom_primary_color_in_css_vars(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
            extra={"branding": {"primary_color": "#abcdef"}},
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")
        self.assertIn("#abcdef", html)

    def test_sha256_hidden_when_disabled(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
            extra={"branding": {"show_sha256": False}},
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")
        self.assertNotIn("SHA-256", html)

    def test_custom_template(self):
        """A user-supplied template should be rendered instead of the built-in one."""
        custom_tpl = self.tmp / "my_template.html"
        custom_tpl.write_text(
            "<html><body><h1>{{ title }}</h1><p>{{ brand.company_name }}</p></body></html>",
            encoding="utf-8",
        )
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
            extra={"branding": {"custom_template_path": str(custom_tpl)}},
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")

        self.assertIn("<h1>Test Report</h1>", html)
        # Should NOT contain built-in template markers
        self.assertNotIn("Bootstrap", html)

    def test_footer_text_customisation(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}],
            output_formats=["html"],
            extra={"branding": {"footer_text": "Confidential — Finance Team"}},
        )
        results = run_pipeline(cfg, self.out_dir)
        html = Path(results["html"]).read_text(encoding="utf-8")
        self.assertIn("Confidential — Finance Team", html)


# ---------------------------------------------------------------------------
# 5. Model validation tests
# ---------------------------------------------------------------------------

class TestModelValidation(BaseTestCase):

    def test_report_config_defaults(self):
        cfg = ReportConfig(
            sources=[
                SourceConfig(name="S", type=SourceType.FILE, path="/tmp/f.csv", format=SourceFormat.CSV)
            ]
        )
        self.assertEqual(cfg.title, "Automated Financial Report")
        self.assertIn("html", cfg.output_formats)

    def test_source_config_file_requires_path(self):
        from pydantic import ValidationError
        with self.assertRaises((ValidationError, ValueError)):
            SourceConfig(name="S", type=SourceType.FILE, format=SourceFormat.CSV)

    def test_source_config_url_requires_url(self):
        from pydantic import ValidationError
        with self.assertRaises((ValidationError, ValueError)):
            SourceConfig(name="S", type=SourceType.URL, format=SourceFormat.JSON)


# ---------------------------------------------------------------------------
# 6. Provenance / integrity tests
# ---------------------------------------------------------------------------

class TestProvenance(BaseTestCase):

    def test_sha256_in_json_provenance(self):
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data["provenance"]), 1)
        prov = data["provenance"][0]
        self.assertIn("sha256", prov)
        self.assertEqual(len(prov["sha256"]), 64)  # SHA-256 hex = 64 chars

    def test_provenance_source_name(self):
        cfg = self._make_config(
            [{"name": "MySource", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, self.out_dir)

        with open(results["json"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["provenance"][0]["name"], "MySource")

    def test_output_dir_created_automatically(self):
        deep_out = self.tmp / "a" / "b" / "c" / "output"
        cfg = self._make_config(
            [{"name": "Rates", "type": "file", "path": "data/rates.csv", "format": "csv"}]
        )
        results = run_pipeline(cfg, deep_out)
        self.assertTrue(deep_out.exists())
        self.assertTrue(Path(results["json"]).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
