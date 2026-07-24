import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


if __name__ == "__main__":
    unittest.main()
