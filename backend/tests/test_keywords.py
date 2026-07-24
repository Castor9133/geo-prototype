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
    _is_low_quality_keyword,
    expand_keywords,
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
        self.assertEqual(len(payload["dimensions"][0]["items"]), 8)
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
        self.assertFalse(_is_low_quality_keyword("如何开始做GEO优化", "GEO优化", "question"))


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
