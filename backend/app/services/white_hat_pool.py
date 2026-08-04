"""白号池服务：登记、统计、种子账号（非正式验收口令）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obs_white_account import WHITE_PLATFORMS, ObsWhiteAccount
from app.models.user import User
from app.services.geo_roles import has_geo_role, is_platform_admin

MIN_PER_PLATFORM = 5


def serialize_account(row: ObsWhiteAccount) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "platform": row.platform,
        "label": row.label,
        "status": row.status,
        "notes": row.notes,
        "meta": dict(row.meta or {}),
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
        "updated_at": row.updated_at.isoformat() + "Z" if row.updated_at else None,
    }


async def pool_summary(db: AsyncSession) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(ObsWhiteAccount.platform, ObsWhiteAccount.status, func.count())
            .group_by(ObsWhiteAccount.platform, ObsWhiteAccount.status)
        )
    ).all()
    by_platform: dict[str, dict[str, int]] = {p: {"available": 0, "busy": 0, "retired": 0, "total": 0} for p in WHITE_PLATFORMS}
    for platform, status, n in rows:
        p = str(platform)
        if p not in by_platform:
            by_platform[p] = {"available": 0, "busy": 0, "retired": 0, "total": 0}
        by_platform[p][str(status)] = int(n)
        by_platform[p]["total"] += int(n)
    ready = all(by_platform[p]["available"] + by_platform[p]["busy"] >= MIN_PER_PLATFORM for p in WHITE_PLATFORMS)
    return {
        "min_per_platform": MIN_PER_PLATFORM,
        "platforms": by_platform,
        "formal_ready": ready,
        "note": "正式验收每平台可用白号须 ≥5；不足只能做非正式练习",
    }


async def list_accounts(
    db: AsyncSession,
    *,
    platform: str | None = None,
    status: str | None = None,
) -> list[ObsWhiteAccount]:
    q = select(ObsWhiteAccount).order_by(ObsWhiteAccount.platform.asc(), ObsWhiteAccount.label.asc())
    if platform:
        q = q.where(ObsWhiteAccount.platform == platform)
    if status:
        q = q.where(ObsWhiteAccount.status == status)
    return list((await db.execute(q)).scalars().all())


async def upsert_account(
    db: AsyncSession,
    *,
    actor: User,
    platform: str,
    label: str,
    status: str = "available",
    notes: str | None = None,
) -> ObsWhiteAccount:
    if not (is_platform_admin(actor) or has_geo_role(actor, "admin")):
        raise PermissionError("仅技术支持可维护白号池")
    p = (platform or "").strip().lower()
    if p not in WHITE_PLATFORMS:
        raise ValueError(f"platform 须为 {', '.join(WHITE_PLATFORMS)}")
    lab = (label or "").strip()
    if not lab:
        raise ValueError("label 不能为空")
    st = (status or "available").strip().lower()
    if st not in ("available", "busy", "retired"):
        raise ValueError("status 须为 available|busy|retired")
    existing = (
        await db.execute(
            select(ObsWhiteAccount).where(
                ObsWhiteAccount.platform == p,
                ObsWhiteAccount.label == lab,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.status = st
        existing.notes = notes
        existing.updated_at = datetime.utcnow()
        await db.flush()
        return existing
    row = ObsWhiteAccount(
        id=uuid.uuid4(),
        platform=p,
        label=lab,
        status=st,
        notes=notes,
        meta={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def seed_minimum_pool(db: AsyncSession, *, actor: User) -> dict[str, Any]:
    """为本机联调种子每平台 5 个占位白号（非真实账号）。"""
    created = 0
    for platform in WHITE_PLATFORMS:
        for i in range(1, MIN_PER_PLATFORM + 1):
            label = f"seed-{platform}-{i:02d}"
            before = (
                await db.execute(
                    select(ObsWhiteAccount).where(
                        ObsWhiteAccount.platform == platform,
                        ObsWhiteAccount.label == label,
                    )
                )
            ).scalar_one_or_none()
            if before:
                continue
            await upsert_account(
                db,
                actor=actor,
                platform=platform,
                label=label,
                status="available",
                notes="本机种子占位；正式验收须换成真实白号",
            )
            created += 1
    summary = await pool_summary(db)
    return {"created": created, "summary": summary}
