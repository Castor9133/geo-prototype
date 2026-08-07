"""GeoLook 借鉴：演示开关、CSV、诊断分型、写稿体检。"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-32chars!!")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-32chars!!!")
os.environ.setdefault("SETTINGS_ENCRYPTION_KEY", "test-settings-enc-key-32chars!!!!!")


class DemoMetricsConfigTests(unittest.TestCase):
    def test_production_rejects_demo_metrics(self):
        from app.core.config import Settings

        s = Settings(
            DEBUG=False,
            SECRET_KEY="a" * 32,
            JWT_SECRET="b" * 32,
            SETTINGS_ENCRYPTION_KEY="c" * 32,
            PUBLIC_BASE_URL="https://app.example.com",
            POSTGRES_PASSWORD="strong-postgres-password-1",
            GEORANK_ALLOW_ANONYMOUS_AI=False,
            GEORANK_DEMO_METRICS=True,
        )
        with self.assertRaises(RuntimeError) as ctx:
            s.validate_production_security()
        self.assertIn("GEORANK_DEMO_METRICS", str(ctx.exception))


class DiagnosisAndCsvTests(unittest.TestCase):
    def test_infer_diagnosis_priority(self):
        from app.services.real_obs import infer_diagnosis_type

        self.assertEqual(
            infer_diagnosis_type(
                mention=False,
                competitor_mention=False,
                owned_citation=False,
                answer_text="这款别买，全是坑",
            ),
            "suspected_negative",
        )
        self.assertEqual(
            infer_diagnosis_type(
                mention=False,
                competitor_mention=True,
                owned_citation=False,
                answer_text="竞品很好",
            ),
            "competitor_dominated",
        )
        self.assertEqual(
            infer_diagnosis_type(
                mention=False,
                competitor_mention=False,
                owned_citation=False,
                answer_text="没有相关品牌",
            ),
            "absent",
        )
        self.assertEqual(
            infer_diagnosis_type(
                mention=True,
                competitor_mention=False,
                owned_citation=False,
                answer_text="本品不错",
                raw_meta={"citation_rank": 15},
            ),
            "low_ranked",
        )
        self.assertIsNone(
            infer_diagnosis_type(
                mention=True,
                competitor_mention=False,
                owned_citation=True,
                answer_text="本品官网有参数",
                citations=[{"rank": 2, "url": "https://example.com"}],
            )
        )

    def test_sample_sheet_roundtrip(self):
        from types import SimpleNamespace

        from app.services.real_obs import build_sample_sheet_csv, parse_sample_sheet_csv

        snap = SimpleNamespace(
            platforms=["doubao"],
            questions=[{"id": "bq1", "text": "本品怎么样？"}, {"id": "bq2", "text": "怎么选？"}],
        )
        csv_text = build_sample_sheet_csv(snap, platform="doubao")
        self.assertIn("question_id", csv_text)
        filled = (
            "question_id,question_text,platform,attempt,mention,competitor_mention,"
            "owned_citation,citation_rank,diagnosis_type,answer_text,ok,notes\n"
            "bq1,本品怎么样？,doubao,1,1,0,1,3,,提到了,1,\n"
        )
        items = parse_sample_sheet_csv(filled)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["question_id"], "bq1")
        self.assertEqual(items[0]["platform"], "doubao")
        self.assertTrue(items[0]["raw_meta"]["sheet_mention"])


class DraftLintTests(unittest.TestCase):
    def test_blocks_absolute_and_unsourced_percent(self):
        from app.services.draft_lint import lint_draft_text

        r = lint_draft_text(
            "我们绝对第一，转化提升 88%，据内部数据全网最好。",
            fact_cards=[{"claim": "续航约 2 小时"}],
        )
        self.assertTrue(r["blocking"])
        codes = {i["code"] for i in r["issues"]}
        self.assertTrue(codes & {"absolute_claim", "unsourced_percent", "fabricate_hint"})

    def test_allows_percent_in_fact_card(self):
        from app.services.draft_lint import lint_draft_text

        r = lint_draft_text(
            "官方口径：能效提升 12%。",
            fact_cards=[{"claim": "能效提升 12%"}],
        )
        self.assertFalse(r["blocking"])


class HandoffHardGateTests(unittest.TestCase):
    def test_ready_for_approve_requires_samples_when_demo_off(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from app.services import geo_strategy_svc as svc

        s = SimpleNamespace(
            diagnostic_report_id="x",
            baseline_snapshot_id="y",
            after_snapshot_id=None,
            status="pending_review",
            verdict=None,
            site_url=None,
            media_url=None,
            deployed_at=None,
            knowledge_base_id=None,
            query_variants=["a", "b", "c"],
            meta={"baseline_sample_count": 1, "after_sample_count": 0},
        )
        with patch.object(svc, "demo_metrics_enabled", return_value=False):
            with patch.object(svc, "is_query_pack_confirmed", return_value=False):
                with patch.object(svc, "is_knowledge_bound", return_value=False):
                    cl = svc.handoff_checklist(s, task_summary={})
        self.assertFalse(cl["ready_for_approve"])
        self.assertFalse(cl["demo_metrics"])

        with patch.object(svc, "demo_metrics_enabled", return_value=True):
            with patch.object(svc, "is_query_pack_confirmed", return_value=False):
                with patch.object(svc, "is_knowledge_bound", return_value=False):
                    cl2 = svc.handoff_checklist(s, task_summary={})
        self.assertTrue(cl2["ready_for_approve"])


class CitationRankingTests(unittest.TestCase):
    def test_build_citation_rankings_counts_articles_and_domains(self):
        from app.services.real_obs import build_citation_rankings

        samples = [
            {
                "ok": True,
                "platform": "doubao",
                "citations": [
                    {
                        "url": "https://lemonbox.com.cn/a",
                        "title": "过敏体质能吃多维维生素吗",
                        "domain": "lemonbox.com.cn",
                    }
                ],
            },
            {
                "ok": True,
                "platform": "yuanbao",
                "citations": [
                    {
                        "url": "https://lemonbox.com.cn/a",
                        "title": "过敏体质能吃多维维生素吗",
                        "domain": "lemonbox.com.cn",
                    }
                ],
            },
            {
                "ok": True,
                "platform": "deepseek",
                "citations": [
                    {
                        "url": "https://foodisgood.com/x",
                        "title": "Is it Low Histamine?",
                        "domain": "foodisgood.com",
                    },
                    {
                        "url": "https://foodisgood.com/x",
                        "title": "Is it Low Histamine?",
                        "domain": "foodisgood.com",
                    },
                ],
            },
        ]
        out = build_citation_rankings(samples)
        self.assertEqual(out["article_total"], 2)
        self.assertEqual(out["domain_total"], 2)
        self.assertEqual(out["articles"][0]["count"], 2)
        self.assertEqual(out["domains"][0]["count"], 2)
        self.assertIn(out["domains"][0]["domain"], {"foodisgood.com", "lemonbox.com.cn"})


if __name__ == "__main__":
    unittest.main()
