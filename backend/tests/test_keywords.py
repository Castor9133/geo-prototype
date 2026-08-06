import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import delete

from tests.database_safety import resolve_test_database, verify_test_database_engine
from app.core.database import async_session, engine
from app.core.config import settings
from app.main import app
from app.models.settings import Setting
from app.services.keyword_expansion import (
    DIMENSIONS,
    _compose_expansion_system_prompt,
    _cross_seed_items,
    _infer_seed_role_hints,
    _infer_keyword_profile,
    _is_low_quality_keyword,
    _seeds_are_near_duplicates,
    expand_keywords,
    normalize_seeds,
)
from app.services.runtime_settings import invalidate_runtime_settings_cache


def _mock_ai_payload() -> str:
    dimensions = []
    for index, dimension in enumerate(DIMENSIONS, start=1):
        items = []
        for item_index in range(1, 9):
            items.append(
                {
                    "keyword": f"{dimension['name']}{item_index}",
                    "recommendation_score": 70 + ((index + item_index) % 12),
                    "business_score": 62 + ((index + item_index) % 15),
                    "reason": f"覆盖{dimension['name']}相关检索意图",
                }
            )
        dimensions.append({"key": dimension["key"], "items": items})
    return json.dumps({"dimensions": dimensions}, ensure_ascii=False)


class KeywordExpansionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_expand_keywords_uses_ai_json_payload(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(return_value=_mock_ai_payload()),
        ):
            payload = await expand_keywords(["GEO优化", "AI搜索"])

        self.assertEqual(payload["seeds"], ["GEO优化", "AI搜索"])
        self.assertEqual(payload["profile"]["name"], "企业服务")
        self.assertEqual(len(payload["dimensions"]), 8)
        self.assertEqual(payload["dimensions"][0]["key"], "semantic")
        # 多种子时后处理可能回填到每维上限 10
        self.assertGreaterEqual(len(payload["dimensions"][0]["items"]), 8)
        self.assertLessEqual(len(payload["dimensions"][0]["items"]), 10)
        self.assertGreater(payload["summary"]["total_keywords"], 0)

    async def test_expand_keywords_falls_back_when_ai_fails(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["GEO优化"])

        self.assertEqual(payload["seeds"], ["GEO优化"])
        self.assertEqual(payload["profile"]["name"], "企业服务")
        self.assertEqual(len(payload["dimensions"]), 8)
        self.assertTrue(all(dimension["items"] for dimension in payload["dimensions"]))
        self.assertGreaterEqual(payload["summary"]["average_recommendation_score"], 35)

    async def test_consumer_education_keywords_do_not_fall_back_to_b2b_scene_prefixes(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["数学辅导"])

        self.assertEqual(payload["profile"]["name"], "教育培训")
        scenario_keywords = [item["keyword"] for item in payload["dimensions"][1]["items"]]
        self.assertTrue(any("家长" in keyword or "学生" in keyword for keyword in scenario_keywords))
        self.assertFalse(any("B2B" in keyword or "SaaS" in keyword for keyword in scenario_keywords))

    async def test_multi_seed_fallback_covers_second_seed(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["深圳广电", "第一现场客户端"])

        self.assertEqual(payload["seeds"], ["深圳广电", "第一现场客户端"])
        self.assertIn("第一现场客户端", payload["profile"]["company_hint"])
        all_keywords = [
            item["keyword"]
            for dimension in payload["dimensions"]
            for item in dimension["items"]
        ]
        self.assertTrue(any("深圳广电" in keyword for keyword in all_keywords))
        self.assertTrue(any("第一现场" in keyword for keyword in all_keywords))

    async def test_multi_seed_ai_only_first_seed_gets_gap_fill(self):
        """模型若只扩第一个种子，后处理须回填其余种子。"""

        def _first_seed_only_payload() -> str:
            dimensions = []
            for dimension in DIMENSIONS:
                dimensions.append(
                    {
                        "key": dimension["key"],
                        "items": [
                            {
                                "keyword": f"深圳广电{dimension['name']}选题{index}",
                                "recommendation_score": 70 + index,
                                "business_score": 60 + index,
                                "reason": "仅覆盖第一种子",
                            }
                            for index in range(1, 9)
                        ],
                    }
                )
            return json.dumps({"dimensions": dimensions}, ensure_ascii=False)

        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(return_value=_first_seed_only_payload()),
        ):
            payload = await expand_keywords(["深圳广电", "第一现场客户端"])

        semantic = next(d for d in payload["dimensions"] if d["key"] == "semantic")
        semantic_keywords = [item["keyword"] for item in semantic["items"]]
        self.assertTrue(any("深圳广电" in keyword for keyword in semantic_keywords))
        self.assertTrue(any("第一现场" in keyword for keyword in semantic_keywords))

    async def test_media_seed_uses_content_media_profile(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["广电栏目 GEO"])

        self.assertEqual(payload["profile"]["name"], "内容媒体")
        question_keywords = [
            item["keyword"] for item in next(d for d in payload["dimensions"] if d["key"] == "question")["items"]
        ]
        self.assertTrue(any("如何" in kw or "怎么" in kw for kw in question_keywords))

    def test_low_quality_keyword_filter_rejects_empty_stacking(self):
        self.assertTrue(_is_low_quality_keyword("GEO平台", "GEO", "semantic"))
        self.assertTrue(_is_low_quality_keyword("GEO优化", "GEO优化", "scenario"))
        self.assertTrue(_is_low_quality_keyword("品牌官网 DJI Mini 5 Pro", "DJI Mini 5 Pro", "scenario"))
        self.assertTrue(_is_low_quality_keyword("深圳广电;第一现场;党媒栏目", "深圳广电;第一现场;党媒", "semantic"))
        self.assertFalse(_is_low_quality_keyword("如何开始做GEO优化", "GEO优化", "question"))
        self.assertFalse(_is_low_quality_keyword("旅行航拍选 DJI Mini 5 Pro", "DJI Mini 5 Pro", "scenario"))

    def test_normalize_seeds_splits_semicolon_blob(self):
        self.assertEqual(
            normalize_seeds(["深圳广电;第一现场;党媒"]),
            ["深圳广电", "第一现场", "党媒"],
        )
        self.assertEqual(
            normalize_seeds(["深圳广电", "第一现场;党媒"]),
            ["深圳广电", "第一现场", "党媒"],
        )

    def test_seed_role_hints_and_multi_seed_prompt_addendum(self):
        hints = _infer_seed_role_hints(["深圳广电", "第一现场客户端", "党媒"])
        by_seed = {row["seed"]: row["hint_role"] for row in hints}
        self.assertEqual(by_seed["深圳广电"], "organization")
        self.assertEqual(by_seed["第一现场客户端"], "product_or_column")
        self.assertEqual(by_seed["党媒"], "topic_or_attribute")
        composed = _compose_expansion_system_prompt("基础提示词", ["深圳广电", "党媒"])
        self.assertIn("基础提示词", composed)
        self.assertIn("seed_map", composed)
        self.assertIn("多种子", composed)

    def test_default_keyword_prompt_has_title_gate_and_anti_stuffing(self):
        from app.services.runtime_settings import (
            DEFAULT_KEYWORD_EXPANSION_CONFIG,
            MULTI_SEED_METHOD_ADDENDUM,
        )

        system = DEFAULT_KEYWORD_EXPANSION_CONFIG["system_prompt"]
        self.assertIn("标题", system)
        self.assertIn("Keyword Stuffing", system)
        self.assertIn("Statistics", system)
        self.assertIn("标题第一关", MULTI_SEED_METHOD_ADDENDUM)
        self.assertIn("别名勿交叉", MULTI_SEED_METHOD_ADDENDUM)

    def test_dji_alias_seeds_skip_media_cross_phrases(self):
        self.assertTrue(_seeds_are_near_duplicates("DJI Mini 5 Pro", "大疆 Mini 5 Pro"))
        self.assertTrue(_seeds_are_near_duplicates("DJI Mini 5 Pro", "Mini 5 Pro 续航"))
        self.assertFalse(_seeds_are_near_duplicates("深圳广电", "第一现场"))

        profile = _infer_keyword_profile(["DJI Mini 5 Pro", "大疆 Mini 5 Pro", "Mini 5 Pro 续航"])
        self.assertEqual(profile["key"], "consumer_electronics")
        for dim in DIMENSIONS:
            crossed = _cross_seed_items(
                ["DJI Mini 5 Pro", "大疆 Mini 5 Pro", "Mini 5 Pro 续航"],
                profile,
                dim["key"],
            )
            self.assertEqual(crossed, [], msg=f"dimension {dim['key']} should skip alias cross")

        hints = _infer_seed_role_hints(["DJI Mini 5 Pro", "大疆 Mini 5 Pro", "Mini 5 Pro 续航"])
        by_seed = {row["seed"]: row for row in hints}
        self.assertEqual(by_seed["大疆 Mini 5 Pro"].get("alias_group"), by_seed["DJI Mini 5 Pro"].get("alias_group"))
        self.assertIn(by_seed["大疆 Mini 5 Pro"]["hint_role"], {"alias", "other", "aspect"})
        # 别名共现一律过滤
        from app.services.keyword_expansion import _is_alias_cross_nonsense

        self.assertTrue(
            _is_alias_cross_nonsense(
                "DJI Mini 5 Pro怎么报道大疆 Mini 5 Pro",
                ["DJI Mini 5 Pro", "大疆 Mini 5 Pro"],
            )
        )
        self.assertTrue(
            _is_alias_cross_nonsense(
                "DJI Mini 5 Pro大疆 Mini 5 Pro",
                ["DJI Mini 5 Pro", "大疆 Mini 5 Pro"],
            )
        )

    async def test_dji_multi_seed_fallback_not_worse_than_natural(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(
                ["DJI Mini 5 Pro", "大疆 Mini 5 Pro", "Mini 5 Pro 续航"]
            )

        all_keywords = [
            item["keyword"]
            for dimension in payload["dimensions"]
            for item in dimension["items"]
        ]
        joined = "\n".join(all_keywords)
        self.assertNotIn("怎么报道", joined)
        self.assertNotIn("联动合作", joined)
        self.assertNotIn("旗下", joined)
        self.assertTrue(any("旅行" in kw or "怎么" in kw or "续航" in kw for kw in all_keywords))

    async def test_multi_seed_fallback_includes_cross_phrases(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["深圳广电;第一现场;党媒"])

        self.assertEqual(payload["seeds"], ["深圳广电", "第一现场", "党媒"])
        all_keywords = [
            item["keyword"]
            for dimension in payload["dimensions"]
            for item in dimension["items"]
        ]
        self.assertFalse(any(";" in keyword or "；" in keyword for keyword in all_keywords))
        self.assertTrue(any("第一现场" in keyword for keyword in all_keywords))
        self.assertTrue(
            any(("与" in keyword or "的" in keyword) and "深圳广电" in keyword for keyword in all_keywords)
        )

    async def test_dji_seed_uses_consumer_electronics_and_natural_scenarios(self):
        with patch(
            "app.services.keyword_expansion.ai_client.complete",
            new=AsyncMock(side_effect=RuntimeError("gateway unavailable")),
        ):
            payload = await expand_keywords(["DJI Mini 5 Pro"])

        self.assertEqual(payload["profile"]["name"], "消费电子")
        scenario_keywords = [
            item["keyword"] for item in next(d for d in payload["dimensions"] if d["key"] == "scenario")["items"]
        ]
        self.assertTrue(any("旅行" in kw or "怎么" in kw or "第一次" in kw for kw in scenario_keywords))
        self.assertFalse(any(kw.startswith("品牌官网 ") or kw.startswith("市场部 ") for kw in scenario_keywords))
        self.assertFalse(any("内容团队做" in kw for kw in scenario_keywords))


class KeywordExpansionApiTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_url, cls.database_name = resolve_test_database(
            default_database_url=settings.DATABASE_URL,
            configured_database_name=os.environ.get("POSTGRES_DB"),
            explicit_test_database_url=os.environ.get("TEST_DATABASE_URL"),
        )

    async def asyncSetUp(self):
        await verify_test_database_engine(engine, self.database_url, self.database_name)
        await self._reset_usage_policy()
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self._reset_usage_policy()
        await engine.dispose()

    async def _reset_usage_policy(self):
        async with async_session() as db:
            await db.execute(delete(Setting).where(Setting.key == "api_usage_policy"))
            await db.commit()
        await invalidate_runtime_settings_cache()

    async def test_keywords_expand_endpoint_returns_structured_response(self):
        with (
            patch(
                "app.api.routes.keywords.resolve_ai_access",
                new=AsyncMock(
                    return_value=SimpleNamespace(provider_override=None, reservation_id=None)
                ),
            ),
            patch(
                "app.api.routes.keywords.record_ai_usage",
                new=AsyncMock(),
            ),
            patch(
                "app.services.keyword_expansion.ai_client.complete",
                new=AsyncMock(return_value=_mock_ai_payload()),
            ),
        ):
            response = await self.client.post(
                "/api/keywords/expand",
                json={"seeds": ["GEO优化", "企业AI"]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["seeds"], ["GEO优化", "企业AI"])
        self.assertIn("profile", payload)
        self.assertEqual(len(payload["dimensions"]), 8)
        self.assertIn("summary", payload)

    async def test_keywords_expand_endpoint_rejects_blank_keywords(self):
        with patch(
            "app.api.routes.keywords.resolve_ai_access",
            new=AsyncMock(
                return_value=SimpleNamespace(provider_override=None, reservation_id=None)
            ),
        ):
            response = await self.client.post(
                "/api/keywords/expand",
                json={"seeds": ["   ", ""]},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("请至少输入一个关键词", response.text)
