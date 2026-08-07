"""文章管理服务：CRUD、发布登记、与观测引用排行对齐。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo_article import (
    ARTICLE_LIFECYCLE,
    ARTICLE_ORIGINS,
    ARTICLE_SOURCE_TYPES,
    GeoArticle,
)
from app.models.geo_strategy import GeoStrategy
from app.models.real_obs import RealObsSample
from app.models.user import User
from app.services import geo_strategy_svc as strategy_svc
from app.services import real_obs as real_obs_svc


def _norm_url(url: str | None) -> str:
    return str(url or "").strip().rstrip("/").lower()


def serialize_article(a: GeoArticle) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "title": a.title,
        "body": a.body or "",
        "source_type": a.source_type,
        "lifecycle_status": a.lifecycle_status,
        "origin": a.origin,
        "published_url": a.published_url,
        "channel": a.channel,
        "strategy_id": str(a.strategy_id) if a.strategy_id else None,
        "knowledge_base_id": str(a.knowledge_base_id) if a.knowledge_base_id else None,
        "content_task_id": str(a.content_task_id) if a.content_task_id else None,
        "owner_user_id": str(a.owner_user_id) if a.owner_user_id else None,
        "citation_count_30d": int(a.citation_count_30d or 0),
        "meta": a.meta or {},
        "created_at": a.created_at.isoformat() + "Z" if a.created_at else None,
        "updated_at": a.updated_at.isoformat() + "Z" if a.updated_at else None,
        "write_href": (
            f"/strategies?strategy={a.strategy_id}&tab=write"
            if a.strategy_id
            else None
        ),
    }


async def list_articles(
    db: AsyncSession,
    *,
    q: str | None = None,
    lifecycle_status: str | None = None,
    origin: str | None = None,
    source_type: str | None = None,
    mine_only: bool = False,
    owner_user_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[GeoArticle]:
    stmt = select(GeoArticle).order_by(GeoArticle.created_at.desc())
    if q and q.strip():
        stmt = stmt.where(GeoArticle.title.ilike(f"%{q.strip()}%"))
    if lifecycle_status and lifecycle_status in ARTICLE_LIFECYCLE:
        stmt = stmt.where(GeoArticle.lifecycle_status == lifecycle_status)
    if origin and origin in ARTICLE_ORIGINS:
        stmt = stmt.where(GeoArticle.origin == origin)
    if source_type and source_type in ARTICLE_SOURCE_TYPES:
        stmt = stmt.where(GeoArticle.source_type == source_type)
    if mine_only and owner_user_id:
        stmt = stmt.where(GeoArticle.owner_user_id == owner_user_id)
    stmt = stmt.limit(min(max(limit, 1), 200))
    return list((await db.execute(stmt)).scalars().all())


async def get_article(db: AsyncSession, article_id: uuid.UUID) -> GeoArticle | None:
    return await db.get(GeoArticle, article_id)


async def create_article(
    db: AsyncSession,
    *,
    actor: User,
    title: str,
    source_type: str,
    body: str | None = None,
    published_url: str | None = None,
    channel: str | None = None,
    strategy_id: uuid.UUID | None = None,
    knowledge_base_id: uuid.UUID | None = None,
    origin: str | None = None,
    create_write_task: bool = True,
) -> GeoArticle:
    st = (source_type or "local").strip().lower()
    if st not in ARTICLE_SOURCE_TYPES:
        raise ValueError("source_type 须为 ai / local / published_url")
    title_clean = (title or "").strip()
    if not title_clean:
        raise ValueError("标题不能为空")

    if st == "published_url":
        url = (published_url or "").strip()
        if not url:
            raise ValueError("导入已发布文章须提供链接")
        lifecycle = "tracked"
        og = origin or "official_site"
    elif st == "ai":
        lifecycle = "draft"
        og = origin or "platform"
    else:
        lifecycle = "pending_publish"
        og = origin or "user"

    if og not in ARTICLE_ORIGINS:
        raise ValueError("origin 无效")

    strategy: GeoStrategy | None = None
    if strategy_id:
        strategy = await db.get(GeoStrategy, strategy_id)
        if not strategy:
            raise ValueError("关联策略不存在")
        if not knowledge_base_id and strategy.knowledge_base_id:
            knowledge_base_id = strategy.knowledge_base_id

    article = GeoArticle(
        title=title_clean[:500],
        body=(body or "").strip() or None,
        source_type=st,
        lifecycle_status=lifecycle,
        origin=og,
        published_url=(published_url or "").strip() or None,
        channel=(channel or "").strip() or None,
        strategy_id=strategy_id,
        knowledge_base_id=knowledge_base_id,
        owner_user_id=actor.id,
        citation_count_30d=0,
        meta={"created_via": "articles_api"},
    )
    db.add(article)
    await db.flush()

    if st == "ai" and strategy and create_write_task:
        try:
            if knowledge_base_id and not strategy.knowledge_base_id:
                strategy.knowledge_base_id = knowledge_base_id
            task = await strategy_svc.attach_task(
                db,
                strategy,
                actor=actor,
                title=title_clean[:300],
                content_kind="deep",
            )
            article.content_task_id = task.id
            try:
                task = await strategy_svc.generate_task_draft(
                    db, strategy, task, actor=actor
                )
                if task.draft_body and not article.body:
                    article.body = (task.draft_body or "")[:20000]
                    article.lifecycle_status = "pending_publish"
            except Exception as gen_exc:  # noqa: BLE001
                meta = dict(article.meta or {})
                meta["draft_generate_error"] = str(gen_exc)[:300]
                article.meta = meta
        except Exception as exc:  # noqa: BLE001 — 挂接失败不阻断建文
            meta = dict(article.meta or {})
            meta["write_task_error"] = str(exc)[:300]
            article.meta = meta

    article.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(article)
    return article


async def update_article(
    db: AsyncSession,
    article: GeoArticle,
    *,
    fields: dict[str, Any],
) -> GeoArticle:
    if "title" in fields and fields["title"] is not None:
        t = str(fields["title"]).strip()
        if not t:
            raise ValueError("标题不能为空")
        article.title = t[:500]
    if "body" in fields:
        article.body = (str(fields["body"] or "").strip() or None)
    if "lifecycle_status" in fields and fields["lifecycle_status"]:
        st = str(fields["lifecycle_status"]).strip()
        if st not in ARTICLE_LIFECYCLE:
            raise ValueError("lifecycle_status 无效")
        article.lifecycle_status = st
    if "origin" in fields and fields["origin"]:
        og = str(fields["origin"]).strip()
        if og not in ARTICLE_ORIGINS:
            raise ValueError("origin 无效")
        article.origin = og
    if "published_url" in fields:
        article.published_url = (str(fields["published_url"] or "").strip() or None)
    if "channel" in fields:
        article.channel = (str(fields["channel"] or "").strip() or None)
    if "strategy_id" in fields:
        sid = fields["strategy_id"]
        article.strategy_id = uuid.UUID(str(sid)) if sid else None
    if "knowledge_base_id" in fields:
        kid = fields["knowledge_base_id"]
        article.knowledge_base_id = uuid.UUID(str(kid)) if kid else None
    article.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(article)
    return article


async def attach_publish(
    db: AsyncSession,
    article: GeoArticle,
    *,
    published_url: str,
    channel: str | None = None,
) -> GeoArticle:
    url = (published_url or "").strip()
    if not url:
        raise ValueError("须提供已发布链接")
    article.published_url = url
    if channel:
        article.channel = channel.strip()
    article.lifecycle_status = "tracked"
    article.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(article)
    return article


async def refresh_citation_counts(db: AsyncSession) -> int:
    """按近 30 日观测样本引用 URL 回写 citation_count_30d。"""
    since = datetime.utcnow() - timedelta(days=30)
    samples = (
        await db.execute(
            select(RealObsSample).where(
                RealObsSample.ok.is_(True),
                or_(
                    RealObsSample.sampled_at >= since,
                    RealObsSample.created_at >= since,
                ),
            )
        )
    ).scalars().all()
    url_counts: dict[str, int] = {}
    for s in samples:
        for c in s.citations or []:
            if isinstance(c, dict):
                u = _norm_url(c.get("url") or c.get("href"))
            else:
                u = _norm_url(str(c))
            if u:
                url_counts[u] = url_counts.get(u, 0) + 1

    articles = (await db.execute(select(GeoArticle))).scalars().all()
    updated = 0
    for a in articles:
        key = _norm_url(a.published_url)
        n = url_counts.get(key, 0) if key else 0
        if int(a.citation_count_30d or 0) != n:
            a.citation_count_30d = n
            a.updated_at = datetime.utcnow()
            updated += 1
    await db.flush()
    return updated


async def citation_ranking_for_articles(
    db: AsyncSession,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """观测引用排行 + 本库文章标题优先。"""
    await refresh_citation_counts(db)
    samples = (
        await db.execute(select(RealObsSample).where(RealObsSample.ok.is_(True)).limit(2000))
    ).scalars().all()
    rankings = real_obs_svc.build_citation_rankings(samples, limit=max(limit, 50))

    articles = (
        await db.execute(
            select(GeoArticle)
            .where(GeoArticle.published_url.is_not(None))
            .order_by(GeoArticle.citation_count_30d.desc())
        )
    ).scalars().all()
    by_url = {_norm_url(a.published_url): a for a in articles if a.published_url}

    enriched = []
    for row in rankings.get("articles") or []:
        key = _norm_url(row.get("url"))
        art = by_url.get(key)
        item = dict(row)
        if art:
            item["title"] = art.title
            item["article_id"] = str(art.id)
            item["owned_library"] = True
            item["count"] = max(int(item.get("count") or 0), int(art.citation_count_30d or 0))
        else:
            item["owned_library"] = False
        enriched.append(item)

    # 本库有 URL 但未出现在观测排行的文章也补上
    seen = {_norm_url(x.get("url")) for x in enriched}
    for a in articles:
        key = _norm_url(a.published_url)
        if not key or key in seen:
            continue
        if int(a.citation_count_30d or 0) <= 0:
            continue
        enriched.append(
            {
                "rank": 0,
                "title": a.title,
                "url": a.published_url,
                "domain": (urlparse(a.published_url).hostname or "").lower().lstrip("www."),
                "count": int(a.citation_count_30d or 0),
                "owned": True,
                "owned_library": True,
                "article_id": str(a.id),
                "platforms": [],
            }
        )
    enriched.sort(key=lambda x: (-int(x.get("count") or 0), str(x.get("title") or "")))
    for i, row in enumerate(enriched):
        row["rank"] = i + 1
    lim = max(1, min(int(limit or 50), 200))
    return {
        "articles": enriched[:lim],
        "article_total": len(enriched),
        "domains": rankings.get("domains") or [],
        "domain_total": rankings.get("domain_total") or 0,
        "sample_count": rankings.get("sample_count") or 0,
        "citation_event_count": rankings.get("citation_event_count") or 0,
    }


async def count_summary(db: AsyncSession) -> dict[str, int]:
    total = await db.scalar(select(func.count()).select_from(GeoArticle)) or 0
    with_link = await db.scalar(
        select(func.count()).select_from(GeoArticle).where(GeoArticle.published_url.is_not(None))
    ) or 0
    return {"article_count": int(total), "link_count": int(with_link)}
