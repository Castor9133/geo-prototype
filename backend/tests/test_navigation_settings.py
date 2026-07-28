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
    def test_default_menu_uses_same_tab_for_internal(self):
        menu = get_default_navigation_menu()

        self.assertGreaterEqual(len(menu["items"]), 4)
        self.assertEqual(menu["items"][0]["id"], "suite")
        self.assertEqual(menu["items"][0]["url"], "/suite")
        self.assertEqual(menu["items"][0]["target"], "_self")
        self.assertEqual(menu["items"][1]["url"], "/diagnostic")
        self.assertFalse(
            {"companies", "experts", "tutorial", "github", "solutions", "plans", "tools"}
            & {item["id"] for item in menu["items"]}
        )
        self.assertEqual(
            {item["id"] for item in menu["items"]},
            {"suite", "diagnostic", "knowledge", "keywords", "distribute", "measure", "config"},
        )
        knowledge = next(item for item in menu["items"] if item["id"] == "knowledge")
        self.assertEqual(knowledge["url"], "/knowledge")
        self.assertEqual(knowledge["target"], "_self")
        distribute = next(item for item in menu["items"] if item["id"] == "distribute")
        self.assertEqual(distribute["url"], "/distribute")
        self.assertEqual(distribute["target"], "_self")
        self.assertTrue(all(item["target"] == "_self" for item in menu["items"]))

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

    def test_normalizer_defaults_internal_paths_to_same_tab(self):
        menu = normalize_navigation_menu_payload(
            {"items": [{"label": "首页", "url": "/"}]}
        )

        self.assertEqual(menu["items"][0]["target"], "_self")

    def test_normalizer_rejects_unsafe_urls(self):
        with self.assertRaisesRegex(NavigationMenuValidationError, "HTTP"):
            normalize_navigation_menu_payload(
                {"items": [{"label": "危险链接", "url": "javascript:alert(1)"}]}
            )

    def test_ensure_suite_prepends_missing_item(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank"},
                    {"id": "solutions", "label": "问答", "url": "/solutions", "target": "_blank"},
                    {"id": "plans", "label": "方案", "url": "/plans", "target": "_blank"},
                ]
            }
        )

        self.assertEqual(menu["items"][0]["id"], "suite")
        self.assertEqual(menu["items"][0]["url"], "/suite")
        self.assertEqual(menu["items"][1]["id"], "diagnostic")
        self.assertEqual(menu["items"][1]["target"], "_self")
        self.assertFalse({"solutions", "plans"} & {item["id"] for item in menu["items"]})

    def test_ensure_suite_keeps_existing_suite(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank"},
                ]
            }
        )

        self.assertEqual([item["id"] for item in menu["items"]], ["suite", "diagnostic", "knowledge", "distribute"])

    def test_ensure_suite_strips_removed_product_entries(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "companies", "label": "公司", "url": "/companies", "target": "_blank"},
                    {"id": "experts", "label": "专家", "url": "/experts", "target": "_blank"},
                    {"id": "tutorial", "label": "教程", "url": "/tutorial", "target": "_blank"},
                    {"id": "github", "label": "GitHub", "url": "https://github.com/yaojingang/georank", "target": "_blank"},
                    {"id": "tools", "label": "工具", "url": "/tools", "target": "_blank"},
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank"},
                ]
            }
        )

        self.assertEqual([item["id"] for item in menu["items"]], ["suite", "diagnostic", "knowledge", "distribute"])
        self.assertFalse({"tools", "companies"} & {item["id"] for item in menu["items"]})

    def test_ensure_suite_rewrites_legacy_knowledge_url(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank"},
                    {"id": "knowledge", "label": "知识库", "url": "/suite?step=knowledge", "target": "_self"},
                    {"id": "distribute", "label": "分发", "url": "/admin/content-engine?tab=tasks", "target": "_blank"},
                ]
            }
        )

        knowledge = next(item for item in menu["items"] if item["id"] == "knowledge")
        self.assertEqual(knowledge["url"], "/knowledge")
        self.assertEqual(knowledge["target"], "_self")
        distribute = next(item for item in menu["items"] if item["id"] == "distribute")
        self.assertEqual(distribute["url"], "/distribute")
        self.assertEqual(distribute["target"], "_self")

    def test_ensure_suite_rewrites_admin_content_engine_to_public(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "knowledge", "label": "知识库", "url": "/admin/content-engine", "target": "_blank"},
                ]
            }
        )
        knowledge = next(item for item in menu["items"] if item["id"] == "knowledge")
        self.assertEqual(knowledge["url"], "/knowledge")
        self.assertEqual(knowledge["target"], "_self")

    def test_ensure_suite_dedupes_duplicate_distribute(self):
        menu = ensure_suite_in_navigation_menu(
            {
                "items": [
                    {"id": "suite", "label": "GEO Suite", "url": "/suite", "target": "_self"},
                    {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_self"},
                    {"id": "knowledge", "label": "知识库", "url": "/knowledge", "target": "_self"},
                    {"id": "keywords", "label": "拓词", "url": "/keywords", "target": "_self"},
                    {"id": "distribute", "label": "分发", "url": "/distribute", "target": "_self"},
                    {"id": "distribute", "label": "分发", "url": "/distribute", "target": "_self"},
                    {"id": "distribute", "label": "分发", "url": "/knowledge?tab=tasks", "target": "_self"},
                    {"id": "distribute", "label": "分发", "url": "/admin/content-engine?tab=channels", "target": "_blank"},
                    {"id": "measure", "label": "观测", "url": "/suite?step=measure", "target": "_self"},
                    {"id": "config", "label": "配置", "url": "/settings", "target": "_self"},
                ]
            }
        )
        ids = [item["id"] for item in menu["items"]]
        self.assertEqual(ids.count("distribute"), 1)
        self.assertEqual(
            ids,
            ["suite", "diagnostic", "knowledge", "keywords", "distribute", "measure", "config"],
        )


if __name__ == "__main__":
    unittest.main()
