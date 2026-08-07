"""文章管理：序列化、引用排行与本库标题对齐。"""
from __future__ import annotations

import os
import unittest
import uuid
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-32chars!!")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-32chars!!!")
os.environ.setdefault("SETTINGS_ENCRYPTION_KEY", "test-settings-enc-key-32chars!!!!!")


class GeoArticlesUnitTests(unittest.TestCase):
    def test_serialize_article_includes_write_href(self):
        from app.services.geo_articles import serialize_article

        sid = uuid.uuid4()
        art = SimpleNamespace(
            id=uuid.uuid4(),
            title="测试文章",
            body="正文",
            source_type="ai",
            lifecycle_status="draft",
            origin="platform",
            published_url=None,
            channel=None,
            strategy_id=sid,
            knowledge_base_id=None,
            content_task_id=None,
            owner_user_id=uuid.uuid4(),
            citation_count_30d=0,
            meta={},
            created_at=None,
            updated_at=None,
        )
        out = serialize_article(art)
        self.assertEqual(out["title"], "测试文章")
        self.assertIn(str(sid), out["write_href"])

    def test_build_rankings_owned_library_title_preferred(self):
        from app.services import real_obs as real_obs_svc

        samples = [
            {
                "ok": True,
                "platform": "doubao",
                "citations": [
                    {
                        "url": "https://example.com/col/faq",
                        "title": "外站标题",
                        "domain": "example.com",
                    }
                ],
            },
            {
                "ok": True,
                "platform": "yuanbao",
                "citations": [
                    {
                        "url": "https://example.com/col/faq",
                        "title": "外站标题",
                        "domain": "example.com",
                    }
                ],
            },
        ]
        rankings = real_obs_svc.build_citation_rankings(samples)
        self.assertEqual(rankings["articles"][0]["count"], 2)
        self.assertEqual(rankings["articles"][0]["url"], "https://example.com/col/faq")


if __name__ == "__main__":
    unittest.main()
