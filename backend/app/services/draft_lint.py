"""写稿红牌体检 — 对照事实卡与规则，拦瞎编/无来源数字等。"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_engine import ContentTask, KnowledgeDocument

# 绝对化空话（严重）
ABSOLUTE_PATTERNS = (
    re.compile(r"100\s*%"),
    re.compile(r"绝对(安全|可靠|第一|领先)"),
    re.compile(r"全网(第一|唯一|最好)"),
    re.compile(r"史上最"),
    re.compile(r"永远不会"),
)

# 疑似无来源的百分比/精确数字（警告或严重）
PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
NUMBER_CLAIM_RE = re.compile(r"(提升|增长|下降|超过|高达|降低)\s*(\d{1,4}(?:\.\d+)?)")

FABRICATE_HINTS = (
    "据内部数据",
    "未经证实",
    "据说",
    "有人说",
    "权威报告显示",  # 无具体来源时常为套话
)


def _fact_claim_blobs(fact_cards: list[Any]) -> list[str]:
    blobs: list[str] = []
    for card in fact_cards or []:
        if isinstance(card, str) and card.strip():
            blobs.append(card.strip())
            continue
        if not isinstance(card, dict):
            continue
        for key in ("claim", "citable_blurb", "evidence", "text", "title"):
            val = card.get(key)
            if isinstance(val, str) and val.strip():
                blobs.append(val.strip())
    return blobs


def lint_draft_text(
    body: str,
    *,
    fact_cards: list[Any] | None = None,
) -> dict[str, Any]:
    """
    返回 { ok, blocking, issues: [{severity, code, message, excerpt}] }.
    severity=error 计入 blocking。
    """
    text = (body or "").strip()
    issues: list[dict[str, Any]] = []
    if not text:
        return {
            "ok": False,
            "blocking": True,
            "issues": [{"severity": "error", "code": "empty", "message": "正文为空", "excerpt": ""}],
            "score": 0,
        }

    for pat in ABSOLUTE_PATTERNS:
        m = pat.search(text)
        if m:
            issues.append(
                {
                    "severity": "error",
                    "code": "absolute_claim",
                    "message": f"疑似绝对化表述：{m.group(0)}",
                    "excerpt": m.group(0),
                }
            )

    for hint in FABRICATE_HINTS:
        if hint in text:
            issues.append(
                {
                    "severity": "error",
                    "code": "fabricate_hint",
                    "message": f"疑似无依据套话：「{hint}」",
                    "excerpt": hint,
                }
            )

    claims = _fact_claim_blobs(fact_cards or [])
    claim_blob = "\n".join(claims).lower()

    for m in PERCENT_RE.finditer(text):
        num = m.group(0)
        # 事实卡里出现过同百分比则放过
        if claim_blob and num.replace(" ", "").lower() in claim_blob.replace(" ", ""):
            continue
        if claims:
            issues.append(
                {
                    "severity": "error",
                    "code": "unsourced_percent",
                    "message": f"百分比「{num}」未在事实卡中找到对应口径",
                    "excerpt": num,
                }
            )
        else:
            issues.append(
                {
                    "severity": "warn",
                    "code": "percent_no_fact_cards",
                    "message": f"出现百分比「{num}」但任务未挂事实卡，请人工核验",
                    "excerpt": num,
                }
            )

    for m in NUMBER_CLAIM_RE.finditer(text):
        excerpt = m.group(0)
        if claim_blob and m.group(2) in claim_blob:
            continue
        if claims:
            issues.append(
                {
                    "severity": "warn",
                    "code": "number_claim",
                    "message": f"量化表述「{excerpt}」建议对照事实卡",
                    "excerpt": excerpt,
                }
            )

    # 事实卡关键数字/短语：若正文完全不沾任何 claim 片段，警告（非红牌）
    if claims and len(text) > 80:
        hit = any(c[:12].lower() in text.lower() for c in claims if len(c) >= 4)
        if not hit:
            issues.append(
                {
                    "severity": "warn",
                    "code": "no_fact_overlap",
                    "message": "正文与事实卡主张重合很少，请确认是否偏离口径",
                    "excerpt": "",
                }
            )

    blocking = any(i["severity"] == "error" for i in issues)
    # 简单分：满分 100，每个 error -25，warn -8
    score = 100
    for i in issues:
        score -= 25 if i["severity"] == "error" else 8
    score = max(0, min(100, score))
    return {
        "ok": not blocking,
        "blocking": blocking,
        "issues": issues,
        "score": score,
        "fact_card_count": len(claims),
    }


async def collect_fact_cards_for_task(db: AsyncSession, task: ContentTask) -> list[Any]:
    cards: list[Any] = []
    if not task.knowledge_base_id:
        return cards
    docs = (
        await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == task.knowledge_base_id)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(40)
        )
    ).scalars().all()
    for d in docs:
        for c in d.fact_cards or []:
            cards.append(c)
    return cards


async def lint_task_draft(db: AsyncSession, task: ContentTask) -> dict[str, Any]:
    body = task.channel_draft_body or task.draft_body or task.template_draft_body or ""
    cards = await collect_fact_cards_for_task(db, task)
    result = lint_draft_text(body, fact_cards=cards)
    result["task_id"] = str(task.id)
    return result
