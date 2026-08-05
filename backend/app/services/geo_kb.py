"""党建党媒 GEO 知识库：标签入库、L1 确认、可检索判定、任务沉淀。"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_engine import ContentTask, KnowledgeBase, KnowledgeDocument
from app.models.user import User
from app.services import content_engine as ce
from app.services.draft_lint import lint_task_draft
from app.services.geo_roles import has_business_geo_role, has_geo_role, is_platform_admin

REQUIRED_TAG_KEYS = ("site_id", "task_bajua", "doc_type")
VALID_TIERS = frozenset({"L1", "L2", "L3", "L4"})
VALID_REVIEW = frozenset({"pending_external", "pending_local", "approved", "retired"})


def normalize_tags(raw: dict[str, Any] | None) -> dict[str, Any]:
    tags = dict(raw or {})
    missing = [k for k in REQUIRED_TAG_KEYS if not str(tags.get(k) or "").strip()]
    if missing:
        raise ValueError(f"缺少必填标签: {', '.join(missing)}")
    return tags


def is_rag_eligible(doc: KnowledgeDocument, *, include_l3: bool = False) -> bool:
    if doc.review_state == "retired":
        return False
    tier = (doc.tier or "L2").upper()
    if tier == "L4":
        return False
    if tier == "L3":
        return bool(include_l3 and doc.review_state == "approved")
    if tier == "L1":
        return bool(doc.review_state == "approved" and doc.local_confirmed_at)
    # L2
    return doc.review_state == "approved"


def serialize_document(doc: KnowledgeDocument) -> dict[str, Any]:
    return {
        "id": str(doc.id),
        "knowledge_base_id": str(doc.knowledge_base_id),
        "title": doc.title,
        "body": doc.body or "",
        "source_path": doc.source_path,
        "source_url": doc.source_url,
        "status": doc.status,
        "tier": doc.tier,
        "tags": doc.tags or {},
        "review_state": doc.review_state,
        "fact_cards": doc.fact_cards or [],
        "external_approved_at": doc.external_approved_at.isoformat() + "Z" if doc.external_approved_at else None,
        "local_confirmed_at": doc.local_confirmed_at.isoformat() + "Z" if doc.local_confirmed_at else None,
        "local_confirmed_by": str(doc.local_confirmed_by) if doc.local_confirmed_by else None,
        "submitted_by": str(doc.submitted_by) if doc.submitted_by else None,
        "external_id": doc.external_id,
        "chunk_count": doc.chunk_count,
        "rag_eligible": is_rag_eligible(doc),
        "created_at": doc.created_at.isoformat() + "Z" if doc.created_at else None,
    }


async def ingest_tagged(
    db: AsyncSession,
    *,
    kb: KnowledgeBase,
    title: str,
    body: str,
    tier: str = "L2",
    tags: dict[str, Any] | None = None,
    fact_cards: list[dict[str, Any]] | None = None,
    source_url: str | None = None,
    external_id: str | None = None,
    external_approved: bool = True,
    submitted_by: UUID | None = None,
) -> KnowledgeDocument:
    tier_u = (tier or "L2").upper()
    if tier_u not in VALID_TIERS:
        raise ValueError(f"tier 须为 {sorted(VALID_TIERS)}")
    norm_tags = normalize_tags(tags)

    if tier_u == "L1":
        review_state = "pending_local" if external_approved else "pending_external"
    elif tier_u == "L4":
        review_state = "approved"
    else:
        review_state = "approved" if external_approved else "pending_external"

    # 先落库再切片；L1 未本仓确认也可切片，但不进 RAG
    doc = await ce.add_document_and_chunk(
        db,
        kb=kb,
        title=title,
        body=body,
        source_url=source_url,
        embed=True,
    )
    doc.tier = tier_u
    doc.tags = norm_tags
    doc.review_state = review_state
    doc.fact_cards = fact_cards or []
    doc.external_id = external_id
    doc.submitted_by = submitted_by
    if external_approved:
        doc.external_approved_at = datetime.utcnow()
    await db.flush()
    return doc


async def apply_external_review(
    db: AsyncSession,
    doc: KnowledgeDocument,
    *,
    review_state: str,
) -> KnowledgeDocument:
    state = (review_state or "").strip().lower()
    if state not in VALID_REVIEW:
        raise ValueError(f"review_state 无效: {review_state}")
    if state == "approved":
        doc.external_approved_at = datetime.utcnow()
        if (doc.tier or "").upper() == "L1":
            doc.review_state = "pending_local"
            doc.local_confirmed_at = None
            doc.local_confirmed_by = None
        else:
            doc.review_state = "approved"
    else:
        doc.review_state = state
    await db.flush()
    return doc


async def confirm_l1_local(
    db: AsyncSession,
    doc: KnowledgeDocument,
    *,
    actor: User,
) -> KnowledgeDocument:
    if (doc.tier or "").upper() != "L1":
        raise ValueError("仅 L1 需要本仓确认")
    if not has_geo_role(actor, "admin"):
        raise PermissionError("需要 admin")
    if doc.submitted_by and doc.submitted_by == actor.id:
        raise PermissionError("提交人不可确认自己的 L1 文档")
    if doc.review_state == "retired":
        raise ValueError("已退役文档不可确认")
    if not doc.external_approved_at and doc.review_state == "pending_external":
        raise ValueError("外审尚未通过")
    doc.local_confirmed_at = datetime.utcnow()
    doc.local_confirmed_by = actor.id
    doc.review_state = "approved"
    await db.flush()
    return doc


async def eligible_document_ids(
    db: AsyncSession,
    kb_id: UUID,
    *,
    include_l3: bool = False,
    bajua: str | None = None,
    site_id: str | None = None,
    tiers: list[str] | None = None,
) -> set[UUID]:
    rows = (
        await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id))
    ).scalars().all()
    allowed: set[UUID] = set()
    tier_filter = {t.upper() for t in (tiers or ["L1", "L2"])}
    if include_l3:
        tier_filter.add("L3")
    for doc in rows:
        tier = (doc.tier or "L2").upper()
        if tier not in tier_filter:
            continue
        if not is_rag_eligible(doc, include_l3=include_l3):
            continue
        tags = doc.tags or {}
        if bajua and str(tags.get("task_bajua") or "") != bajua:
            continue
        if site_id and str(tags.get("site_id") or "") != site_id:
            continue
        allowed.add(doc.id)
    return allowed


WORKFLOW_ORDER = [
    "claimed",
    "template_draft",
    "channel_draft",
    "in_review",
    "ready",
    "archived",
    "promoted",
]


def serialize_task(task: ContentTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "workflow_status": task.workflow_status or "claimed",
        "template_key": task.template_key,
        "channel_key": task.channel_key,
        "input_query": task.input_query,
        "draft_body": task.draft_body,
        "template_draft_body": task.template_draft_body,
        "channel_draft_body": task.channel_draft_body,
        "knowledge_base_id": str(task.knowledge_base_id) if task.knowledge_base_id else None,
        "geo_run_id": str(task.geo_run_id) if task.geo_run_id else None,
        "strategy_id": str(task.strategy_id) if getattr(task, "strategy_id", None) else None,
        "claimed_by": str(task.claimed_by) if task.claimed_by else None,
        "reviewed_by": str(task.reviewed_by) if task.reviewed_by else None,
        "promote_suggestion": task.promote_suggestion,
        "promoted_document_id": str(task.promoted_document_id) if task.promoted_document_id else None,
        "meta": task.meta or {},
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() + "Z" if task.created_at else None,
        "finished_at": task.finished_at.isoformat() + "Z" if task.finished_at else None,
    }


async def save_template_draft(
    db: AsyncSession,
    task: ContentTask,
    *,
    body: str,
    template_key: str | None = None,
    actor: User | None = None,
) -> ContentTask:
    task.template_draft_body = body
    task.draft_body = body
    if template_key:
        task.template_key = template_key
    task.workflow_status = "template_draft"
    if actor and not task.claimed_by:
        task.claimed_by = actor.id
    task.meta = {**(task.meta or {}), "template_saved_at": datetime.utcnow().isoformat() + "Z"}
    await db.flush()
    return task


async def save_channel_draft(
    db: AsyncSession,
    task: ContentTask,
    *,
    body: str,
    channel_key: str | None = None,
) -> ContentTask:
    if not (task.template_draft_body or task.draft_body):
        raise ValueError("请先完成模板生产稿")
    task.channel_draft_body = body
    task.draft_body = body
    if channel_key:
        task.channel_key = channel_key
    task.workflow_status = "channel_draft"
    task.meta = {**(task.meta or {}), "channel_saved_at": datetime.utcnow().isoformat() + "Z"}
    await db.flush()
    return task


async def submit_for_review(db: AsyncSession, task: ContentTask) -> ContentTask:
    if not (task.channel_draft_body or task.draft_body):
        raise ValueError("请先完成平台适配稿")
    task.workflow_status = "in_review"
    await db.flush()
    return task


async def approve_ready(
    db: AsyncSession,
    task: ContentTask,
    *,
    actor: User,
    force_reason: str | None = None,
) -> ContentTask:
    # 日常过审仅审核岗；admin 不顶替日常过审，但可用 force_reason 红牌放行
    if not has_business_geo_role(actor, "reviewer") and not (
        is_platform_admin(actor) and (force_reason or "").strip()
    ):
        raise PermissionError("需要审核岗位过审稿件（技术支持不可日常过审）")
    if task.claimed_by and task.claimed_by == actor.id and not is_platform_admin(actor):
        raise PermissionError("编写人不可过审自己领取的稿件，请换审核账号")
    if (task.workflow_status or "") not in ("in_review", "channel_draft", "template_draft"):
        raise ValueError("仅审核中或已出稿件可过审")

    lint = await lint_task_draft(db, task)
    if lint.get("blocking"):
        if is_platform_admin(actor) and (force_reason or "").strip():
            task.meta = {
                **(task.meta or {}),
                "lint_force_reason": force_reason.strip(),
                "lint_forced_by": str(actor.id),
                "lint_last": lint,
            }
        else:
            msgs = "；".join(
                i.get("message") or i.get("code") or ""
                for i in (lint.get("issues") or [])
                if i.get("severity") == "error"
            )
            raise ValueError(
                "写稿体检未通过（红牌）："
                + (msgs or "存在严重问题")
                + "。管理员可填写 force_reason 强行过审。"
            )
    else:
        task.meta = {**(task.meta or {}), "lint_last": lint}

    task.workflow_status = "ready"
    task.reviewed_by = actor.id
    task.status = "completed"
    task.finished_at = datetime.utcnow()
    await db.flush()
    return task


async def compute_promote_suggestion(db: AsyncSession, task: ContentTask) -> str | None:
    """根据关联 geo_run 的 real_obs after 快照给建议。"""
    if not task.geo_run_id:
        return None
    from app.services import real_obs as ro

    # lazy import GeoRun compare
    from app.models.geo_run import GeoRun

    run = await db.get(GeoRun, task.geo_run_id)
    if not run:
        return None
    cmp = await ro.compare_run(db, run)
    stats = cmp.get("after_stats") or {}
    strong = int(stats.get("strong_adopted_count") or 0)
    mention = int(stats.get("mention_count") or 0)
    n = int(stats.get("sample_count") or 0)
    if n <= 0:
        return None
    if strong >= 1:
        return "promote"
    if mention == 0:
        return "reject"
    if mention < max(1, n // 2):
        return "reject"
    return None


async def refresh_task_suggestion(db: AsyncSession, task: ContentTask) -> ContentTask:
    suggestion = await compute_promote_suggestion(db, task)
    task.promote_suggestion = suggestion
    await db.flush()
    return task


async def confirm_promote(
    db: AsyncSession,
    task: ContentTask,
    *,
    actor: User,
    kb: KnowledgeBase,
) -> ContentTask:
    if not has_geo_role(actor, "admin", "reviewer"):
        raise PermissionError("需要 admin 或 reviewer")
    if task.workflow_status not in ("ready", "in_review"):
        # allow promote from ready primarily
        if task.workflow_status != "ready":
            raise ValueError("仅 ready 任务可沉淀")
    body = task.channel_draft_body or task.draft_body or ""
    if not body.strip():
        raise ValueError("无正文可沉淀")
    tags = {
        "site_id": (task.meta or {}).get("site_id") or "pilot-site",
        "task_bajua": (task.meta or {}).get("task_bajua") or "社区民生",
        "doc_type": "活动报道",
        "source_org": "广电生成沉淀",
        "from_task_id": str(task.id),
    }
    doc = await ingest_tagged(
        db,
        kb=kb,
        title=f"[沉淀] {task.title}"[:300],
        body=body,
        tier="L2",
        tags=tags,
        fact_cards=[
            {
                "claim": task.title,
                "evidence_url": None,
                "bajua": tags["task_bajua"],
                "doc_type": "活动报道",
                "as_of": datetime.utcnow().date().isoformat(),
                "quote_span": body[:200],
            }
        ],
        external_approved=True,
        submitted_by=actor.id,
    )
    # L2 信任外审路径：已 approved
    task.workflow_status = "promoted"
    task.promoted_document_id = doc.id
    task.promote_suggestion = "promote"
    task.meta = {**(task.meta or {}), "promoted_at": datetime.utcnow().isoformat() + "Z"}
    await db.flush()
    return task


async def confirm_reject(db: AsyncSession, task: ContentTask, *, actor: User) -> ContentTask:
    if not has_geo_role(actor, "admin", "reviewer"):
        raise PermissionError("需要 admin 或 reviewer")
    task.workflow_status = "archived"
    task.promote_suggestion = "reject"
    task.meta = {
        **(task.meta or {}),
        "archived_at": datetime.utcnow().isoformat() + "Z",
        "archived_by": str(actor.id),
    }
    await db.flush()
    return task


async def kb_tier_stats(db: AsyncSession, kb_id: UUID) -> dict[str, Any]:
    rows = (
        await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id))
    ).scalars().all()
    tiers: dict[str, int] = {"L1": 0, "L2": 0, "L3": 0, "L4": 0}
    rag_n = 0
    pending_l1 = 0
    for d in rows:
        t = (d.tier or "L2").upper()
        if t in tiers:
            tiers[t] += 1
        if is_rag_eligible(d):
            rag_n += 1
        if t == "L1" and d.review_state == "pending_local":
            pending_l1 += 1
    return {"tiers": tiers, "rag_eligible": rag_n, "pending_l1_confirm": pending_l1, "total": len(rows)}
