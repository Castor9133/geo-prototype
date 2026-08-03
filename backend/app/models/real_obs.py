"""真实点名观测 — 网页端半自动采样（与 trust_obs API 探针分轨）"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

REAL_OBS_PLATFORMS = ("doubao", "yuanbao", "deepseek")
REAL_OBS_PHASES = ("baseline", "after")
REAL_OBS_STATUSES = ("pending", "sampling", "completed", "partial", "failed")


class RealObsSnapshot(Base):
    __tablename__ = "real_obs_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    geo_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(20), nullable=False, default="after", index=True)
    prompt_pack_version: Mapped[str] = mapped_column(String(80), nullable=False, default="manual-v1")
    platforms: Mapped[list | None] = mapped_column(JSONB, default=list)
    questions: Mapped[list | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    owned_domains: Mapped[list | None] = mapped_column(JSONB, default=list)
    fact_source_urls: Mapped[list | None] = mapped_column(JSONB, default=list)
    entity_aliases: Mapped[list | None] = mapped_column(JSONB, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    probe_after_at: Mapped[datetime | None] = mapped_column(DateTime)
    method_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class RealObsSample(Base):
    __tablename__ = "real_obs_samples"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "question_id",
            "platform",
            "attempt",
            name="uq_real_obs_sample_unit",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("real_obs_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    geo_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    answer_text: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB, default=list)
    mention: Mapped[bool] = mapped_column(Boolean, default=False)
    competitor_mention: Mapped[bool] = mapped_column(Boolean, default=False)
    owned_citation: Mapped[bool] = mapped_column(Boolean, default=False)
    strong_adopted: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_snippet: Mapped[str | None] = mapped_column(Text)
    label_source: Mapped[str] = mapped_column(String(20), nullable=False, default="rule")
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_meta: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    sampled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
