"""真实点名观测 API — 挂在 /api/geo-runs/{run_id}/real-obs/*"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import DbSession, OptionalUser
from app.models.geo_run import GeoRun
from app.services import real_obs as service

router = APIRouter()


class SnapshotCreate(BaseModel):
    phase: str = Field(default="after", description="baseline|after")
    platforms: list[str] | None = None
    questions: list[dict[str, Any] | str] | None = None
    owned_domains: list[str] | None = None
    fact_source_urls: list[str] | None = None
    entity_aliases: list[str] | None = None
    published_at: datetime | None = Field(
        default=None, description="人工确认已外发时间；缺省则 after 用当前 UTC"
    )
    prompt_pack_version: str = "manual-v1"


class SampleIngest(BaseModel):
    question_id: str
    platform: str
    attempt: int = 1
    answer_text: str | None = None
    citations: list[Any] | None = None
    ok: bool = True
    error_message: str | None = None
    raw_meta: dict[str, Any] | None = None
    sampled_at: datetime | None = None


class SampleBatchIngest(BaseModel):
    samples: list[SampleIngest] = Field(min_length=1)


class SampleOverride(BaseModel):
    mention: bool | None = None
    owned_citation: bool | None = None
    strong_adopted: bool | None = None
    competitor_mention: bool | None = None


async def _get_run(db: DbSession, run_id: uuid.UUID) -> GeoRun:
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")
    return run


@router.post("/{run_id}/real-obs/snapshots")
async def create_real_obs_snapshot(
    run_id: uuid.UUID,
    payload: SnapshotCreate,
    db: DbSession,
    _: OptionalUser,
):
    run = await _get_run(db, run_id)
    try:
        snap = await service.create_snapshot(
            db,
            run,
            phase=payload.phase,
            platforms=payload.platforms,
            questions=payload.questions,
            owned_domains=payload.owned_domains,
            fact_source_urls=payload.fact_source_urls,
            entity_aliases=payload.entity_aliases,
            published_at=payload.published_at,
            prompt_pack_version=payload.prompt_pack_version,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "snapshot": service.serialize_snapshot(snap),
        "job": service.build_probe_job(run, snap),
        "disclaimer": service.METHOD_NOTE,
    }


@router.get("/{run_id}/real-obs/snapshots")
async def list_real_obs_snapshots(run_id: uuid.UUID, db: DbSession, _: OptionalUser):
    await _get_run(db, run_id)
    snaps = await service.list_snapshots(db, run_id)
    return {
        "items": [service.serialize_snapshot(s) for s in snaps],
        "disclaimer": service.METHOD_NOTE,
    }


@router.get("/{run_id}/real-obs/snapshots/{snapshot_id}")
async def get_real_obs_snapshot(
    run_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: DbSession,
    _: OptionalUser,
):
    run = await _get_run(db, run_id)
    snap = await service.get_snapshot(db, snapshot_id)
    if not snap or snap.geo_run_id != run_id:
        raise HTTPException(404, "快照不存在")
    samples = await service.list_samples(db, snapshot_id)
    return {
        "snapshot": service.serialize_snapshot(snap),
        "samples": [service.serialize_sample(s) for s in samples],
        "job": service.build_probe_job(run, snap),
        "disclaimer": service.METHOD_NOTE,
    }


@router.post("/{run_id}/real-obs/snapshots/{snapshot_id}/start")
async def start_real_obs_sampling(
    run_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: DbSession,
    _: OptionalUser,
):
    run = await _get_run(db, run_id)
    snap = await service.get_snapshot(db, snapshot_id)
    if not snap or snap.geo_run_id != run_id:
        raise HTTPException(404, "快照不存在")
    snap = await service.mark_sampling(db, snap, run)
    return {"snapshot": service.serialize_snapshot(snap), "job": service.build_probe_job(run, snap)}


@router.post("/{run_id}/real-obs/snapshots/{snapshot_id}/samples")
async def ingest_real_obs_sample(
    run_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    payload: SampleIngest,
    db: DbSession,
    _: OptionalUser,
):
    run = await _get_run(db, run_id)
    snap = await service.get_snapshot(db, snapshot_id)
    if not snap or snap.geo_run_id != run_id:
        raise HTTPException(404, "快照不存在")
    try:
        sample = await service.upsert_sample(
            db,
            run,
            snap,
            question_id=payload.question_id,
            platform=payload.platform,
            attempt=payload.attempt,
            answer_text=payload.answer_text,
            citations=payload.citations,
            ok=payload.ok,
            error_message=payload.error_message,
            raw_meta=payload.raw_meta,
            sampled_at=payload.sampled_at,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    snap = await service.get_snapshot(db, snapshot_id)
    return {
        "sample": service.serialize_sample(sample),
        "snapshot": service.serialize_snapshot(snap) if snap else None,
    }


@router.post("/{run_id}/real-obs/snapshots/{snapshot_id}/samples/batch")
async def ingest_real_obs_samples_batch(
    run_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    payload: SampleBatchIngest,
    db: DbSession,
    _: OptionalUser,
):
    run = await _get_run(db, run_id)
    snap = await service.get_snapshot(db, snapshot_id)
    if not snap or snap.geo_run_id != run_id:
        raise HTTPException(404, "快照不存在")
    results = []
    for item in payload.samples:
        try:
            sample = await service.upsert_sample(
                db,
                run,
                snap,
                question_id=item.question_id,
                platform=item.platform,
                attempt=item.attempt,
                answer_text=item.answer_text,
                citations=item.citations,
                ok=item.ok,
                error_message=item.error_message,
                raw_meta=item.raw_meta,
                sampled_at=item.sampled_at,
            )
            results.append(service.serialize_sample(sample))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        snap = await service.get_snapshot(db, snapshot_id)
        if not snap:
            raise HTTPException(404, "快照不存在")
    return {
        "samples": results,
        "snapshot": service.serialize_snapshot(snap),
    }


@router.patch("/{run_id}/real-obs/samples/{sample_id}")
async def override_real_obs_sample(
    run_id: uuid.UUID,
    sample_id: uuid.UUID,
    payload: SampleOverride,
    db: DbSession,
    _: OptionalUser,
):
    await _get_run(db, run_id)
    from app.models.real_obs import RealObsSample

    sample = await db.get(RealObsSample, sample_id)
    if not sample or sample.geo_run_id != run_id:
        raise HTTPException(404, "样本不存在")
    sample = await service.override_sample_labels(
        db,
        sample,
        mention=payload.mention,
        owned_citation=payload.owned_citation,
        strong_adopted=payload.strong_adopted,
        competitor_mention=payload.competitor_mention,
    )
    return {"sample": service.serialize_sample(sample)}


@router.get("/{run_id}/real-obs/compare")
async def compare_real_obs(run_id: uuid.UUID, db: DbSession, _: OptionalUser):
    run = await _get_run(db, run_id)
    return await service.compare_run(db, run)
