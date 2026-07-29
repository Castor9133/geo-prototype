"""SEO 四模块：从既有诊断分析派生「目的 / 结果 / 建议」."""
from __future__ import annotations

from typing import Any


def build_seo_modules(
    schema: dict[str, Any] | None,
    meta: dict[str, Any] | None,
    content: dict[str, Any] | None,
    citation: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    schema = schema or {}
    meta = meta or {}
    content = content or {}
    citation = citation or {}

    meta_score = float(meta.get("score") or 0)
    schema_score = float(schema.get("score") or 0)
    content_score = float(content.get("score") or 0)
    citation_score = float(citation.get("score") or 0)
    structure_score = round((schema_score * 0.55) + (content_score * 0.45))

    missing_meta = list(meta.get("missing") or [])[:4]
    missing_schema = list(schema.get("missing_recommended") or [])[:4]
    h1 = content.get("h1_count")
    h2 = content.get("h2_count")
    faq = content.get("faq_like_sections")
    ext = citation.get("external_link_count")
    auth = citation.get("authority_link_count")

    crawl_advice = (
        f"补齐：{'、'.join(missing_meta)}。"
        if missing_meta
        else "保持 title / description / OG 完整，并确认无 robots 误拦。"
    )
    structure_advice = (
        f"建议补 Schema：{'、'.join(missing_schema)}；关键 H2 改为用户问句，并补 FAQ 块。"
        if missing_schema
        else "Schema 覆盖尚可；继续强化问句化 H2 与 FAQPage。"
    )
    discovery_advice = (
        "增加权威外链与清晰内链锚点，让爬虫与答案引擎更容易发现关键事实页。"
        if (auth or 0) < 1
        else "维持权威外链密度，并用内链把产品规格 / 禁飞 / 对比页串成可发现图谱。"
    )
    # 性能：用正文体量与结构复杂度作代理（无 Lighthouse 时的演示友好信号）
    wordish = int(content.get("word_count") or content.get("text_length") or 0)
    if wordish <= 0:
        wordish = int((h2 or 0) * 180 + (h1 or 0) * 40)
    perf_score = 88 if wordish < 2500 else (72 if wordish < 6000 else 55)
    perf_result = (
        f"正文体量代理约 {wordish or '未知'} 字量级；结构节点 H1={h1 or 0} / H2={h2 or 0}。"
        "本模块为抓取成本代理，非真实 Lighthouse。"
    )
    perf_advice = (
        "控制首屏与正文冗余，优先可被摘录的短直答段落，降低模型上下文成本。"
        if perf_score < 75
        else "体量尚可；继续把关键事实放在靠前、可独立摘录的段落。"
    )

    return [
        {
            "id": "crawlability",
            "title": "可抓取与可达",
            "purpose": "确认搜索/答案引擎能打开页面并读到基础摘要信号（title、description、OG）。",
            "score": round(meta_score),
            "result": (
                f"Meta 就绪分 {round(meta_score)}。"
                + (f" 待补：{'、'.join(missing_meta)}。" if missing_meta else " 基础抓取信号较完整。")
            ),
            "advice": crawl_advice,
        },
        {
            "id": "parseable_structure",
            "title": "可解析结构",
            "purpose": "确认 Schema 与标题/FAQ 结构能被稳定解析为实体与问答块。",
            "score": structure_score,
            "result": (
                f"结构合成分 {structure_score}（Schema {round(schema_score)} · 内容 {round(content_score)}）。"
                f" H1={h1 or 0} · H2={h2 or 0} · FAQ 样块={faq or 0}。"
            ),
            "advice": structure_advice,
        },
        {
            "id": "internal_discovery",
            "title": "内链与发现",
            "purpose": "确认关键事实页能被内链发现，并有权威外链作背书就绪信号（≠ AI 引用率）。",
            "score": round(citation_score),
            "result": f"外链 {ext or 0} · 权威 {auth or 0}；发现/背书就绪分 {round(citation_score)}。",
            "advice": discovery_advice,
        },
        {
            "id": "performance_cost",
            "title": "性能与成本",
            "purpose": "评估页面体量与结构对抓取/摘要成本的影响（代理信号，非实测性能分）。",
            "score": perf_score,
            "result": perf_result,
            "advice": perf_advice,
        },
    ]
