"""策略六元组与下一步闸门（无 DB）"""
from __future__ import annotations

import unittest
import uuid

from app.models.geo_strategy import GeoStrategy
from app.services.geo_strategy_svc import (
    compute_next_action,
    is_query_pack_confirmed,
    validate_six_tuple,
)


def _base(**kwargs) -> GeoStrategy:
    data = dict(
        id=uuid.uuid4(),
        title="t",
        platform="doubao",
        question_class="第一现场是什么",
        content_orientation="深文+FAQ",
        query_variants=["a", "b", "c"],
        channel_matrix={"site_required": True, "media_types": ["wechat"]},
        success_signal={"mode": "mention_top10", "top_n": 10},
        knowledge_document_ids=[],
        knowledge_tag_pack={},
        status="draft",
        meta={},
    )
    data.update(kwargs)
    return GeoStrategy(**data)


class GeoStrategyValidateTests(unittest.TestCase):
    def test_executable_no_longer_requires_docs_or_final_queries(self):
        s = _base(query_variants=["a", "b"], knowledge_document_ids=[], knowledge_tag_pack={})
        # 批准可开工：只要渠道/取向等基本项
        validate_six_tuple(s, for_executable=True)

    def test_executable_still_requires_media_types(self):
        s = _base(channel_matrix={"site_required": True, "media_types": []})
        with self.assertRaises(ValueError):
            validate_six_tuple(s, for_executable=True)


class NextActionAndExpandTests(unittest.TestCase):
    def test_query_pack_confirmed_needs_flag_and_three(self):
        s = _base(meta={"query_pack_confirmed": True}, query_variants=["a", "b"])
        self.assertFalse(is_query_pack_confirmed(s))
        s.query_variants = ["a", "b", "c"]
        self.assertTrue(is_query_pack_confirmed(s))

    def test_next_action_order(self):
        s = _base(diagnostic_report_id=None)
        self.assertEqual(compute_next_action(s)["key"], "diagnostic")

        s.diagnostic_report_id = uuid.uuid4()
        self.assertEqual(compute_next_action(s)["key"], "baseline")

        s.baseline_snapshot_id = uuid.uuid4()
        self.assertEqual(compute_next_action(s)["key"], "craft")  # draft → 送审

        s.status = "executable"
        self.assertEqual(compute_next_action(s)["key"], "expand")

        s.meta = {"query_pack_confirmed": True}
        self.assertEqual(compute_next_action(s)["key"], "knowledge")

        s.knowledge_document_ids = [str(uuid.uuid4())]
        s.knowledge_tag_pack = {"site_id": "x", "theme": "y"}
        self.assertEqual(compute_next_action(s, task_summary={"all_ready": False})["key"], "write")


if __name__ == "__main__":
    unittest.main()
