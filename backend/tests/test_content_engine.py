"""内容引擎纯逻辑测试（可离线，不依赖 Postgres / asyncpg）。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.content_engine_utils import (  # noqa: E402
    CHINA_PROMPTS,
    cosine,
    local_hash_embedding,
    repo_root,
    slugify,
    soften_markdown_prose,
    split_chunks,
)


class ContentEngineUnitTests(unittest.TestCase):
    def test_split_chunks_by_paragraphs(self):
        text = "第一段内容。\n\n第二段内容。\n\n" + ("长段落" * 200)
        chunks = split_chunks(text, max_chars=80)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(len(c) <= 80 for c in chunks))

    def test_split_chunks_empty(self):
        self.assertEqual(split_chunks(""), [])
        self.assertEqual(split_chunks("   "), [])

    def test_local_hash_embedding_deterministic(self):
        a = local_hash_embedding("DJI Mini 5 Pro 续航")
        b = local_hash_embedding("DJI Mini 5 Pro 续航")
        c = local_hash_embedding("完全不同的主题")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertAlmostEqual(sum(x * x for x in a), 1.0, places=5)
        self.assertLess(cosine(a, c), cosine(a, b))

    def test_cosine_handles_none(self):
        self.assertEqual(cosine(None, [1.0]), 0.0)
        self.assertEqual(cosine([], [1.0]), 0.0)

    def test_slugify(self):
        self.assertEqual(slugify("  Hello World!!  "), "hello-world")
        self.assertTrue(len(slugify("中文产品演示")) > 0)
        self.assertEqual(slugify(""), "kb")

    def test_repo_root_points_to_demo_pack(self):
        root = repo_root()
        demo = root / "docs" / "pilot-demo" / "cn-product-demo-v2" / "fact-cards"
        self.assertTrue((root / "backend").is_dir(), f"repo root missing backend: {root}")
        self.assertTrue(demo.is_dir(), f"expected demo fact-cards at {demo}")
        self.assertGreaterEqual(len(list(demo.glob("*.md"))), 10)

    def test_china_prompts_seed_shape(self):
        self.assertGreaterEqual(len(CHINA_PROMPTS), 7)
        for item in CHINA_PROMPTS:
            self.assertIn("{{Knowledge}}", item["body"])
            self.assertIn("title", item)
            self.assertIn("sort_order", item)
            self.assertIn("禁止", item["body"])
            self.assertIn("Markdown", item["body"])

    def test_soften_markdown_prose(self):
        raw = (
            "# 大疆为什么值得信任\n\n"
            "这是**加粗**与*斜体*，还有`代码`。\n\n"
            "---\n\n"
            "## 一、图传距离\n\n"
            "详见 [官网](https://www.dji.com)。\n"
        )
        soft = soften_markdown_prose(raw)
        self.assertNotIn("**", soft)
        self.assertNotIn("---", soft)
        self.assertNotIn("#", soft)
        self.assertNotIn("`", soft)
        self.assertIn("加粗", soft)
        self.assertIn("官网", soft)
        self.assertIn("一、图传距离", soft)

    def test_channel_templates_manifest_five_shells(self):
        manifest = repo_root() / "dist" / "data" / "channel-templates.json"
        self.assertTrue(manifest.is_file(), f"missing {manifest}")
        import json

        data = json.loads(manifest.read_text(encoding="utf-8"))
        keys = {item["key"] for item in data["items"]}
        self.assertEqual(
            keys,
            {
                "wechat-article",
                "zhihu-answer",
                "xiaohongshu-note",
                "site-faq",
                "douyin-script",
            },
        )
        for item in data["items"]:
            self.assertTrue(item.get("flow_theme_keys"))
            self.assertIn("shell", item)


if __name__ == "__main__":
    unittest.main()
