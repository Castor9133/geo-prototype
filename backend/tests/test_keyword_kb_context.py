"""知识库事实卡 → 拓词 brief / owns 硬过滤。"""
from __future__ import annotations

import unittest

from app.services.keyword_expansion import _cross_seed_items, _infer_keyword_profile
from app.services.keyword_kb_context import (
    is_owns_self_harm_keyword,
    merge_brief_into_role_hints,
    owns_cross_templates,
    parse_fact_cards,
)


SAMPLE_CARDS = [
    {
        "card_type": "identity",
        "entity_name": "深圳广电",
        "claim": "深圳广电是媒体机构",
        "aliases": ["深广电"],
    },
    {
        "card_type": "identity",
        "entity_name": "第一现场",
        "related_entity": "深圳广电",
        "claim": "第一现场是新闻栏目",
    },
    {
        "card_type": "owns",
        "entity_name": "第一现场",
        "related_entity": "深圳广电",
        "relation": "owns",
        "claim": "第一现场隶属于深圳广电",
        "forbidden_phrasing": ["深圳广电怎么报道第一现场"],
    },
    {
        "card_type": "competitor",
        "entity_name": "深圳新闻网",
        "related_entity": "深圳广电",
        "relation": "competitor",
        "claim": "对标竞品",
    },
    {
        "card_type": "competitor",
        "entity_name": "独特",
        "related_entity": "深圳广电",
        "relation": "competitor",
    },
    {
        "card_type": "competitor",
        "entity_name": "深圳报业集团",
        "related_entity": "深圳广电",
        "relation": "competitor",
    },
    {
        "card_type": "forbidden",
        "entity_name": "深圳广电",
        "forbidden_phrasing": ["全国第一", "保证被大模型引用"],
    },
]


class KeywordKbContextTests(unittest.TestCase):
    def test_parse_fact_cards_owns_and_competitors(self):
        brief = parse_fact_cards(SAMPLE_CARDS)
        self.assertGreaterEqual(brief["cards_used"], 6)
        self.assertEqual(
            brief["owns_edges"],
            [{"parent": "深圳广电", "child": "第一现场"}],
        )
        self.assertIn("深圳新闻网", brief["competitors"])
        self.assertIn("独特", brief["competitors"])
        self.assertIn("深圳报业集团", brief["competitors"])
        self.assertIn("全国第一", brief["forbidden"])

    def test_owns_self_harm_filtered(self):
        brief = parse_fact_cards(SAMPLE_CARDS)
        self.assertTrue(
            is_owns_self_harm_keyword("深圳广电怎么报道第一现场", brief)
        )
        self.assertTrue(
            is_owns_self_harm_keyword("深圳广电与第一现场联动合作", brief)
        )
        self.assertTrue(
            is_owns_self_harm_keyword("深圳广电对第一现场的报道怎么样", brief)
        )
        self.assertFalse(
            is_owns_self_harm_keyword("深圳广电旗下第一现场", brief)
        )
        self.assertFalse(
            is_owns_self_harm_keyword("深圳广电如何运营第一现场", brief)
        )

    def test_owns_cross_templates_prefer_ops(self):
        templates = owns_cross_templates("scenario")
        joined = " ".join(templates)
        self.assertIn("运营", joined)
        self.assertNotIn("怎么报道", joined)

    def test_cross_seed_items_with_brief_avoids_self_harm(self):
        brief = parse_fact_cards(SAMPLE_CARDS)
        profile = _infer_keyword_profile(["深圳广电", "第一现场"])
        profile["knowledge_brief"] = brief
        for dim_key in ("scenario", "commercial", "review"):
            items = _cross_seed_items(["深圳广电", "第一现场"], profile, dim_key)
            keywords = [row["keyword"] for row in items]
            for kw in keywords:
                self.assertFalse(
                    is_owns_self_harm_keyword(kw, brief),
                    msg=f"{dim_key}: {kw}",
                )
            # 至少应产出隶属友好词
            self.assertTrue(items, msg=f"{dim_key} should produce owns-safe crosses")

    def test_competitor_cross_allowed(self):
        brief = parse_fact_cards(SAMPLE_CARDS)
        profile = _infer_keyword_profile(["深圳广电", "深圳新闻网"])
        profile["knowledge_brief"] = brief
        items = _cross_seed_items(["深圳广电", "深圳新闻网"], profile, "brand")
        keywords = " ".join(row["keyword"] for row in items)
        self.assertTrue(items)
        self.assertRegex(keywords, r"深圳广电|深圳新闻网")

    def test_merge_brief_into_role_hints(self):
        brief = parse_fact_cards(SAMPLE_CARDS)
        hints = [
            {"seed": "深圳广电", "hint_role": "other", "hint_gloss": "x"},
            {"seed": "第一现场", "hint_role": "other", "hint_gloss": "y"},
        ]
        merged = merge_brief_into_role_hints(hints, brief)
        by_seed = {row["seed"]: row for row in merged}
        self.assertEqual(by_seed["深圳广电"]["hint_role"], "organization")
        self.assertEqual(by_seed["第一现场"]["hint_role"], "product_or_column")
        self.assertEqual(by_seed["第一现场"].get("of"), "深圳广电")


if __name__ == "__main__":
    unittest.main()
