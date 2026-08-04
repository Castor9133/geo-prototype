"""GEO 策略对象（党建党媒快速落地：作业与验收本体）"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STRATEGY_PLATFORMS = ("doubao", "yuanbao", "deepseek")
STRATEGY_STATUSES = (
    "draft",
    "pending_review",
    "executable",
    "deployed",
    "observing",
    "effective",
    "partial",
    "ineffective",
    "archived",
)
MEDIA_CHANNEL_TYPES = (
    "wechat",
    "toutiao",
    "douyin",
    "baike",
    "baijiahao",
    "other",
)


class GeoStrategy(Base):
    __tablename__ = "geo_strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    question_class: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    query_variants: Mapped[list | None] = mapped_column(JSONB, default=list)
    content_orientation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    channel_matrix: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    success_signal: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    knowledge_document_ids: Mapped[list | None] = mapped_column(JSONB, default=list)
    knowledge_tag_pack: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    geo_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    diagnostic_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    baseline_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    after_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_strategies.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    site_url: Mapped[str | None] = mapped_column(String(500))
    media_channel_type: Mapped[str | None] = mapped_column(String(40))
    media_url: Mapped[str | None] = mapped_column(String(500))
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime)
    deployed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    verdict: Mapped[str | None] = mapped_column(String(40))
    verdict_detail: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    judged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    judged_at: Mapped[datetime | None] = mapped_column(DateTime)

    force_reason: Mapped[str | None] = mapped_column(Text)
    force_initiated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    force_business_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    force_admin_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    force_status: Mapped[str | None] = mapped_column(String(40))

    promote_suggestion: Mapped[str | None] = mapped_column(String(40))
    promoted_document_ids: Mapped[list | None] = mapped_column(JSONB, default=list)

    gap_note: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
