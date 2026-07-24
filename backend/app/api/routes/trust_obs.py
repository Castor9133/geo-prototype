"""
可信观测 API — admin 管理 + Suite 只读 latest
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession, OptionalUser
from app.models.trust_obs import TrustObsProbe, TrustObsSample
from app.services import trust_obs as service

router = APIRouter()


class ProbeUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probe_key: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=2000)
    entity_name: str = Field(default="GEO 示范栏目", max_length=200)
    entity_aliases: list[str] = Field(default_factory=list, max_length=20)
    owned_domains: list[str] = Field(default_factory=list, max_length=20)
    competitor_names: list[str] = Field(default_factory=list, max_length=20)
    prompt_version: str = Field(default="probe-v1", max_length=40)
    is_active: bool = True
    sort_order: int = Field(default=100, ge=0, le=10000)


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repeats: int = Field(default=2, ge=1, le=3)
    locale: str = Field(default="zh-CN", max_length=40)
    device: str = Field(default="api", max_length=40)
    login_state: str = Field(default="api-key", max_length=40)


class SampleRelabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_label: str = Field(min_length=1, max_length=40)


@router.get("/probes")
async def list_probes(db: DbSession, _: AdminUser):
    probes = await service.list_probes(db)
    return {"items": [service.serialize_probe(p) for p in probes]}


@router.post("/probes")
async def upsert_probe(payload: ProbeUpsertRequest, db: DbSession, _: AdminUser):
    result = await db.execute(select(TrustObsProbe).where(TrustObsProbe.probe_key == payload.probe_key))
    probe = result.scalar_one_or_none()
    if probe is None:
        probe = TrustObsProbe(probe_key=payload.probe_key.strip())
        db.add(probe)
    probe.question = payload.question.strip()
    probe.entity_name = payload.entity_name.strip() or "GEO 示范栏目"
    probe.entity_aliases = [x.strip() for x in payload.entity_aliases if x.strip()][:20]
    probe.owned_domains = [x.strip().lower() for x in payload.owned_domains if x.strip()][:20]
    probe.competitor_names = [x.strip() for x in payload.competitor_names if x.strip()][:20]
    probe.prompt_version = payload.prompt_version.strip() or "probe-v1"
    probe.is_active = bool(payload.is_active)
    probe.sort_order = int(payload.sort_order)
    await db.commit()
    await db.refresh(probe)
    return service.serialize_probe(probe)


@router.post("/runs")
async def create_run(payload: RunCreateRequest, db: DbSession, admin: AdminUser):
    run = await service.execute_run(
        db,
        user_id=admin.id,
        repeats=payload.repeats,
        locale=payload.locale,
        device=payload.device,
        login_state=payload.login_state,
    )
    _, samples = await service.get_run_with_samples(db, run.id)
    return service.serialize_run(run, samples)


@router.get("/runs")
async def list_runs(db: DbSession, _: AdminUser, limit: int = 20):
    limit = max(1, min(limit, 50))
    result = await db.execute(
        select(TrustObsRun).order_by(TrustObsRun.created_at.desc()).limit(limit)
    )
    runs = list(result.scalars().all())
    return {"items": [service.serialize_run(r) for r in runs]}


@router.get("/runs/latest")
async def latest_run(db: DbSession, _: OptionalUser):
    """Suite 只读：最近一次 completed 运行。"""
    run, samples = await service.get_latest_completed_run(db)
    if not run:
        return {
            "run": None,
            "badge": "API 自动采样（非网页抓取）",
            "method_note": service.METHOD_NOTE,
            "message": "尚无完成的采样轮次，请在后台「可信观测」点击运行。",
        }
    return {
        "run": service.serialize_run(run, samples),
        "badge": "API 自动采样（非网页抓取）",
        "method_note": service.METHOD_NOTE,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, db: DbSession, _: AdminUser):
    run, samples = await service.get_run_with_samples(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="运行不存在")
    return service.serialize_run(run, samples)


@router.patch("/samples/{sample_id}")
async def relabel_sample(sample_id: UUID, payload: SampleRelabelRequest, db: DbSession, _: AdminUser):
    allowed = {"mention", "citation", "recommendation", "co_mention", "absent", "error"}
    label = payload.primary_label.strip().lower()
    if label not in allowed:
        raise HTTPException(status_code=400, detail="不支持的标签")
    sample = await db.get(TrustObsSample, sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="样本不存在")
    sample.primary_label = label
    sample.labels = [label]
    sample.manual_override = True
    await db.commit()

    run, samples = await service.get_run_with_samples(db, sample.run_id)
    if run:
        run.aggregate = service.aggregate_labels(samples)
        await db.commit()
    await db.refresh(sample)
    return service.serialize_sample(sample)
