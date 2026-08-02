"""
Comprehensive tests for reportflow.branding.

Covers:
- BrandingConfig defaults and custom values
- CSS variable generation (_build_css_vars)
- build_template_context merging
- get_jinja_env: built-in template path
- get_jinja_env: custom template path
- get_jinja_env: missing custom template raises FileNotFoundError
- Template rendering with custom brand values
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportflow.branding import (
    BrandingConfig,
    _build_css_vars,
    build_template_context,
    get_jinja_env,
    BUILTIN_TEMPLATE_NAME,
)


class TestBrandingConfigDefaults(unittest.TestCase):

    def test_default_company_name(self):
        b = BrandingConfig()
        self.assertEqual(b.company_name, "ReportFlow")

    def test_default_primary_color(self):
        b = BrandingConfig()
        self.assertEqual(b.primary_color, "#1e3a8a")

    def test_default_show_sha256(self):
        b = BrandingConfig()
        self.assertTrue(b.show_sha256)

    def test_default_show_powered_by(self):
        b = BrandingConfig()
        self.assertTrue(b.show_powered_by)

    def test_default_custom_template_path_is_none(self):
        b = BrandingConfig()
        self.assertIsNone(b.custom_template_path)

    def test_custom_values_accepted(self):
        b = BrandingConfig(
            company_name="Acme",
            primary_color="#ff0000",
            show_sha256=False,
        )
        self.assertEqual(b.company_name, "Acme")
        self.assertEqual(b.primary_color, "#ff0000")
        self.assertFalse(b.show_sha256)

    def test_extra_fields_allowed(self):
        """BrandingConfig should silently accept unknown keys (forward-compat)."""
        b = BrandingConfig(unknown_future_field="value")
        self.assertIsNotNone(b)


class TestBuildCssVars(unittest.TestCase):

    def test_contains_primary_color(self):
        b = BrandingConfig(primary_color="#aabbcc")
        css = _build_css_vars(b)
        self.assertIn("#aabbcc", css)

    def test_contains_all_tokens(self):
        b = BrandingConfig()
        css = _build_css_vars(b)
        for token in ("--rf-primary", "--rf-secondary", "--rf-accent", "--rf-text",
                      "--rf-bg", "--rf-card-border", "--rf-font", "--rf-heading-font"):
            self.assertIn(token, css, f"Token {token!r} missing from CSS vars")

    def test_heading_font_falls_back_to_font_family(self):
        b = BrandingConfig(font_family="Arial", heading_font_family=None)
        css = _build_css_vars(b)
        # heading font should equal font_family when not set
        self.assertIn("Arial", css)

    def test_heading_font_override(self):
        b = BrandingConfig(font_family="Arial", heading_font_family="Georgia")
        css = _build_css_vars(b)
        self.assertIn("Georgia", css)


class TestBuildTemplateContext(unittest.TestCase):

    def test_brand_key_present(self):
        b = BrandingConfig()
        ctx = build_template_context({"title": "T"}, b)
        self.assertIn("brand", ctx)
        self.assertIsInstance(ctx["brand"], BrandingConfig)

    def test_css_vars_key_present(self):
        b = BrandingConfig()
        ctx = build_template_context({}, b)
        self.assertIn("css_vars", ctx)

    def test_base_context_preserved(self):
        b = BrandingConfig()
        ctx = build_template_context({"title": "My Report", "records": [1, 2]}, b)
        self.assertEqual(ctx["title"], "My Report")
        self.assertEqual(ctx["records"], [1, 2])

    def test_brand_values_accessible(self):
        b = BrandingConfig(company_name="TestCo")
        ctx = build_template_context({}, b)
        self.assertEqual(ctx["brand"].company_name, "TestCo")


class TestGetJinjaEnv(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_builtin_env_returns_correct_template_name(self):
        b = BrandingConfig()
        env, name = get_jinja_env(b)
        self.assertEqual(name, BUILTIN_TEMPLATE_NAME)

    def test_builtin_template_loadable(self):
        b = BrandingConfig()
        env, name = get_jinja_env(b)
        tpl = env.get_template(name)
        self.assertIsNotNone(tpl)

    def test_custom_template_path_used(self):
        custom = self.tmp / "custom.html"
        custom.write_text("<p>{{ title }}</p>", encoding="utf-8")
        b = BrandingConfig(custom_template_path=str(custom))
        env, name = get_jinja_env(b)
        self.assertEqual(name, "custom.html")

    def test_custom_template_renders(self):
        custom = self.tmp / "custom.html"
        custom.write_text("<p>{{ title }} — {{ brand.company_name }}</p>", encoding="utf-8")
        b = BrandingConfig(company_name="Acme", custom_template_path=str(custom))
        env, name = get_jinja_env(b)
        tpl = env.get_template(name)
        result = tpl.render(title="Report", brand=b)
        self.assertIn("Report", result)
        self.assertIn("Acme", result)

    def test_missing_custom_template_raises(self):
        b = BrandingConfig(custom_template_path="/nonexistent/path/template.html")
        with self.assertRaises(FileNotFoundError):
            get_jinja_env(b)


class TestBuiltinTemplateRendering(unittest.TestCase):
    """Smoke-test the built-in template with a minimal context."""

    def _render(self, brand: BrandingConfig, extra_ctx: dict = None) -> str:
        from datetime import datetime, timezone

        class FakeSnapshot:
            name = "TestSource"
            source = "/tmp/test.csv"
            sha256 = "a" * 64
            retrieved_at = datetime.now(timezone.utc)

        env, name = get_jinja_env(brand)
        tpl = env.get_template(name)
        base_ctx = {
            "title": "Unit Test Report",
            "snapshots": [FakeSnapshot()],
            "records": [{"col": 1}],
            "table_html": "<table><tr><td>1</td></tr></table>",
            "generated_at": "2026-01-01 00:00:00 UTC",
        }
        if extra_ctx:
            base_ctx.update(extra_ctx)
        ctx = build_template_context(base_ctx, brand)
        return tpl.render(**ctx)

    def test_title_in_output(self):
        html = self._render(BrandingConfig())
        self.assertIn("Unit Test Report", html)

    def test_company_name_in_output(self):
        html = self._render(BrandingConfig(company_name="MyCompany"))
        self.assertIn("MyCompany", html)

    def test_sha256_shown_by_default(self):
        html = self._render(BrandingConfig())
        self.assertIn("SHA-256", html)

    def test_sha256_hidden_when_disabled(self):
        html = self._render(BrandingConfig(show_sha256=False))
        self.assertNotIn("SHA-256", html)

    def test_powered_by_shown_by_default(self):
        html = self._render(BrandingConfig())
        self.assertIn("Powered by", html)

    def test_powered_by_hidden_when_disabled(self):
        html = self._render(BrandingConfig(show_powered_by=False))
        self.assertNotIn("Powered by", html)

    def test_custom_footer_text(self):
        html = self._render(BrandingConfig(footer_text="Top Secret"))
        self.assertIn("Top Secret", html)

    def test_logo_rendered_when_provided(self):
        html = self._render(BrandingConfig(logo_url="https://example.com/logo.png"))
        self.assertIn("https://example.com/logo.png", html)

    def test_no_logo_img_when_not_provided(self):
        html = self._render(BrandingConfig(logo_url=None))
        self.assertNotIn('class="company-logo"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
