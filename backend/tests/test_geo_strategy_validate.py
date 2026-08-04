"""策略六元组校验（无 DB）"""
from __future__ import annotations

import unittest
import uuid

from app.models.geo_strategy import GeoStrategy
from app.services.geo_strategy_svc import validate_six_tuple


class GeoStrategyValidateTests(unittest.TestCase):
    def test_executable_requires_docs_tags_and_three_queries(self):
        s = GeoStrategy(
            id=uuid.uuid4(),
            title="t",
            platform="doubao",
            question_class="第一现场是什么",
            content_orientation="深文+FAQ",
            query_variants=["a", "b"],
            channel_matrix={"site_required": True, "media_types": ["wechat"]},
            success_signal={"mode": "mention_top10", "top_n": 10},
            knowledge_document_ids=[],
            knowledge_tag_pack={},
        )
        with self.assertRaises(ValueError):
            validate_six_tuple(s, for_executable=True)

        s.knowledge_document_ids = [str(uuid.uuid4())]
        s.knowledge_tag_pack = {"site_id": "diyixianchang", "theme": "intro"}
        with self.assertRaises(ValueError):
            validate_six_tuple(s, for_executable=True)

        s.query_variants = ["a", "b", "c"]
        validate_six_tuple(s, for_executable=True)


if __name__ == "__main__":
    unittest.main()
