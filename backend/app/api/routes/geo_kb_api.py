"""GEO 知识库入库 / L1 确认 / 任务两步草稿 / 沉淀建议"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DbSession, OptionalUser
from app.models.content_engine import ContentTask, KnowledgeBase, KnowledgeDocument
from app.models.user import User
from app.services import geo_kb as gkb
from app.services.geo_roles import effective_geo_roles, has_geo_role

router = APIRouter()


class IngestTaggedBody(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    tier: str = "L2"
    tags: dict[str, Any]
    fact_cards: list[dict[str, Any]] | None = None
    source_url: str | None = None
    external_id: str | None = None
    external_approved: bool = True


class ExternalReviewBody(BaseModel):
    review_state: str = Field(description="approved|retired|pending_external|pending_local")


class TemplateDraftBody(BaseModel):
    body: str = Field(min_length=1)
    template_key: str | None = None


class ChannelDraftBody(BaseModel):
    body: str = Field(min_length=1)
    channel_key: str | None = None


class ClaimBody(BaseModel):
    geo_run_id: uuid.UUID | None = None
    strategy_id: uuid.UUID | None = None
    site_id: str | None = None
    task_bajua: str | None = None


class GeoRoleBody(BaseModel):
    geo_role: str | None = Field(default=None, description="editor|reviewer|risk|null")


@router.get("/geo/me")
async def geo_me(user: CurrentUser):
    return {
        "user_id": str(user.id),
        "email": user.email,
        "platform_role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "geo_role": getattr(user, "geo_role", None),
        "effective_roles": sorted(effective_geo_roles(user)),
    }


@router.patch("/geo/users/{user_id}/role")
async def set_geo_role(user_id: uuid.UUID, payload: GeoRoleBody, db: DbSession, _: AdminUser):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(404, "用户不存在")
    role = (payload.geo_role or "").strip().lower() or None
    if role and role not in ("editor", "reviewer", "risk"):
        raise HTTPException(400, "geo_role 须为 editor|reviewer|risk 或清空")
    target.geo_role = role
    await db.commit()
    return {"id": str(target.id), "geo_role": target.geo_role}


@router.post("/knowledge-bases/{kb_id}/ingest-tagged")
async def ingest_tagged(kb_id: uuid.UUID, payload: IngestTaggedBody, db: DbSession, user: CurrentUser):
    if not has_geo_role(user, "admin", "editor", "reviewer", "risk"):
        # 外系统可用 admin demo token；也允许 admin
        raise HTTPException(403, "需要 GEO 角色或 admin")
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    try:
        doc = await gkb.ingest_tagged(
            db,
            kb=kb,
            title=payload.title,
            body=payload.body,
            tier=payload.tier,
            tags=payload.tags,
            fact_cards=payload.fact_cards,
            source_url=payload.source_url,
            external_id=payload.external_id,
            external_approved=payload.external_approved,
            submitted_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(doc)
    return gkb.serialize_document(doc)


@router.post("/knowledge-bases/{kb_id}/documents/{doc_id}/external-review")
async def external_review_callback(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    payload: ExternalReviewBody,
    db: DbSession,
    user: CurrentUser,
):
    if not has_geo_role(user, "admin", "risk", "reviewer"):
        raise HTTPException(403, "需要审核回调权限")
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(404, "文档不存在")
    try:
        doc = await gkb.apply_external_review(db, doc, review_state=payload.review_state)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(doc)
    return gkb.serialize_document(doc)


@router.post("/knowledge-bases/{kb_id}/documents/{doc_id}/confirm-l1")
async def confirm_l1(kb_id: uuid.UUID, doc_id: uuid.UUID, db: DbSession, user: CurrentUser):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(404, "文档不存在")
    try:
        doc = await gkb.confirm_l1_local(db, doc, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(doc)
    return gkb.serialize_document(doc)


@router.get("/knowledge-bases/{kb_id}/geo-stats")
async def geo_stats(kb_id: uuid.UUID, db: DbSession, _: OptionalUser):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    stats = await gkb.kb_tier_stats(db, kb_id)
    return {"knowledge_base_id": str(kb_id), **stats}


@router.get("/knowledge-bases/{kb_id}/documents-geo")
async def list_docs_geo(
    kb_id: uuid.UUID,
    db: DbSession,
    _: OptionalUser,
    tier: str | None = None,
    review_state: str | None = None,
    bajua: str | None = None,
):
    q = select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    if tier:
        q = q.where(KnowledgeDocument.tier == tier.upper())
    if review_state:
        q = q.where(KnowledgeDocument.review_state == review_state)
    rows = (await db.execute(q.order_by(KnowledgeDocument.created_at.desc()).limit(200))).scalars().all()
    items = []
    for d in rows:
        if bajua and str((d.tags or {}).get("task_bajua") or "") != bajua:
            continue
        items.append(gkb.serialize_document(d))
    return {"items": items}


@router.post("/tasks/{task_id}/claim")
async def claim_task(task_id: uuid.UUID, payload: ClaimBody, db: DbSession, user: CurrentUser):
    if not has_geo_role(user, "editor", "admin", "reviewer"):
        raise HTTPException(403, "需要 editor")
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    task.workflow_status = "claimed"
    task.claimed_by = user.id
    if payload.geo_run_id:
        task.geo_run_id = payload.geo_run_id
    if payload.strategy_id:
        task.strategy_id = payload.strategy_id
    meta = dict(task.meta or {})
    if payload.site_id:
        meta["site_id"] = payload.site_id
    if payload.task_bajua:
        meta["task_bajua"] = payload.task_bajua
    task.meta = meta
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.patch("/tasks/{task_id}/template-draft")
async def patch_template_draft(
    task_id: uuid.UUID, payload: TemplateDraftBody, db: DbSession, user: CurrentUser
):
    if not has_geo_role(user, "editor", "admin"):
        raise HTTPException(403, "需要 editor")
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    task = await gkb.save_template_draft(
        db, task, body=payload.body, template_key=payload.template_key, actor=user
    )
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.patch("/tasks/{task_id}/channel-draft")
async def patch_channel_draft(
    task_id: uuid.UUID, payload: ChannelDraftBody, db: DbSession, user: CurrentUser
):
    if not has_geo_role(user, "editor", "admin"):
        raise HTTPException(403, "需要 editor")
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        task = await gkb.save_channel_draft(
            db, task, body=payload.body, channel_key=payload.channel_key
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.post("/tasks/{task_id}/submit-review")
async def submit_review(task_id: uuid.UUID, db: DbSession, user: CurrentUser):
    if not has_geo_role(user, "editor", "admin"):
        raise HTTPException(403, "需要 editor")
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        task = await gkb.submit_for_review(db, task)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.post("/tasks/{task_id}/approve-ready")
async def approve_ready(task_id: uuid.UUID, db: DbSession, user: CurrentUser):
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        task = await gkb.approve_ready(db, task, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.post("/tasks/{task_id}/refresh-suggestion")
async def refresh_suggestion(task_id: uuid.UUID, db: DbSession, user: CurrentUser):
    if not has_geo_role(user, "admin", "reviewer", "editor"):
        raise HTTPException(403, "权限不足")
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    task = await gkb.refresh_task_suggestion(db, task)
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.post("/tasks/{task_id}/confirm-promote")
async def confirm_promote(task_id: uuid.UUID, db: DbSession, user: CurrentUser):
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    kb_id = task.knowledge_base_id
    if not kb_id:
        raise HTTPException(400, "任务未绑定知识库")
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    try:
        task = await gkb.confirm_promote(db, task, actor=user, kb=kb)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.post("/tasks/{task_id}/confirm-reject")
async def confirm_reject(task_id: uuid.UUID, db: DbSession, user: CurrentUser):
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        task = await gkb.confirm_reject(db, task, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return gkb.serialize_task(task)


@router.get("/tasks-geo")
async def list_tasks_geo(
    db: DbSession,
    _: OptionalUser,
    workflow_status: str | None = None,
    suggestion: str | None = None,
    limit: int = 50,
):
    q = select(ContentTask).order_by(ContentTask.created_at.desc()).limit(min(limit, 100))
    if workflow_status:
        q = q.where(ContentTask.workflow_status == workflow_status)
    if suggestion:
        q = q.where(ContentTask.promote_suggestion == suggestion)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [gkb.serialize_task(t) for t in rows]}
