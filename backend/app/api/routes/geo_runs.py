"""
GEO 回合 API — 以 run_id 贯穿诊断/拓词/内容/分发/观测 handoff
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models.content_engine import ContentPrompt, ContentTask, KnowledgeBase
from app.models.geo_run import (
    DEFAULT_COMPETITOR,
    DEFAULT_ENTITY,
    DEFAULT_OBSERVE_SCRIPT,
    DEFAULT_PLATFORMS,
    GeoRun,
)
from app.services import content_engine as ce
from app.services.geo_observe_script import load_observe_script, script_summary

router = APIRouter()


class GeoRunCreate(BaseModel):
    title: str | None = None
    entity: str = DEFAULT_ENTITY
    competitor: str = DEFAULT_COMPETITOR
    url: str | None = None
    platforms: list[str] | None = None
    knowledge_base_id: str | None = None
    observe_script_key: str = DEFAULT_OBSERVE_SCRIPT
    notes: str | None = None


class GeoRunHandoff(BaseModel):
    step: str | None = Field(default=None, description="diagnostic|knowledge|keywords|distribute|measure")
    diagnostic_report_id: str | None = None
    keyword_pack_id: str | None = None
    selected_keywords: list[str] | None = None
    knowledge_base_id: str | None = None
    task_ids: list[str] | None = None
    channel_ready: list[str] | None = None
    status: str | None = None
    url: str | None = None
    meta: dict[str, Any] | None = None


class FromKeywordsBody(BaseModel):
    keywords: list[str] = Field(min_length=1)
    knowledge_base_id: uuid.UUID | None = None
    prompt_id: uuid.UUID | None = None
    template_key: str | None = "wechat_article"
    run_generation: bool = True


def _run_dict(run: GeoRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "title": run.title,
        "entity": run.entity,
        "competitor": run.competitor,
        "url": run.url,
        "platforms": run.platforms or list(DEFAULT_PLATFORMS),
        "status": run.status,
        "artifacts": run.artifacts or {},
        "observe_script_key": run.observe_script_key,
        "notes": run.notes,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "demo_badge": "方法演示·无白号采样",
    }


def _append_step(artifacts: dict[str, Any], step: str | None, meta: dict[str, Any] | None) -> dict[str, Any]:
    steps = list(artifacts.get("steps") or [])
    steps.append(
        {
            "kind": "handoff",
            "step": step or "update",
            "at": datetime.utcnow().isoformat() + "Z",
            "meta": meta or {},
        }
    )
    artifacts["steps"] = steps[-40:]
    return artifacts


@router.post("")
@router.post("/")
async def create_geo_run(payload: GeoRunCreate, db: DbSession, _: CurrentUser):
    entity = (payload.entity or DEFAULT_ENTITY).strip() or DEFAULT_ENTITY
    title = (payload.title or "").strip() or f"{entity} · GEO 回合"
    artifacts: dict[str, Any] = {
        "steps": [
            {
                "kind": "run_created",
                "at": datetime.utcnow().isoformat() + "Z",
                "meta": {"entity": entity},
            }
        ]
    }
    if payload.knowledge_base_id:
        artifacts["knowledge_base_id"] = payload.knowledge_base_id

    run = GeoRun(
        title=title,
        entity=entity,
        competitor=(payload.competitor or DEFAULT_COMPETITOR).strip() or DEFAULT_COMPETITOR,
        url=payload.url,
        platforms=payload.platforms or list(DEFAULT_PLATFORMS),
        status="active",
        artifacts=artifacts,
        observe_script_key=payload.observe_script_key or DEFAULT_OBSERVE_SCRIPT,
        notes=payload.notes,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return _run_dict(run)


@router.get("")
@router.get("/")
async def list_geo_runs(db: DbSession, _: CurrentUser, limit: int = 20):
    rows = (
        await db.execute(select(GeoRun).order_by(GeoRun.created_at.desc()).limit(min(limit, 50)))
    ).scalars().all()
    return {"items": [_run_dict(r) for r in rows]}


@router.get("/scripts/{script_key}")
async def get_observe_script(script_key: str, _: CurrentUser):
    try:
        script = load_observe_script(script_key)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return script


@router.get("/{run_id}")
async def get_geo_run(run_id: uuid.UUID, db: DbSession, _: CurrentUser):
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")
    return _run_dict(run)


@router.get("/{run_id}/steps")
async def get_geo_run_steps(run_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """接口三问 Q3：测试智能体可读的运行可视化 Board。"""
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")
    artifacts = run.artifacts or {}
    return {
        "run_id": str(run.id),
        "status": run.status,
        "steps": artifacts.get("steps") or [],
        "artifacts": {
            k: v for k, v in artifacts.items() if k != "steps"
        },
    }


@router.get("/{run_id}/geo-preview")
async def get_geo_preview(run_id: uuid.UUID, db: DbSession, _: CurrentUser):
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")
    try:
        script = load_observe_script(run.observe_script_key)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "run_id": str(run.id),
        "demo_badge": "方法演示·无白号采样",
        "preview": script_summary(script),
        "script": script,
    }


@router.patch("/{run_id}/handoff")
async def patch_handoff(run_id: uuid.UUID, payload: GeoRunHandoff, db: DbSession, _: CurrentUser):
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")
    artifacts = dict(run.artifacts or {})
    if payload.diagnostic_report_id is not None:
        artifacts["diagnostic_report_id"] = payload.diagnostic_report_id
    if payload.keyword_pack_id is not None:
        artifacts["keyword_pack_id"] = payload.keyword_pack_id
    if payload.selected_keywords is not None:
        artifacts["selected_keywords"] = payload.selected_keywords
    if payload.knowledge_base_id is not None:
        artifacts["knowledge_base_id"] = payload.knowledge_base_id
    if payload.task_ids is not None:
        existing = list(artifacts.get("task_ids") or [])
        for tid in payload.task_ids:
            if tid not in existing:
                existing.append(tid)
        artifacts["task_ids"] = existing
    if payload.channel_ready is not None:
        artifacts["channel_ready"] = payload.channel_ready
    if payload.url is not None:
        run.url = payload.url
    if payload.status is not None:
        run.status = payload.status
    artifacts = _append_step(artifacts, payload.step, payload.meta)
    run.artifacts = artifacts
    run.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)
    return _run_dict(run)


@router.post("/{run_id}/tasks/from-keywords")
async def tasks_from_keywords(
    run_id: uuid.UUID,
    payload: FromKeywordsBody,
    db: DbSession,
    _: AdminUser,
):
    run = await db.get(GeoRun, run_id)
    if not run:
        raise HTTPException(404, "回合不存在")

    keywords = [k.strip() for k in payload.keywords if k and str(k).strip()]
    if not keywords:
        raise HTTPException(400, "请至少勾选 1 个选题")

    kb_id = payload.knowledge_base_id
    if kb_id is None:
        stored = (run.artifacts or {}).get("knowledge_base_id")
        if stored:
            try:
                kb_id = uuid.UUID(str(stored))
            except ValueError:
                kb_id = None
    if kb_id is None:
        kb = (
            await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).limit(1))
        ).scalar_one_or_none()
        if kb:
            kb_id = kb.id

    prompt_id = payload.prompt_id
    if prompt_id is None:
        prompt = (
            await db.execute(
                select(ContentPrompt)
                .where(ContentPrompt.is_active.is_(True))
                .order_by(ContentPrompt.sort_order.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if prompt:
            prompt_id = prompt.id

    created: list[dict[str, Any]] = []
    for kw in keywords[:8]:
        task = ContentTask(
            title=f"{run.entity} · {kw}"[:300],
            knowledge_base_id=kb_id,
            prompt_id=prompt_id,
            template_key=payload.template_key or "wechat_article",
            input_query=kw,
            status="pending",
            meta={
                "run_id": str(run.id),
                "entity": run.entity,
                "source": "keywords",
                "keyword": kw,
            },
        )
        db.add(task)
        await db.flush()
        if payload.run_generation:
            await ce.run_content_task(db, task.id)
            await db.refresh(task)
        created.append(
            {
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "keyword": kw,
                "draft_preview": (task.draft_body or "")[:240],
            }
        )

    artifacts = dict(run.artifacts or {})
    artifacts["selected_keywords"] = keywords
    task_ids = list(artifacts.get("task_ids") or [])
    for item in created:
        if item["id"] not in task_ids:
            task_ids.append(item["id"])
    artifacts["task_ids"] = task_ids
    if kb_id:
        artifacts["knowledge_base_id"] = str(kb_id)
    artifacts = _append_step(
        artifacts,
        "keywords",
        {"created_tasks": len(created), "keywords": keywords},
    )
    run.artifacts = artifacts
    run.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "run_id": str(run.id),
        "tasks": created,
        "distribute_path": f"/distribute?run_id={run.id}",
    }
