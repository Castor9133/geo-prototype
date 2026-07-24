"""
可信观测（Trust Observation）— 探针题 / 采样运行 / 答案样本
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrustObsProbe(Base):
    __tablename__ = "trust_obs_probes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    probe_key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False, default="probe-v1", index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    entity_name: Mapped[str] = mapped_column(String(200), nullable=False, default="GEO 示范栏目")
    entity_aliases: Mapped[list | None] = mapped_column(JSONB, default=list)
    owned_domains: Mapped[list | None] = mapped_column(JSONB, default=list)
    competitor_names: Mapped[list | None] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrustObsRun(Base):
    __tablename__ = "trust_obs_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False, default="probe-v1")
    locale: Mapped[str] = mapped_column(String(40), nullable=False, default="zh-CN")
    device: Mapped[str] = mapped_column(String(40), nullable=False, default="api")
    login_state: Mapped[str] = mapped_column(String(40), nullable=False, default="api-key")
    model_name: Mapped[str | None] = mapped_column(String(120))
    repeats: Mapped[int] = mapped_column(Integer, default=2)
    aggregate: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    method_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TrustObsSample(Base):
    __tablename__ = "trust_obs_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    probe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    probe_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    raw_answer: Mapped[str | None] = mapped_column(Text)
    primary_label: Mapped[str] = mapped_column(String(40), nullable=False, default="absent", index=True)
    labels: Mapped[list | None] = mapped_column(JSONB, default=list)
    classifier_meta: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
