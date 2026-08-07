"""GEO 文章管理：发布与追踪对象（与 ContentTask 写稿流水分离）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ARTICLE_SOURCE_TYPES = ("ai", "local", "published_url")
ARTICLE_LIFECYCLE = ("draft", "pending_publish", "publishing", "tracked")
ARTICLE_ORIGINS = ("platform", "user", "official_site")


class GeoArticle(Base):
    __tablename__ = "geo_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="local", index=True)
    lifecycle_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="draft", index=True
    )
    origin: Mapped[str] = mapped_column(String(40), nullable=False, default="user", index=True)
    published_url: Mapped[str | None] = mapped_column(String(800))
    channel: Mapped[str | None] = mapped_column(String(80))
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    content_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    citation_count_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
