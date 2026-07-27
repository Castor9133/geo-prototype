import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.deps import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.services.trust_obs import classify_answer  # noqa: E402


class TrustObsClassifierTests(unittest.TestCase):
    def test_absent(self):
        result = classify_answer("今天天气不错。", entity_name="GEO 示范栏目")
        self.assertEqual(result["primary_label"], "absent")

    def test_mention(self):
        result = classify_answer(
            "GEO 示范栏目是一档面向智能化内容工程的演示栏目。",
            entity_name="GEO 示范栏目",
        )
        self.assertEqual(result["primary_label"], "mention")

    def test_citation_owned_domain(self):
        result = classify_answer(
            "可参考 GEO 示范栏目介绍：https://localhost/pilot-demo/geo-demo-column/",
            entity_name="GEO 示范栏目",
            owned_domains=["localhost"],
        )
        self.assertEqual(result["primary_label"], "citation")

    def test_co_mention(self):
        result = classify_answer(
            "GEO 示范栏目与竞品示范栏目都在做内容工程。",
            entity_name="GEO 示范栏目",
            competitors=["竞品示范栏目"],
        )
        self.assertEqual(result["primary_label"], "co_mention")

    def test_recommendation(self):
        result = classify_answer(
            "推荐关注 GEO 示范栏目以了解知识工程实践。",
            entity_name="GEO 示范栏目",
        )
        self.assertEqual(result["primary_label"], "recommendation")


class TrustObsApiAuthSmokeTests(unittest.TestCase):
    """API 鉴权烟测：管理端需登录；latest 允许匿名只读。"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Docker 环境 TRUSTED_HOSTS 通常不含 testserver，统一用 localhost
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://localhost")

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)
        self.loop.run_until_complete(self.client.aclose())
        self.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    def test_admin_runs_require_auth(self):
        response = self.run_async(self.client.get("/api/admin/trust-obs/runs"))
        self.assertEqual(response.status_code, 401, response.text)

    def test_admin_create_run_requires_auth(self):
        response = self.run_async(self.client.post("/api/admin/trust-obs/runs", json={"repeats": 1}))
        self.assertEqual(response.status_code, 401, response.text)

    def test_admin_probes_require_auth(self):
        response = self.run_async(self.client.get("/api/admin/trust-obs/probes"))
        self.assertEqual(response.status_code, 401, response.text)

    def test_non_admin_token_forbidden(self):
        async def fake_user():
            mock = MagicMock()
            mock.is_active = True
            mock.role = UserRole.USER
            mock.id = "00000000-0000-0000-0000-000000000099"
            return mock

        app.dependency_overrides[get_current_user] = fake_user
        try:
            response = self.run_async(self.client.get("/api/admin/trust-obs/runs"))
            self.assertEqual(response.status_code, 403, response.text)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_latest_allows_anonymous(self):
        response = self.run_async(self.client.get("/api/admin/trust-obs/runs/latest"))
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIn("badge", payload)
        self.assertIn("非网页抓取", payload.get("badge", ""))


if __name__ == "__main__":
    unittest.main()
