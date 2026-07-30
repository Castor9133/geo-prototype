"""SEO 四模块：从既有诊断分析派生「目的 / 结果 / 影响 / 建议」.

文案面向任意站点运营（媒体、品牌、政务、电商等），禁止绑定某一垂类示例。
"""
from __future__ import annotations

from typing import Any

# 技术字段 → 运营可读名称
_META_LABELS: dict[str, str] = {
    "title": "页面标题（title）",
    "meta_description": "页面摘要（description）",
    "canonical": "规范网址（canonical）",
    "viewport": "移动端适配声明（viewport）",
    "robots": "抓取许可声明（robots）",
    "html_lang": "页面语言（html lang）",
    "favicon": "站点图标（favicon）",
    "og_title": "分享标题（og:title）",
    "og_description": "分享摘要（og:description）",
    "og_image": "分享配图（og:image）",
    "og_type": "分享类型（og:type）",
    "og_locale": "分享语言区（og:locale）",
    "twitter_card": "社交卡片（Twitter Card）",
}

# 缺字段 → 对运营可见的影响（不是「AI 引用率」承诺）
_META_IMPACTS: dict[str, str] = {
    "title": "结果卡片和摘要条常抓不到清晰标题，用户点进来前就不知道本页讲什么。",
    "meta_description": "搜索/答案侧缺少一句话介绍，列表里看起来「没说明」，点击意愿会掉。",
    "canonical": "同一内容多链接时引擎不知道以哪版为准，曝光和信任信号会被拆散。",
    "viewport": "手机端版式可能错乱，移动用户打开体验差，影响「能不能顺利读完」的第一印象。",
    "robots": "说不清页面是否允许收录；一旦误设禁止抓取，整页会从结果里消失。",
    "html_lang": "引擎可能按错语言理解内容，摘要和推荐容易串到错误地区或错误主体语境。",
    "favicon": "站点辨识变弱，多标签页/结果侧不易一眼认出是你们的站。",
    "og_title": "转发到社交/IM 时标题空白或乱抓，传播素材不可控。",
    "og_description": "分享卡片缺介绍文案，转发效果弱。",
    "og_image": "分享无配图，信息流里不显眼，活动/专题页传播打折。",
    "og_type": "分享平台难判断内容类型，卡片展示不稳定。",
    "og_locale": "跨语言/跨区分享时语言信号不准，易推错受众。",
    "twitter_card": "部分社媒渠道卡片不完整，转发展示弱。",
}

_SCHEMA_LABELS: dict[str, str] = {
    "Organization": "机构/主体身份（Organization）",
    "WebSite": "站点实体（WebSite）",
    "FAQPage": "问答页标记（FAQPage）",
    "Article": "文章实体（Article）",
    "Product": "商品/服务实体（Product）",
    "BreadcrumbList": "面包屑导航（BreadcrumbList）",
    "HowTo": "步骤说明（HowTo）",
}

_SCHEMA_IMPACTS: dict[str, str] = {
    "Organization": (
        "引擎难以确认「这是谁的官网/哪个机构」；同名主体多时，"
        "更容易被认错来源，被当作权威出处的机会变少。"
    ),
    "WebSite": "站点整体身份不清晰，搜索/答案侧更难把多页内容归到同一机构名下。",
    "FAQPage": (
        "用户常问的时间、入口、规则、怎么办理类问题，不易被稳定摘成「问答块」；"
        "运营写了 FAQ 文案，引擎也可能当普通段落略过。"
    ),
    "Article": "资讯/稿件页缺少「这是一篇正式文章」的信号，发布时间与来源权威更难被认。",
    "Product": "服务/商品要点难被当成结构化信息，选型或对比类问题里更难被点名。",
    "BreadcrumbList": "栏目层级不清楚，引擎更难理解本页在站点地图里的位置。",
    "HowTo": "步骤类内容（报名、办理、使用说明）不易被拆成可执行指引。",
}


def _label_meta(key: str) -> str:
    return _META_LABELS.get(key, key)


def _label_schema(key: str) -> str:
    return _SCHEMA_LABELS.get(key, key)


def _join_impacts(keys: list[str], table: dict[str, str], label_fn, *, limit: int = 3) -> str:
    parts: list[str] = []
    for key in keys[:limit]:
        impact = table.get(key)
        if impact:
            parts.append(f"「{label_fn(key)}」：{impact}")
    return " ".join(parts)


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
    internal = citation.get("internal_link_count")

    missing_meta_labels = [_label_meta(k) for k in missing_meta]
    missing_schema_labels = [_label_schema(k) for k in missing_schema]

    # —— 可抓取与可达 ——
    if missing_meta:
        crawl_impact = (
            "缺这些基础标签，不等于网站打不开，但等于「引擎打开了也不知道怎么介绍你们」。"
            + _join_impacts(missing_meta, _META_IMPACTS, _label_meta)
        )
        crawl_advice = (
            f"请技术/建站同事补齐：{'、'.join(missing_meta_labels)}。"
            "验收：用无痕窗口打开页面源码，能看到对应标签；"
            "运营侧再核对标题和摘要是否写清「本页主题 / 受众 / 一句话价值」。"
        )
        crawl_result = (
            f"基础摘要就绪分 {round(meta_score)}/100。"
            f" 仍缺：{'、'.join(missing_meta_labels)}。"
            " 引擎能打开页面，但摘要与语言/收录信号不完整。"
        )
    else:
        crawl_impact = (
            "当前基础抓取信号较完整：引擎一般能读到标题、摘要与语言环境，"
            "误拦收录的风险较低。仍需定期检查 robots 未被误改。"
        )
        crawl_advice = (
            "保持 title / description / OG 完整；发版前后抽查 robots，避免误设 noindex。"
            "运营侧继续用「主题 + 受众价值」写标题和摘要，方便被摘录。"
        )
        crawl_result = (
            f"基础摘要就绪分 {round(meta_score)}/100。标题、摘要、语言等基础信号较完整。"
        )

    # —— 可解析结构 ——
    structure_bits: list[str] = []
    if (h1 or 0) != 1:
        structure_bits.append(
            f"本页有 {h1 or 0} 个主标题（H1），主题不够「一眼一个重点」，"
            "引擎和用户都更难判断本页主讲什么。"
        )
    if (h2 or 0) < 2:
        structure_bits.append(
            "几乎没有二级标题（H2）：长文像一整块，用户问题对不上小节，"
            "答案引擎更难截取「某一问对应某一答」。"
        )
    if (faq or 0) < 1:
        structure_bits.append(
            "未见明显 FAQ 问答块：时间、入口、规则、怎么联系等常见问题缺少现成答句，"
            "运营要反复口头解释的内容，线上也难被直接引用。"
        )
    if missing_schema:
        structure_bits.append(
            _join_impacts(missing_schema, _SCHEMA_IMPACTS, _label_schema)
        )

    if structure_bits:
        structure_impact = " ".join(structure_bits[:4])
    else:
        structure_impact = (
            "结构化标记与标题层级基本可用；继续把小节写成用户会问的句子，"
            "并维护 FAQ，有利于被摘成问答块（就绪 ≠ 保证被引用）。"
        )

    if missing_schema or (h2 or 0) < 2 or (faq or 0) < 1 or (h1 or 0) != 1:
        structure_advice = (
            ("建议补结构化标记：" + "、".join(missing_schema_labels) + "。" if missing_schema else "")
            + "每页只留 1 个清晰 H1；把关键 H2 改成用户口吻的问句"
            "（如「怎么联系？」「开放/播出时间？」「核心结论是什么？」）；"
            "在页内增加 FAQ 区块并尽量挂 FAQPage。"
            "运营验收：任意一个高频咨询问题，能在页内找到对应小标题和一段可直接复制的短答。"
        ).strip()
    else:
        structure_advice = (
            "结构化标记与标题结构尚可；继续强化问句化 H2 与 FAQ，"
            "并把关键事实、规则、入口说明写成可独立摘录的短段。"
        )

    structure_result = (
        f"结构合成分 {structure_score}/100（实体标记 {round(schema_score)} · 正文结构 {round(content_score)}）。"
        f" 主标题 H1={h1 or 0} · 小节 H2={h2 or 0} · FAQ 样块={faq or 0}。"
        + (
            f" 建议补的实体类型：{'、'.join(missing_schema_labels)}。"
            if missing_schema
            else ""
        )
    )

    # —— 内链与发现 ——
    if (auth or 0) < 1:
        discovery_impact = (
            "权威外链偏少时，页面缺少「别人也认」的背书线索；"
            "这不等于 AI 引用率，但会让引擎更难判断你们内容是否值得采信。"
            "内链若也弱，栏目页、专题页、说明页等关键内容不易被连带发现。"
        )
        discovery_advice = (
            "运营：在正文中自然引用官方文件、权威媒体、合作机构等外链；"
            "用清晰锚文字把「栏目首页 / 专题 / 说明或帮助页」串成可点路径。"
            "验收：从首页或本页 2～3 次点击能到达上述关键内容。"
        )
    else:
        discovery_impact = (
            f"已有约 {auth} 条权威向线索、外链 {ext or 0} 条"
            + (f"、站内链 {internal}" if internal is not None else "")
            + "。发现与背书就绪较好；注意：这是「页面外链/内链就绪」，不是答案面板里的提及率。"
        )
        discovery_advice = (
            "维持权威外链密度；用内链把栏目、专题、说明/帮助等关键页串成可发现图谱，"
            "避免重要事实埋在孤立落地页里。"
        )

    discovery_result = (
        f"外链 {ext or 0} · 权威线索 {auth or 0}"
        + (f" · 站内链 {internal}" if internal is not None else "")
        + f"；发现/背书就绪分 {round(citation_score)}/100。"
    )

    # —— 性能与成本 ——
    wordish = int(content.get("word_count") or content.get("text_length") or 0)
    if wordish <= 0:
        wordish = int((h2 or 0) * 180 + (h1 or 0) * 40)
    perf_score = 88 if wordish < 2500 else (72 if wordish < 6000 else 55)
    if perf_score < 75:
        perf_impact = (
            "正文过长或结构过碎时，抓取和摘要要「读更多字才能捞到重点」；"
            "关键信息若埋在后半页，被摘进答案的机会会变差（此为成本代理，非实验室测速分）。"
        )
        perf_advice = (
            "压缩首屏空话与重复模块；把核心结论、入口、时间/规则写成靠前的短直答段。"
            "运营验收：滚动不超过一屏，应能看到一句可转发的核心结论。"
        )
    else:
        perf_impact = (
            "当前体量对抓取/摘要成本压力不大；若关键事实靠后或散落多处，"
            "仍可能被「读到了但摘不稳」。本模块是代理信号，不是 Lighthouse 实测。"
        )
        perf_advice = (
            "体量尚可；继续把核心结论、规则说明、联系/入口放在靠前、可独立摘录的段落，"
            "方便编辑、客服与对外口径复用同一套标准答法。"
        )
    perf_result = (
        f"正文体量代理约 {wordish or '未知'} 字；结构节点 H1={h1 or 0} / H2={h2 or 0}。"
        "（抓取成本代理，非真实性能实验室分。）"
    )

    return [
        {
            "id": "crawlability",
            "title": "可抓取与可达",
            "purpose": (
                "先确认搜索/答案引擎能打开页面，并读到「标题、摘要、语言、是否允许收录」"
                "这些给用户看的第一层介绍信息。"
            ),
            "score": round(meta_score),
            "result": crawl_result,
            "impact": crawl_impact,
            "advice": crawl_advice,
        },
        {
            "id": "parseable_structure",
            "title": "可解析结构",
            "purpose": (
                "确认机构/站点身份、标题层级和 FAQ 能否被稳定读成「实体 + 问答块」，"
                "方便对上用户真实会问的话。"
            ),
            "score": structure_score,
            "result": structure_result,
            "impact": structure_impact,
            "advice": structure_advice,
        },
        {
            "id": "internal_discovery",
            "title": "内链与发现",
            "purpose": (
                "确认栏目、专题、说明等关键内容页能被内链找到，"
                "并有权威外链作信任线索（就绪信号 ≠ AI 答案引用率）。"
            ),
            "score": round(citation_score),
            "result": discovery_result,
            "impact": discovery_impact,
            "advice": discovery_advice,
        },
        {
            "id": "performance_cost",
            "title": "性能与成本",
            "purpose": (
                "评估正文长短和结构是否让引擎「读得贵、摘得慢」；"
                "帮助运营把最重要的话放在更好被看见的位置。"
            ),
            "score": perf_score,
            "result": perf_result,
            "impact": perf_impact,
            "advice": perf_advice,
        },
    ]
