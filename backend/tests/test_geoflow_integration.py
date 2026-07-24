import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.geoflow_integration import (  # noqa: E402
    _build_geoflow_integration_config,
    _extract_keywords_from_text,
    _titles_from_keywords,
    _unwrap_resource_id,
    build_preview_handoff_result,
    normalize_geoflow_integration_payload,
    public_geoflow_status,
    verify_callback_signature,
)


class GeoflowIntegrationTests(unittest.TestCase):
    def test_build_config_defaults_and_env_fallback(self):
        config = _build_geoflow_integration_config({})
        self.assertIn("base_url", config)
        self.assertEqual(config["public_cta_label"], "发送到 GEOFlow")
        self.assertIn("enabled", config)
        self.assertIn("default_company_id", config)

    def test_normalize_payload_keeps_limits(self):
        config = normalize_geoflow_integration_payload(
            {
                "enabled": True,
                "base_url": "http://localhost:18080",
                "public_base_url": "http://localhost:18080",
                "draft_limit": 99,
                "article_limit": 0,
                "timeout_seconds": 3,
            }
        )
        self.assertTrue(config["enabled"])
        self.assertEqual(config["draft_limit"], 50)
        self.assertEqual(config["article_limit"], 1)
        self.assertEqual(config["timeout_seconds"], 5)

    def test_public_status_preview_without_token(self):
        status = public_geoflow_status(
            {
                "enabled": True,
                "base_url": "http://localhost:18080",
                "public_base_url": "http://localhost:18080",
                "public_cta_label": "发送到 GEOFlow",
            },
            has_token=False,
        )
        self.assertEqual(status["mode"], "preview")
        self.assertFalse(status["configured"])
        self.assertEqual(status["suite_path"], "/suite?step=review")

    def test_keyword_and_title_helpers(self):
        keywords = _extract_keywords_from_text("GEO 诊断, AI 搜索\n品牌可见性")
        self.assertGreaterEqual(len(keywords), 2)
        titles = _titles_from_keywords(keywords, "brief")
        self.assertTrue(titles)
        self.assertIn("keyword", titles[0])

    def test_preview_handoff_shape(self):
        result = build_preview_handoff_result(
            task_name="demo",
            brief="hello world",
            keywords=["GEO"],
            titles=[{"title": "t", "keyword": "GEO"}],
            config={"public_base_url": "http://localhost:18080"},
        )
        self.assertEqual(result["mode"], "preview")
        self.assertIn("next_steps", result)
        self.assertIn("geo_admin/tasks", result["geoflow_admin_url"])

    def test_unwrap_nested_item_id(self):
        payload = {"success": True, "data": {"item": {"id": 42, "name": "kb"}}}
        self.assertEqual(_unwrap_resource_id(payload), 42)

    def test_callback_signature(self):
        from app.core.config import settings

        original = settings.GEOSUITE_CALLBACK_SECRET
        settings.GEOSUITE_CALLBACK_SECRET = "suite-test-secret"
        try:
            body = b'{"event":"article.published"}'
            import hashlib
            import hmac

            sig = "sha256=" + hmac.new(b"suite-test-secret", body, hashlib.sha256).hexdigest()
            self.assertTrue(verify_callback_signature(body, sig))
            self.assertFalse(verify_callback_signature(body, "sha256=deadbeef"))
        finally:
            settings.GEOSUITE_CALLBACK_SECRET = original


if __name__ == "__main__":
    unittest.main()
