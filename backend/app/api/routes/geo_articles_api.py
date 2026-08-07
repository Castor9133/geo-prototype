"""GEO 文章管理 API：/api/geo-articles"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.services import geo_articles as svc

router = APIRouter()


class CreateArticleBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source_type: str = Field(description="ai | local | published_url")
    body: str | None = None
    published_url: str | None = None
    channel: str | None = None
    strategy_id: uuid.UUID | None = None
    knowledge_base_id: uuid.UUID | None = None
    origin: str | None = None
    create_write_task: bool = True


class PatchArticleBody(BaseModel):
    title: str | None = None
    body: str | None = None
    lifecycle_status: str | None = None
    origin: str | None = None
    published_url: str | None = None
    channel: str | None = None
    strategy_id: uuid.UUID | None = None
    knowledge_base_id: uuid.UUID | None = None


class AttachPublishBody(BaseModel):
    published_url: str = Field(min_length=1, max_length=800)
    channel: str | None = None


@router.get("")
async def list_articles(
    db: DbSession,
    user: CurrentUser,
    q: str | None = None,
    lifecycle_status: str | None = None,
    origin: str | None = None,
    source_type: str | None = None,
    mine_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = await svc.list_articles(
        db,
        q=q,
        lifecycle_status=lifecycle_status,
        origin=origin,
        source_type=source_type,
        mine_only=mine_only,
        owner_user_id=user.id,
        limit=limit,
    )
    summary = await svc.count_summary(db)
    return {
        "items": [svc.serialize_article(a) for a in rows],
        **summary,
    }


@router.get("/citation-ranking")
async def article_citation_ranking(
    db: DbSession,
    _: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    return await svc.citation_ranking_for_articles(db, limit=limit)


@router.post("")
async def create_article(payload: CreateArticleBody, db: DbSession, user: CurrentUser):
    try:
        art = await svc.create_article(
            db,
            actor=user,
            title=payload.title,
            source_type=payload.source_type,
            body=payload.body,
            published_url=payload.published_url,
            channel=payload.channel,
            strategy_id=payload.strategy_id,
            knowledge_base_id=payload.knowledge_base_id,
            origin=payload.origin,
            create_write_task=payload.create_write_task,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(art)
    return svc.serialize_article(art)


@router.get("/{article_id}")
async def get_article(article_id: uuid.UUID, db: DbSession, _: CurrentUser):
    art = await svc.get_article(db, article_id)
    if not art:
        raise HTTPException(404, "文章不存在")
    return svc.serialize_article(art)


@router.patch("/{article_id}")
async def patch_article(
    article_id: uuid.UUID, payload: PatchArticleBody, db: DbSession, _: CurrentUser
):
    art = await svc.get_article(db, article_id)
    if not art:
        raise HTTPException(404, "文章不存在")
    fields = payload.model_dump(exclude_unset=True)
    try:
        art = await svc.update_article(db, art, fields=fields)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(art)
    return svc.serialize_article(art)


@router.post("/{article_id}/attach-publish")
async def attach_publish(
    article_id: uuid.UUID, payload: AttachPublishBody, db: DbSession, _: CurrentUser
):
    art = await svc.get_article(db, article_id)
    if not art:
        raise HTTPException(404, "文章不存在")
    try:
        art = await svc.attach_publish(
            db,
            art,
            published_url=payload.published_url,
            channel=payload.channel,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(art)
    return svc.serialize_article(art)
