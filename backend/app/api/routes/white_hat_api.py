"""白号池 API：/api/obs-white-accounts"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.services import white_hat_pool as pool

router = APIRouter()


class UpsertBody(BaseModel):
    platform: str
    label: str = Field(min_length=1, max_length=120)
    status: str = "available"
    notes: str | None = None


@router.get("/summary")
async def summary(db: DbSession, _: CurrentUser):
    return await pool.pool_summary(db)


@router.get("")
@router.get("/")
async def list_accounts(
    db: DbSession,
    _: CurrentUser,
    platform: str | None = None,
    status: str | None = None,
):
    rows = await pool.list_accounts(db, platform=platform, status=status)
    return {"items": [pool.serialize_account(r) for r in rows]}


@router.post("")
@router.post("/")
async def upsert(payload: UpsertBody, db: DbSession, user: CurrentUser):
    try:
        row = await pool.upsert_account(
            db,
            actor=user,
            platform=payload.platform,
            label=payload.label,
            status=payload.status,
            notes=payload.notes,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return pool.serialize_account(row)


@router.post("/seed-minimum")
async def seed_minimum(db: DbSession, user: CurrentUser):
    try:
        out = await pool.seed_minimum_pool(db, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    await db.commit()
    return out
