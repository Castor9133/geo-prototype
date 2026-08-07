"""GEO 策略 API：/api/geo-strategies"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.content_engine import KnowledgeBase, KnowledgeDocument
from app.models.geo_run import GeoRun
from app.models.geo_strategy import GeoStrategy
from app.models.real_obs import RealObsSnapshot
from app.services import geo_strategy_svc as svc
from app.services import real_obs as real_obs_svc
from app.services.geo_kb import serialize_task

router = APIRouter()


class SeedBody(BaseModel):
    platform: str
    question_class: str
    gap_note: str = Field(min_length=1)
    title: str | None = None
    knowledge_base_id: uuid.UUID | None = None
    geo_run_id: uuid.UUID | None = None


class CreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    platform: str
    question_class: str
    content_orientation: str = ""
    query_variants: list[str] = Field(default_factory=list)
    channel_matrix: dict[str, Any] | None = None
    success_signal: dict[str, Any] | None = None
    knowledge_document_ids: list[str] = Field(default_factory=list)
    knowledge_tag_pack: dict[str, Any] = Field(default_factory=dict)
    knowledge_base_id: uuid.UUID | None = None
    geo_run_id: uuid.UUID | None = None
    gap_note: str | None = None


class PatchBody(BaseModel):
    title: str | None = None
    platform: str | None = None
    question_class: str | None = None
    content_orientation: str | None = None
    query_variants: list[str] | None = None
    channel_matrix: dict[str, Any] | None = None
    success_signal: dict[str, Any] | None = None
    knowledge_document_ids: list[str] | None = None
    knowledge_tag_pack: dict[str, Any] | None = None
    knowledge_base_id: uuid.UUID | None = None
    geo_run_id: uuid.UUID | None = None
    gap_note: str | None = None


class DeployBody(BaseModel):
    site_url: str = Field(min_length=1)
    media_channel_type: str
    media_url: str = Field(min_length=1)


class AttachTaskBody(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content_kind: str = "deep"
    prompt_id: uuid.UUID | None = None
    generate: bool = Field(default=False, description="挂载后立即 LLM 生成模板稿")


class VerdictBody(BaseModel):
    verdict: str | None = Field(default=None, description="effective|partial|ineffective，空则用建议")
    force_reason: str | None = Field(default=None, description="管理员强开判定（正式模式样本不足时）")


class ApproveBody(BaseModel):
    force_reason: str | None = Field(default=None, description="管理员强开批准（正式模式摸底样本不足时）")


class ForceBody(BaseModel):
    reason: str = Field(min_length=1)


class AttachDiagnosticBody(BaseModel):
    diagnostic_report_id: uuid.UUID


class FromDiagnosticBody(BaseModel):
    diagnostic_report_id: uuid.UUID
    platform: str = "doubao"
    question_class: str | None = None
    title: str | None = None


class ConfirmQueriesBody(BaseModel):
    query_variants: list[str] = Field(min_length=3)


class ObsSampleItem(BaseModel):
    question_text: str | None = None
    question_id: str | None = None
    mention: bool = False
    citation_rank: int | None = None
    citation_url: str | None = None
    citation_title: str | None = None
    owned_citation: bool = False
    strong_adopted: bool = False
    answer_text: str | None = None
    informal: bool = False
    competitor_mention: bool = False
    diagnosis_type: str | None = None


class RecordObsBody(BaseModel):
    phase: str = Field(description="baseline|after")
    account_label: str | None = None
    samples: list[ObsSampleItem] = Field(min_length=1)


async def _get(db: DbSession, strategy_id: uuid.UUID) -> GeoStrategy:
    s = await db.get(GeoStrategy, strategy_id)
    if not s:
        raise HTTPException(404, "策略不存在")
    return s


async def _ser(db: DbSession, s: GeoStrategy) -> dict:
    summary = await svc.task_summary_for(db, s.id)
    return svc.serialize_strategy(s, task_summary=summary)


@router.get("")
@router.get("/")
async def list_strategies(
    db: DbSession,
    _: CurrentUser,
    status: str | None = None,
    platform: str | None = None,
    limit: int = 50,
):
    rows = await svc.list_strategies(db, status=status, platform=platform, limit=limit)
    items = []
    for s in rows:
        items.append(await _ser(db, s))
    return {"items": items}


@router.get("/options")
async def strategy_form_options(db: DbSession, _: CurrentUser, run_limit: int = 40):
    """新建/编辑策略用的下拉选项：知识库 + 观测任务 + 已入库素材（无需手工复制 UUID）。"""
    kbs = (
        await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).limit(80))
    ).scalars().all()
    runs = (
        await db.execute(
            select(GeoRun).order_by(GeoRun.created_at.desc()).limit(min(max(run_limit, 1), 80))
        )
    ).scalars().all()
    docs = (
        await db.execute(
            select(KnowledgeDocument)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    kb_name = {str(kb.id): (kb.name or kb.slug or "未命名知识库") for kb in kbs}
    return {
        "knowledge_bases": [
            {
                "id": str(kb.id),
                "name": kb.name,
                "slug": kb.slug,
                "doc_count": kb.doc_count or 0,
                "source_label": kb.source_label,
            }
            for kb in kbs
        ],
        "geo_runs": [
            {
                "id": str(run.id),
                "title": run.title or run.entity or "未命名观测任务",
                "entity": run.entity,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in runs
        ],
        "documents": [
            {
                "id": str(d.id),
                "title": d.title or "未命名素材",
                "knowledge_base_id": str(d.knowledge_base_id),
                "knowledge_base_name": kb_name.get(str(d.knowledge_base_id), ""),
                "status": d.status,
                "tier": getattr(d, "tier", None) or "L2",
            }
            for d in docs
        ],
    }


@router.post("/seed")
async def seed_strategy(payload: SeedBody, db: DbSession, user: CurrentUser):
    try:
        s = await svc.create_from_seed(
            db,
            actor=user,
            platform=payload.platform,
            question_class=payload.question_class,
            gap_note=payload.gap_note,
            title=payload.title,
            knowledge_base_id=payload.knowledge_base_id,
            geo_run_id=payload.geo_run_id,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/from-diagnostic")
async def from_diagnostic(payload: FromDiagnosticBody, db: DbSession, user: CurrentUser):
    """查页面完成后一键建选题草稿并挂诊断。"""
    try:
        s = await svc.create_from_diagnostic(
            db,
            actor=user,
            diagnostic_report_id=payload.diagnostic_report_id,
            platform=payload.platform,
            question_class=payload.question_class,
            title=payload.title,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/")
async def create_strategy(payload: CreateBody, db: DbSession, user: CurrentUser):
    try:
        s = await svc.create_strategy(
            db,
            actor=user,
            title=payload.title,
            platform=payload.platform,
            question_class=payload.question_class,
            content_orientation=payload.content_orientation,
            query_variants=payload.query_variants,
            channel_matrix=payload.channel_matrix,
            success_signal=payload.success_signal,
            knowledge_document_ids=payload.knowledge_document_ids,
            knowledge_tag_pack=payload.knowledge_tag_pack,
            knowledge_base_id=payload.knowledge_base_id,
            geo_run_id=payload.geo_run_id,
            gap_note=payload.gap_note,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: uuid.UUID, db: DbSession, _: CurrentUser):
    s = await _get(db, strategy_id)
    return await _ser(db, s)


@router.patch("/{strategy_id}")
async def patch_strategy(strategy_id: uuid.UUID, payload: PatchBody, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.update_draft(db, s, actor=user, **payload.model_dump(exclude_unset=True))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/attach-diagnostic")
async def attach_diagnostic(
    strategy_id: uuid.UUID, payload: AttachDiagnosticBody, db: DbSession, user: CurrentUser
):
    s = await _get(db, strategy_id)
    try:
        s = await svc.attach_diagnostic(
            db, s, actor=user, diagnostic_report_id=payload.diagnostic_report_id
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/register-baseline")
async def register_baseline(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    """② 挂接 baseline 快照。无白号时创建 pending 占位，不跑浏览器采样。"""
    s = await _get(db, strategy_id)
    try:
        s = await svc.register_baseline_snapshot(db, s, actor=user, create_pending=True)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/record-obs-samples")
async def record_obs_samples(strategy_id: uuid.UUID, payload: RecordObsBody, db: DbSession, user: CurrentUser):
    """回传白号摸底/复测样本（半自动）。"""
    s = await _get(db, strategy_id)
    try:
        s = await svc.record_obs_samples(
            db,
            s,
            actor=user,
            phase=payload.phase,
            samples=[item.model_dump() for item in payload.samples],
            account_label=payload.account_label,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.get("/{strategy_id}/obs-sample-sheet.csv")
async def download_strategy_obs_sheet(
    strategy_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    phase: str = "baseline",
):
    """按策略导出摸底/复测答题卡 CSV。"""
    s = await _get(db, strategy_id)
    ph = (phase or "baseline").strip().lower()
    snap_id = s.baseline_snapshot_id if ph == "baseline" else s.after_snapshot_id
    if not snap_id:
        raise HTTPException(400, "请先建立摸底/复测快照后再下载答题卡")
    snap = await db.get(RealObsSnapshot, snap_id)
    if not snap:
        raise HTTPException(404, "快照不存在")
    body = real_obs_svc.build_sample_sheet_csv(snap, platform=s.platform)
    filename = f"strategy-{strategy_id}-{ph}-sample-sheet.csv"
    return Response(
        content=body.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{strategy_id}/obs-citation-rankings")
async def strategy_obs_citation_rankings(
    strategy_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    phase: str = "baseline",
    limit: int = 50,
):
    """当前策略摸底/复测快照的引用域名与引用文章排行。"""
    s = await _get(db, strategy_id)
    ph = (phase or "baseline").strip().lower()
    if ph not in ("baseline", "after"):
        raise HTTPException(400, "phase 须为 baseline 或 after")
    snap_id = s.baseline_snapshot_id if ph == "baseline" else s.after_snapshot_id
    if not snap_id:
        return {
            "phase": ph,
            "strategy_id": str(s.id),
            "snapshot_id": None,
            "range_label": "",
            "sample_count": 0,
            "citation_event_count": 0,
            "domains": [],
            "articles": [],
            "domain_total": 0,
            "article_total": 0,
        }
    snap = await db.get(RealObsSnapshot, snap_id)
    if not snap:
        raise HTTPException(404, "快照不存在")
    samples = await real_obs_svc.list_samples(db, snap_id)
    rankings = real_obs_svc.build_citation_rankings(samples, limit=limit)
    start = snap.created_at or snap.started_at
    end = snap.finished_at or snap.updated_at or start
    range_label = ""
    if start:
        range_label = start.strftime("%Y-%m-%d")
        if end and end.date() != start.date():
            range_label += " ~ " + end.strftime("%Y-%m-%d")
    return {
        "phase": ph,
        "strategy_id": str(s.id),
        "snapshot_id": str(snap.id),
        "range_label": range_label,
        "platform": s.platform,
        **rankings,
    }


@router.post("/{strategy_id}/obs-sample-sheet")
async def upload_strategy_obs_sheet(
    strategy_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    phase: str = "baseline",
    file: UploadFile = File(...),
):
    """上传答题卡 CSV → 写入观测样本（同 record-obs-samples）。"""
    s = await _get(db, strategy_id)
    ph = (phase or "baseline").strip().lower()
    snap_id = s.baseline_snapshot_id if ph == "baseline" else s.after_snapshot_id
    if not snap_id:
        raise HTTPException(400, "请先建立摸底/复测快照后再上传答题卡")
    snap = await db.get(RealObsSnapshot, snap_id)
    if not snap:
        raise HTTPException(404, "快照不存在")
    qmap = {
        str(q.get("id")): str(q.get("text") or "")
        for q in (snap.questions or [])
        if isinstance(q, dict)
    }
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="replace")
    try:
        items = real_obs_svc.parse_sample_sheet_csv(text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    # 策略页按本策略平台过滤；同问法多行取第一条匹配平台
    plat = (s.platform or "").strip().lower()
    samples_for_strategy = []
    seen_q: set[str] = set()
    for item in items:
        if plat and item["platform"] != plat:
            continue
        qid = item["question_id"]
        if qid in seen_q:
            continue
        seen_q.add(qid)
        meta = item.get("raw_meta") or {}
        samples_for_strategy.append(
            {
                "question_id": qid,
                "question_text": qmap.get(qid) or "",
                "mention": bool(meta.get("sheet_mention")),
                "competitor_mention": bool(meta.get("sheet_competitor_mention")),
                "owned_citation": bool(meta.get("sheet_owned_citation")),
                "citation_rank": meta.get("citation_rank"),
                "diagnosis_type": meta.get("diagnosis_override"),
                "answer_text": item.get("answer_text"),
                "informal": True,
            }
        )
    if not samples_for_strategy:
        raise HTTPException(400, f"CSV 中没有平台为 {plat or '策略平台'} 的有效行")
    try:
        s = await svc.record_obs_samples(
            db,
            s,
            actor=user,
            phase=ph,
            samples=samples_for_strategy,
            account_label="sample-sheet-csv",
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.get("/{strategy_id}/handoff-checklist")
async def get_handoff_checklist(strategy_id: uuid.UUID, db: DbSession, _: CurrentUser):
    s = await _get(db, strategy_id)
    summary = await svc.task_summary_for(db, s.id)
    return svc.handoff_checklist(s, task_summary=summary)


@router.post("/{strategy_id}/confirm-queries")
async def confirm_queries(strategy_id: uuid.UUID, payload: ConfirmQueriesBody, db: DbSession, user: CurrentUser):
    """拓词确认：写回观测问法（写稿前置）。"""
    s = await _get(db, strategy_id)
    try:
        s = await svc.confirm_query_pack(
            db, s, actor=user, query_variants=payload.query_variants
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/submit")
async def submit_strategy(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.submit_for_approval(db, s, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/approve")
async def approve_strategy(
    strategy_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    payload: ApproveBody | None = None,
):
    s = await _get(db, strategy_id)
    try:
        s = await svc.approve_executable(
            db,
            s,
            actor=user,
            force_reason=(payload.force_reason if payload else None),
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/tasks")
async def attach_task(strategy_id: uuid.UUID, payload: AttachTaskBody, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        task = await svc.attach_task(
            db,
            s,
            actor=user,
            title=payload.title,
            content_kind=payload.content_kind,
            prompt_id=payload.prompt_id,
        )
        if payload.generate:
            task = await svc.generate_task_draft(db, s, task, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return serialize_task(task)


@router.post("/{strategy_id}/tasks/{task_id}/generate")
async def generate_strategy_task(
    strategy_id: uuid.UUID, task_id: uuid.UUID, db: DbSession, user: CurrentUser
):
    s = await _get(db, strategy_id)
    from app.models.content_engine import ContentTask

    task = await db.get(ContentTask, task_id)
    if not task or task.strategy_id != s.id:
        raise HTTPException(404, "任务不存在或不属于该策略")
    try:
        task = await svc.generate_task_draft(db, s, task, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(task)
    return serialize_task(task)


@router.get("/{strategy_id}/tasks")
async def list_strategy_tasks(strategy_id: uuid.UUID, db: DbSession, _: CurrentUser):
    await _get(db, strategy_id)
    from app.models.content_engine import ContentTask

    rows = (
        await db.execute(
            select(ContentTask)
            .where(ContentTask.strategy_id == strategy_id)
            .order_by(ContentTask.created_at.desc())
        )
    ).scalars().all()
    return {"items": [serialize_task(t) for t in rows]}


@router.post("/{strategy_id}/deploy")
async def deploy_strategy(strategy_id: uuid.UUID, payload: DeployBody, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.mark_deployed(
            db,
            s,
            actor=user,
            site_url=payload.site_url,
            media_channel_type=payload.media_channel_type,
            media_url=payload.media_url,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.get("/{strategy_id}/verdict-suggestion")
async def verdict_suggestion(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        return await svc.compute_verdict_suggestion(db, s)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{strategy_id}/confirm-verdict")
async def confirm_verdict(strategy_id: uuid.UUID, payload: VerdictBody, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.confirm_verdict(
            db,
            s,
            actor=user,
            verdict=payload.verdict,
            force_reason=payload.force_reason,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/fork")
async def fork_strategy(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        child = await svc.fork_new_version(db, s, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(child)
    return await _ser(db, child)


@router.post("/{strategy_id}/force/initiate")
async def force_initiate(strategy_id: uuid.UUID, payload: ForceBody, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.force_initiate(db, s, actor=user, reason=payload.reason)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/force/business-confirm")
async def force_business(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.force_business_confirm(db, s, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/force/admin-confirm")
async def force_admin(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    try:
        s = await svc.force_admin_confirm(db, s, actor=user)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)


@router.post("/{strategy_id}/start-observe")
async def start_observe(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    """⑤后：按策略问法×单平台建白号观测快照（须已投放且全稿 ready）。"""
    from app.services import real_obs as real_obs_svc

    s = await _get(db, strategy_id)
    if s.status not in ("deployed", "observing"):
        raise HTTPException(400, "须先已投放")
    summary = await svc.task_summary_for(db, s.id)
    if not summary["all_ready"]:
        raise HTTPException(400, "全部执行物须已连续过审")
    variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
    if len(variants) < 3:
        raise HTTPException(400, "至少 3 条观测问法")
    if not s.geo_run_id:
        raise HTTPException(400, "策略须绑定 geo_run_id 以挂接 real_obs 快照")
    run = await db.get(GeoRun, s.geo_run_id)
    if not run:
        raise HTTPException(404, "关联 geo_run 不存在")
    questions = [{"id": f"q{i+1}", "text": t} for i, t in enumerate(variants)]
    owned = []
    if s.site_url:
        from urllib.parse import urlparse

        host = urlparse(s.site_url).netloc
        if host:
            owned = [host]
    try:
        snap = await real_obs_svc.create_snapshot(
            db,
            run,
            phase="after",
            platforms=[s.platform],
            questions=questions,
            owned_domains=owned or None,
            fact_source_urls=[s.site_url] if s.site_url else None,
            published_at=s.deployed_at,
            prompt_pack_version=f"strategy-v{s.version}",
            strategy_id=s.id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.status = "observing"
    s.after_snapshot_id = snap.id
    meta = dict(s.meta or {})
    meta["after_pending"] = True
    meta["after_note"] = "after 快照已建；白号采样回传另测"
    s.meta = meta
    await db.commit()
    await db.refresh(s)
    await db.refresh(snap)
    return {
        "strategy": await _ser(db, s),
        "snapshot": real_obs_svc.serialize_snapshot(snap),
        "job": real_obs_svc.build_probe_job(run, snap),
        "disclaimer": real_obs_svc.METHOD_NOTE,
        "obs_sampling_deferred": True,
    }


@router.post("/{strategy_id}/confirm-promote-l2")
async def confirm_promote_l2(strategy_id: uuid.UUID, db: DbSession, user: CurrentUser):
    s = await _get(db, strategy_id)
    if not s.knowledge_base_id:
        raise HTTPException(400, "策略未绑定知识库")
    kb = await db.get(KnowledgeBase, s.knowledge_base_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    try:
        s = await svc.confirm_promote_l2(db, s, actor=user, kb=kb)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    await db.refresh(s)
    return await _ser(db, s)
