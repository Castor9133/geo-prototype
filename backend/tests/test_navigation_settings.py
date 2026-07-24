import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.navigation_settings import (  # noqa: E402
    NavigationMenuValidationError,
    ensure_suite_in_navigation_menu,
    get_default_navigation_menu,
    normalize_navigation_menu_payload,
)


class NavigationSettingsTests(unittest.TestCase):
    def test_default_menu_uses_new_tab(self):
        menu = get_default_navigation_menu()

        self.assertGreaterEqual(len(menu["items"]), 7)
        self.assertEqual(menu["items"][0]["id"], "suite")
        self.assertEqual(menu["items"][0]["url"], "/suite")
        self.assertEqual(menu["items"][0]["target"], "_self")
        self.assertTrue(
            all(item["target"] == "_blank" for item in menu["items"] if item["id"] != "suite")
        )
        self.assertEqual(menu["items"][1]["url"], "/companies")
        self.assertFalse(
            {"experts", "tutorial", "github"} & {item["id"] for item in menu["items"]}
        )

    def test_normalizer_preserves_order_and_supported_targets(self):
        menu = normalize_navigation_menu_payload(
            {
                "items": [
                    {"id": "docs", "label": "文档", "url": "https://docs.example.com", "target": "_blank"},
                    {"id": "about", "label": "关于", "url": "/about", "target": "_self", "enabled": False},
                ]
            }
        )

        self.assertEqual([item["id"] for item in menu["items"]], ["docs", "about"])
        self.assertEqual(menu["items"][0]["target"], "_blank")
        self.assertEqual(menu["items"][1]["target"], "_self")
        self.assertFalse(menu["items"][1]["enabled"])

    def test_normalizer_defaults_missing_target_to_new_tab(self):
        menu = normalize_navigation_menu_payload(
            {"items": [{"label": "首页", "url": "/"}]}
        )

        self.assertEqual(menu["items"][0]["target"], "_blank")

    def test_normalizer_rejects_unsafe_urls(self):
        with self.assertRaisesRegex(NavigationMenuValidationError, "HTTP"):
            normalize_navigation_menu_payload(
                {"items": [{"label": "危险链接", "url": "javascript:alert(1)"}]}
            )

    def test_ensure_suite_prepends_missing_item(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "companies", "label": "公司", "url": "/companies", "target": "_blank"},
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank"},
                ]
            }
        )

        self.assertEqual(menu["items"][0]["id"], "suite")
        self.assertEqual(menu["items"][0]["url"], "/suite")
        self.assertEqual(menu["items"][1]["id"], "companies")

    def test_ensure_suite_keeps_existing_suite(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "companies", "label": "公司", "url": "/companies", "target": "_blank"},
                ]
            }
        )

        self.assertEqual([item["id"] for item in menu["items"]], ["suite", "companies"])

    def test_ensure_suite_strips_removed_product_entries(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "experts", "label": "专家", "url": "/experts", "target": "_blank"},
                    {"id": "tutorial", "label": "教程", "url": "/tutorial", "target": "_blank"},
                    {"id": "github", "label": "GitHub", "url": "https://github.com/yaojingang/georank", "target": "_blank"},
                    {"id": "companies", "label": "公司", "url": "/companies", "target": "_blank"},
                ]
            }
        )

        self.assertEqual([item["id"] for item in menu["items"]], ["suite", "companies"])


if __name__ == "__main__":
    unittest.main()
