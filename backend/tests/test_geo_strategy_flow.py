"""策略全流程离线测试：环间交付物 / 闸门 / 提示词（不测白号观测采样）。"""
from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.geo_strategy import GeoStrategy  # noqa: E402
from app.services.content_engine_utils import CHINA_PROMPTS, soften_markdown_prose  # noqa: E402
from app.services.geo_strategy_svc import (  # noqa: E402
    handoff_checklist,
    validate_six_tuple,
)


def _strategy(**kwargs) -> GeoStrategy:
    defaults = dict(
        id=uuid.uuid4(),
        title="第一现场栏目认知·豆包",
        platform="doubao",
        question_class="第一现场是什么栏目",
        content_orientation="深文+FAQ",
        query_variants=[
            "第一现场是什么栏目",
            "第一现场主要报道什么",
            "哪里看第一现场官方内容",
        ],
        channel_matrix={"site_required": True, "media_types": ["wechat"]},
        success_signal={"mode": "mention_top10", "top_n": 10},
        knowledge_document_ids=[str(uuid.uuid4())],
        knowledge_tag_pack={"site_id": "diyixianchang", "theme": "栏目认知"},
        status="draft",
        version=1,
        created_by=uuid.uuid4(),
    )
    defaults.update(kwargs)
    return GeoStrategy(**defaults)


class HandoffChecklistTests(unittest.TestCase):
    def test_ready_for_approve_needs_diag_and_baseline(self):
        s = _strategy()
        c = handoff_checklist(s)
        self.assertFalse(c["ready_for_approve"])
        self.assertTrue(c["obs_white_hat_deferred"])

        s.diagnostic_report_id = uuid.uuid4()
        c = handoff_checklist(s)
        self.assertFalse(c["ready_for_approve"])

        s.baseline_snapshot_id = uuid.uuid4()
        c = handoff_checklist(s)
        self.assertTrue(c["ready_for_approve"])
        keys = {i["key"]: i["ok"] for i in c["items"]}
        self.assertTrue(keys["diagnostic"])
        self.assertTrue(keys["baseline"])
        self.assertFalse(keys["deployed"])

    def test_deploy_and_verdict_flags(self):
        s = _strategy(
            status="deployed",
            diagnostic_report_id=uuid.uuid4(),
            baseline_snapshot_id=uuid.uuid4(),
            site_url="https://example.local/diyixianchang",
            media_url="https://mp.weixin.qq.com/s/demo",
            media_channel_type="wechat",
        )
        from datetime import datetime

        s.deployed_at = datetime.utcnow()
        c = handoff_checklist(s, task_summary={"all_ready": True, "total": 2, "ready_count": 2})
        self.assertTrue(c["ready_for_deploy"])
        keys = {i["key"]: i["ok"] for i in c["items"]}
        self.assertTrue(keys["tasks_ready"])
        self.assertTrue(keys["deployed"])
        self.assertFalse(keys["after"])
        self.assertFalse(keys["verdict"])


class SixTupleAndApproveGateTests(unittest.TestCase):
    def test_executable_six_tuple(self):
        s = _strategy()
        validate_six_tuple(s, for_executable=True)

    def test_flow_gates_documented_order(self):
        """模拟①→⑥状态推进（跳过白号采样，仅检查交付物字段）。"""
        editor = uuid.uuid4()
        reviewer = uuid.uuid4()
        s = _strategy(created_by=editor, status="draft")
        # ①
        s.diagnostic_report_id = uuid.uuid4()
        # ② pending baseline（不采样）
        s.baseline_snapshot_id = uuid.uuid4()
        s.meta = {"baseline_pending": True, "baseline_note": "白号另测"}
        # ③ submit/approve 前置
        self.assertTrue(handoff_checklist(s)["ready_for_approve"])
        s.status = "pending_review"
        s.status = "executable"
        s.approved_by = reviewer
        self.assertNotEqual(s.created_by, s.approved_by)
        # ④ knowledge already on strategy
        validate_six_tuple(s, for_executable=True)
        # ⑤ tasks ready summary
        ts = {"all_ready": True, "total": 2, "ready_count": 2}
        # ⑥ deploy
        s.site_url = "https://example.local/diyixianchang/a"
        s.media_channel_type = "wechat"
        s.media_url = "https://mp.weixin.qq.com/s/x"
        from datetime import datetime

        s.deployed_at = datetime.utcnow()
        s.status = "deployed"
        c = handoff_checklist(s, task_summary=ts)
        self.assertTrue(c["items"][5]["ok"])  # deployed
        # ⑦⑧ 白号观测/判定：本套测试故意不执行采样，只挂 after 占位与强制沉淀路径字段
        s.after_snapshot_id = uuid.uuid4()
        s.meta["after_pending"] = True
        s.force_status = "pending_business"
        s.force_reason = "冒烟：无白号，走强制沉淀闸门字段完整性"
        s.force_initiated_by = reviewer
        s.force_business_confirmed_by = uuid.uuid4()
        s.force_status = "pending_admin"
        self.assertEqual(s.force_status, "pending_admin")
        self.assertTrue(s.after_snapshot_id)


class PromptAndPilotDataTests(unittest.TestCase):
    def test_china_prompts_geo_constraints(self):
        self.assertGreaterEqual(len(CHINA_PROMPTS), 5)
        for item in CHINA_PROMPTS:
            body = item["body"]
            self.assertIn("{{Knowledge}}", body)
            self.assertTrue(
                "禁止" in body or "不得" in body or "勿" in body,
                msg=f"prompt missing guardrails: {item.get('title')}",
            )

    def test_soften_keeps_readable_prose(self):
        soft = soften_markdown_prose("## 结论\n\n第一现场是**官方栏目**。")
        self.assertIn("结论", soft)
        self.assertIn("官方栏目", soft)
        self.assertNotIn("**", soft)

    def test_dangqun_sample_ingest_shape(self):
        root = Path(__file__).resolve().parents[2]
        sample = root / "docs" / "pilot-demo" / "dangqun-geo-kb" / "sample-ingest.json"
        self.assertTrue(sample.is_file(), sample)
        data = json.loads(sample.read_text(encoding="utf-8"))
        self.assertEqual(data["tier"], "L1")
        self.assertIn("site_id", data["tags"])
        self.assertIn("task_bajua", data["tags"])
        self.assertIn("doc_type", data["tags"])
        self.assertTrue(data["body"].strip())
        self.assertTrue(data.get("external_approved"))

    def test_tag_contract_exists(self):
        root = Path(__file__).resolve().parents[2]
        contract = root / "docs" / "pilot-demo" / "dangqun-geo-kb" / "TAG_CONTRACT.md"
        self.assertTrue(contract.is_file())
        text = contract.read_text(encoding="utf-8")
        self.assertIn("site_id", text)
        self.assertIn("task_bajua", text)


class CitationRankLogicTests(unittest.TestCase):
    def test_mention_top10_helper_via_sample_shape(self):
        """不跑浏览器：只验证判定辅助逻辑对 citations 形状的要求。"""
        from types import SimpleNamespace

        from app.services.geo_strategy_svc import _citation_rank_ok

        sm = SimpleNamespace(
            mention=True,
            ok=True,
            citations=[{"url": "https://example.local/a", "rank": 3}],
            owned_citation=False,
            strong_adopted=False,
        )
        self.assertTrue(_citation_rank_ok(sm, top_n=10))
        sm2 = SimpleNamespace(
            mention=True,
            ok=True,
            citations=[],
            owned_citation=False,
            strong_adopted=False,
        )
        self.assertFalse(_citation_rank_ok(sm2, top_n=10))


if __name__ == "__main__":
    unittest.main()
