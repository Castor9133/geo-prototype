"""GEO 回合（Run）— Suite 闭环作业单位"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DEFAULT_PLATFORMS = ["豆包", "元宝", "Kimi", "DeepSeek"]
DEFAULT_ENTITY = "DJI Mini 5 Pro"
DEFAULT_COMPETITOR = "Autel"
DEFAULT_OBSERVE_SCRIPT = "geo-observe-funnel-dji-vs-autel"


class GeoRun(Base):
    __tablename__ = "geo_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    entity: Mapped[str] = mapped_column(String(200), nullable=False, default=DEFAULT_ENTITY)
    competitor: Mapped[str] = mapped_column(String(200), nullable=False, default=DEFAULT_COMPETITOR)
    url: Mapped[str | None] = mapped_column(String(500))
    platforms: Mapped[list | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    # artifacts: diagnostic_report_id, keyword_pack_id, selected_keywords[],
    # knowledge_base_id, task_ids[], observe_script_key, channel_ready[], steps[]
    artifacts: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    observe_script_key: Mapped[str] = mapped_column(
        String(120), default=DEFAULT_OBSERVE_SCRIPT, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
