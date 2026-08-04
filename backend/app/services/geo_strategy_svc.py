"""GEO 策略服务：六元组校验、审批、投放、观测判定、版本迭代、强制沉淀。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_engine import ContentTask, KnowledgeBase
from app.models.geo_strategy import (
    MEDIA_CHANNEL_TYPES,
    STRATEGY_PLATFORMS,
    GeoStrategy,
)
from app.models.real_obs import RealObsSample, RealObsSnapshot
from app.models.user import User
from app.services import geo_kb as gkb
from app.services.geo_roles import has_business_geo_role, is_platform_admin


def _as_uuid_list(raw: list | None) -> list[str]:
    out: list[str] = []
    for item in raw or []:
        out.append(str(item))
    return out


def serialize_strategy(s: GeoStrategy, *, task_summary: dict | None = None) -> dict[str, Any]:
    checklist = handoff_checklist(s, task_summary=task_summary)
    return {
        "id": str(s.id),
        "title": s.title,
        "platform": s.platform,
        "question_class": s.question_class,
        "query_variants": list(s.query_variants or []),
        "content_orientation": s.content_orientation or "",
        "channel_matrix": dict(s.channel_matrix or {}),
        "success_signal": dict(s.success_signal or {}),
        "knowledge_document_ids": _as_uuid_list(s.knowledge_document_ids),
        "knowledge_tag_pack": dict(s.knowledge_tag_pack or {}),
        "knowledge_base_id": str(s.knowledge_base_id) if s.knowledge_base_id else None,
        "geo_run_id": str(s.geo_run_id) if s.geo_run_id else None,
        "diagnostic_report_id": str(s.diagnostic_report_id) if s.diagnostic_report_id else None,
        "baseline_snapshot_id": str(s.baseline_snapshot_id) if s.baseline_snapshot_id else None,
        "after_snapshot_id": str(s.after_snapshot_id) if s.after_snapshot_id else None,
        "version": s.version,
        "parent_strategy_id": str(s.parent_strategy_id) if s.parent_strategy_id else None,
        "status": s.status,
        "created_by": str(s.created_by) if s.created_by else None,
        "approved_by": str(s.approved_by) if s.approved_by else None,
        "approved_at": s.approved_at.isoformat() if s.approved_at else None,
        "site_url": s.site_url,
        "media_channel_type": s.media_channel_type,
        "media_url": s.media_url,
        "deployed_at": s.deployed_at.isoformat() if s.deployed_at else None,
        "verdict": s.verdict,
        "verdict_detail": dict(s.verdict_detail or {}),
        "judged_at": s.judged_at.isoformat() if s.judged_at else None,
        "force_status": s.force_status,
        "force_reason": s.force_reason,
        "promote_suggestion": s.promote_suggestion,
        "promoted_document_ids": _as_uuid_list(s.promoted_document_ids),
        "gap_note": s.gap_note,
        "meta": dict(s.meta or {}),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "task_summary": task_summary,
        "handoff_checklist": checklist,
    }


def validate_six_tuple(s: GeoStrategy, *, for_executable: bool = False) -> None:
    if s.platform not in STRATEGY_PLATFORMS:
        raise ValueError(f"platform 须为 {', '.join(STRATEGY_PLATFORMS)}")
    if not (s.question_class or "").strip():
        raise ValueError("问题类不能为空")
    if not (s.content_orientation or "").strip():
        raise ValueError("内容供给取向不能为空")
    docs = s.knowledge_document_ids or []
    tags = s.knowledge_tag_pack or {}
    if for_executable:
        if not docs:
            raise ValueError("知识绑定：文档集不能为空")
        if not tags:
            raise ValueError("知识绑定：标签/主题包不能为空")
        variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
        if len(variants) < 3:
            raise ValueError("问题类至少 3 条观测问法")
        matrix = s.channel_matrix or {}
        if not matrix.get("site_required", True):
            raise ValueError("渠道矩阵须包含第一现场官网")
        media_types = matrix.get("media_types") or matrix.get("media") or []
        if not media_types:
            raise ValueError("渠道矩阵须声明至少一个媒体号类型")
        sig = s.success_signal or {}
        if not sig.get("mode"):
            s.success_signal = {"mode": "mention_top10", "top_n": 10}


async def create_strategy(
    db: AsyncSession,
    *,
    actor: User,
    title: str,
    platform: str,
    question_class: str,
    content_orientation: str = "",
    query_variants: list[str] | None = None,
    channel_matrix: dict | None = None,
    success_signal: dict | None = None,
    knowledge_document_ids: list[str] | None = None,
    knowledge_tag_pack: dict | None = None,
    knowledge_base_id: uuid.UUID | None = None,
    geo_run_id: uuid.UUID | None = None,
    gap_note: str | None = None,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor 或 reviewer 起草策略")
    s = GeoStrategy(
        title=title.strip(),
        platform=platform.strip().lower(),
        question_class=question_class.strip(),
        content_orientation=(content_orientation or "").strip(),
        query_variants=list(query_variants or []),
        channel_matrix=channel_matrix
        or {"site_required": True, "media_types": ["wechat"]},
        success_signal=success_signal or {"mode": "mention_top10", "top_n": 10},
        knowledge_document_ids=list(knowledge_document_ids or []),
        knowledge_tag_pack=dict(knowledge_tag_pack or {}),
        knowledge_base_id=knowledge_base_id,
        geo_run_id=geo_run_id,
        gap_note=gap_note,
        status="draft",
        version=1,
        created_by=actor.id,
        force_status="none",
    )
    validate_six_tuple(s, for_executable=False)
    db.add(s)
    await db.flush()
    return s


async def create_from_seed(
    db: AsyncSession,
    *,
    actor: User,
    platform: str,
    question_class: str,
    gap_note: str,
    title: str | None = None,
    knowledge_base_id: uuid.UUID | None = None,
    geo_run_id: uuid.UUID | None = None,
) -> GeoStrategy:
    """① 缺口感知 → 策略草稿种子。"""
    return await create_strategy(
        db,
        actor=actor,
        title=title or f"[草稿] {question_class} · {platform}",
        platform=platform,
        question_class=question_class,
        content_orientation="待补：深文 + FAQ/短答供给取向",
        query_variants=[],
        gap_note=gap_note,
        knowledge_base_id=knowledge_base_id,
        geo_run_id=geo_run_id,
    )


async def update_draft(db: AsyncSession, s: GeoStrategy, *, actor: User, **fields: Any) -> GeoStrategy:
    if s.status not in ("draft", "pending_review", "executable"):
        raise ValueError("判定后的策略不可原地改字段，请开新版本")
    if s.status == "executable" and fields:
        # 投放前可改；可执行后若已投放则禁止
        pass
    if s.deployed_at:
        raise ValueError("已投放策略不可原地改六元组，请判定后开新版本或先回滚状态")
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    for key in (
        "title",
        "platform",
        "question_class",
        "content_orientation",
        "gap_note",
    ):
        if key in fields and fields[key] is not None:
            setattr(s, key, fields[key] if key != "platform" else str(fields[key]).lower())
    if "query_variants" in fields and fields["query_variants"] is not None:
        s.query_variants = list(fields["query_variants"])
    if "channel_matrix" in fields and fields["channel_matrix"] is not None:
        s.channel_matrix = dict(fields["channel_matrix"])
    if "success_signal" in fields and fields["success_signal"] is not None:
        s.success_signal = dict(fields["success_signal"])
    if "knowledge_document_ids" in fields and fields["knowledge_document_ids"] is not None:
        s.knowledge_document_ids = [str(x) for x in fields["knowledge_document_ids"]]
    if "knowledge_tag_pack" in fields and fields["knowledge_tag_pack"] is not None:
        s.knowledge_tag_pack = dict(fields["knowledge_tag_pack"])
    if "knowledge_base_id" in fields:
        s.knowledge_base_id = fields["knowledge_base_id"]
    if "geo_run_id" in fields:
        s.geo_run_id = fields["geo_run_id"]
    if s.status == "pending_review":
        s.status = "draft"
    validate_six_tuple(s, for_executable=False)
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def submit_for_approval(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor 提交审批")
    if s.status not in ("draft", "pending_review"):
        raise ValueError("仅草稿可提交审批")
    validate_six_tuple(s, for_executable=True)
    s.status = "pending_review"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


def handoff_checklist(s: GeoStrategy, *, task_summary: dict | None = None) -> dict[str, Any]:
    """环间交付物检查表（①–⑨）。观测白号采样本身不在此强制执行。"""
    ts = task_summary or {}
    items = [
        {
            "step": "①页面诊断",
            "key": "diagnostic",
            "ok": bool(s.diagnostic_report_id),
            "deliverable": "已挂接诊断报告",
        },
        {
            "step": "②投放前摸底",
            "key": "baseline",
            "ok": bool(s.baseline_snapshot_id),
            "deliverable": "已登记摸底结果",
            "note": "正式验收须用白号提问回传；可先占位",
        },
        {
            "step": "③策略已批可开工",
            "key": "executable",
            "ok": s.status in (
                "executable",
                "deployed",
                "observing",
                "effective",
                "partial",
                "ineffective",
            ),
            "deliverable": "审核已通过",
        },
        {
            "step": "④素材已备齐",
            "key": "knowledge",
            "ok": bool(s.knowledge_document_ids) and bool(s.knowledge_tag_pack),
            "deliverable": "已指定用哪些稿 + 主题标签",
        },
        {
            "step": "⑤稿件已过审",
            "key": "tasks_ready",
            "ok": bool(ts.get("all_ready")),
            "deliverable": "至少2篇且全部过审",
        },
        {
            "step": "⑥已对外发布",
            "key": "deployed",
            "ok": bool(s.site_url and s.media_url and s.deployed_at),
            "deliverable": "官网链接 + 媒体号链接已登记",
        },
        {
            "step": "⑦投放后复测",
            "key": "after",
            "ok": bool(s.after_snapshot_id),
            "deliverable": "已建复测记录",
            "note": "正式验收须白号复测",
        },
        {
            "step": "⑧效果已判定",
            "key": "verdict",
            "ok": s.verdict in ("effective", "partial", "ineffective"),
            "deliverable": "生效 / 部分见效 / 未见效",
        },
    ]
    return {
        "items": items,
        "ready_for_approve": bool(s.diagnostic_report_id and s.baseline_snapshot_id),
        "ready_for_deploy": bool(ts.get("all_ready")),
        "obs_white_hat_deferred": True,
    }


async def attach_diagnostic(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    diagnostic_report_id: uuid.UUID,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    from app.models.diagnostic import DiagnosticReport

    report = await db.get(DiagnosticReport, diagnostic_report_id)
    if not report:
        raise ValueError("诊断报告不存在")
    s.diagnostic_report_id = diagnostic_report_id
    meta = dict(s.meta or {})
    meta["diagnostic_url"] = report.url
    meta["diagnostic_status"] = (
        report.status.value if hasattr(report.status, "value") else str(report.status)
    )
    s.meta = meta
    if not s.gap_note:
        s.gap_note = f"诊断缺口接入：{report.url}"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def register_baseline_snapshot(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    create_pending: bool = True,
) -> GeoStrategy:
    """② 挂接 baseline。无白号时创建 pending 快照占位（不执行浏览器采样）。"""
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
    if len(variants) < 3:
        raise ValueError("登记 baseline 前须有 ≥3 条问法")
    if not s.geo_run_id:
        raise ValueError("须绑定 geo_run_id")
    from app.models.geo_run import GeoRun
    from app.services import real_obs as real_obs_svc

    run = await db.get(GeoRun, s.geo_run_id)
    if not run:
        raise ValueError("关联 geo_run 不存在")
    if create_pending or not s.baseline_snapshot_id:
        questions = [{"id": f"bq{i+1}", "text": t} for i, t in enumerate(variants)]
        snap = await real_obs_svc.create_snapshot(
            db,
            run,
            phase="baseline",
            platforms=[s.platform],
            questions=questions,
            prompt_pack_version=f"strategy-baseline-v{s.version}",
            strategy_id=s.id,
        )
        s.baseline_snapshot_id = snap.id
        meta = dict(s.meta or {})
        meta["baseline_pending"] = True
        meta["baseline_note"] = "pending 占位；正式验收须白号采样回传"
        s.meta = meta
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def approve_executable(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer"):
        raise PermissionError("需要 reviewer 审批策略")
    if s.created_by and s.created_by == actor.id:
        raise PermissionError("起草人不可审批自己的策略")
    if s.status != "pending_review":
        raise ValueError("仅待审策略可批准为可执行")
    if not s.diagnostic_report_id:
        raise ValueError("须先挂接①诊断报告")
    if not s.baseline_snapshot_id:
        raise ValueError("须先挂接②baseline 快照（无白号可先 register-baseline 占位）")
    validate_six_tuple(s, for_executable=True)
    s.status = "executable"
    s.approved_by = actor.id
    s.approved_at = datetime.utcnow()
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def task_summary_for(db: AsyncSession, strategy_id: uuid.UUID) -> dict[str, Any]:
    rows = (
        await db.execute(select(ContentTask).where(ContentTask.strategy_id == strategy_id))
    ).scalars().all()
    by_status: dict[str, int] = {}
    for t in rows:
        st = t.workflow_status or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
    ready_n = by_status.get("ready", 0) + by_status.get("promoted", 0)
    all_ready = len(rows) >= 2 and ready_n == len(rows) and all(
        (t.workflow_status or "") in ("ready", "promoted") for t in rows
    )
    return {
        "total": len(rows),
        "by_status": by_status,
        "ready_count": ready_n,
        "all_ready": all_ready,
        "awaiting_observe": all_ready,
    }


async def attach_task(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    title: str,
    content_kind: str = "deep",
    prompt_id: uuid.UUID | None = None,
) -> ContentTask:
    if s.status not in ("executable", "deployed", "observing"):
        raise ValueError("仅可执行/已投放策略可挂执行物")
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor")
    if not s.knowledge_base_id:
        raise ValueError("策略未绑定知识库")
    kind = (content_kind or "deep").strip().lower()
    # 未指定提示词时按供给取向挂内置模板，便于一键生成
    resolved_prompt_id = prompt_id
    if resolved_prompt_id is None:
        from app.models.content_engine import ContentPrompt
        from app.services.content_engine import ensure_default_prompts

        await ensure_default_prompts(db)
        prefer_keys = (
            ("FAQ", "问答")
            if kind in ("faq", "short", "短答")
            else ("七段式", "结论前置", "答案摘要")
        )
        prompts = (
            await db.execute(
                select(ContentPrompt)
                .where(ContentPrompt.is_active.is_(True))
                .order_by(ContentPrompt.sort_order.asc())
            )
        ).scalars().all()
        for key in prefer_keys:
            for p in prompts:
                if key in (p.title or ""):
                    resolved_prompt_id = p.id
                    break
            if resolved_prompt_id is not None:
                break
        if resolved_prompt_id is None and prompts:
            resolved_prompt_id = prompts[0].id

    query = (s.question_class or title or "").strip()
    variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
    if variants:
        query = variants[0]
    task = ContentTask(
        title=title.strip(),
        knowledge_base_id=s.knowledge_base_id,
        strategy_id=s.id,
        geo_run_id=s.geo_run_id,
        prompt_id=resolved_prompt_id,
        input_query=query,
        workflow_status="claimed",
        claimed_by=actor.id,
        status="pending",
        meta={
            "content_kind": kind,
            "strategy_platform": s.platform,
            "entity": "第一现场",
            "ai_focus_inject": True,
            "target_platforms": [s.platform],
        },
    )
    db.add(task)
    await db.flush()
    return task


async def generate_task_draft(
    db: AsyncSession,
    s: GeoStrategy,
    task: ContentTask,
    *,
    actor: User,
) -> ContentTask:
    """对策略执行物跑内容引擎生成（LLM + 知识检索 + 标题槽位填充）。"""
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    if task.strategy_id != s.id:
        raise ValueError("任务不属于该策略")
    from app.services import content_engine as ce

    task = await ce.run_content_task(db, task.id)
    body = (task.template_draft_body or task.draft_body or "").strip()
    if body:
        # 策略链路默认同步一份渠道稿，便于直接提交审核
        media = (s.channel_matrix or {}).get("media_types") or ["wechat"]
        channel_key = str(media[0] if media else "wechat")
        task = await gkb.save_channel_draft(db, task, body=body, channel_key=channel_key)
    return task


async def mark_deployed(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    site_url: str,
    media_channel_type: str,
    media_url: str,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要业务角色登记投放")
    summary = await task_summary_for(db, s.id)
    if not summary["all_ready"]:
        raise ValueError("策略下全部执行物须连续过审 ready（至少 2 篇）后才能已投放")
    if not (site_url or "").strip():
        raise ValueError("官网 URL 必填")
    mtype = (media_channel_type or "").strip().lower()
    if mtype not in MEDIA_CHANNEL_TYPES:
        raise ValueError(f"媒体号类型须为 {', '.join(MEDIA_CHANNEL_TYPES)}")
    if not (media_url or "").strip():
        raise ValueError("媒体号 URL 必填")
    if s.status not in ("executable", "deployed"):
        raise ValueError("策略须为可执行状态")
    s.site_url = site_url.strip()
    s.media_channel_type = mtype
    s.media_url = media_url.strip()
    s.deployed_at = datetime.utcnow()
    s.deployed_by = actor.id
    s.status = "deployed"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


def _citation_rank_ok(sample: RealObsSample, top_n: int = 10) -> bool:
    """提及且引用位次进入前 top_n；无引用列表则不能判生效。"""
    if not sample.mention or not sample.ok:
        return False
    citations = sample.citations or []
    if not citations:
        return False
    # citations: [{url, rank?, title?}] 或字符串列表
    for i, c in enumerate(citations):
        if isinstance(c, dict):
            rank = c.get("rank")
            if rank is None:
                rank = i + 1
            url = str(c.get("url") or c.get("link") or "")
            owned = bool(c.get("owned") or sample.owned_citation)
            if int(rank) <= top_n and (sample.mention or owned or url):
                # 有编号引用且位次合格
                if sample.owned_citation or sample.strong_adopted or sample.mention:
                    return int(rank) <= top_n
            if int(rank) <= top_n and sample.mention:
                return True
        else:
            if i + 1 <= top_n and sample.mention:
                return True
    # 若有 citations 且 mention，取最小 rank
    ranks: list[int] = []
    for i, c in enumerate(citations):
        if isinstance(c, dict) and c.get("rank") is not None:
            ranks.append(int(c["rank"]))
        else:
            ranks.append(i + 1)
    return bool(ranks) and min(ranks) <= top_n and sample.mention


async def compute_verdict_suggestion(db: AsyncSession, s: GeoStrategy) -> dict[str, Any]:
    variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
    if len(variants) < 3:
        raise ValueError("须有至少 3 条问法")
    top_n = int((s.success_signal or {}).get("top_n") or 10)
    mode = (s.success_signal or {}).get("mode") or "mention_top10"

    # 判定优先用 after；无 after 再回退到最新挂接快照（避免误用仅占位的 baseline）
    snap: RealObsSnapshot | None = None
    if s.after_snapshot_id:
        snap = await db.get(RealObsSnapshot, s.after_snapshot_id)
    if snap is None:
        q = select(RealObsSnapshot).where(
            RealObsSnapshot.strategy_id == s.id,
            RealObsSnapshot.phase == "after",
        )
        snap = (
            await db.execute(q.order_by(RealObsSnapshot.created_at.desc()))
        ).scalars().first()
    if snap is None:
        q = select(RealObsSnapshot).where(RealObsSnapshot.strategy_id == s.id)
        snap = (
            await db.execute(q.order_by(RealObsSnapshot.created_at.desc()))
        ).scalars().first()
    if snap is None:
        raise ValueError("尚无挂接本策略的观测快照（验收须 after；白号采样另测）")
    samples = (
        await db.execute(select(RealObsSample).where(RealObsSample.snapshot_id == snap.id))
    ).scalars().all()
    # 按问法文本聚合（question_text 匹配 variants）
    per_q: list[dict[str, Any]] = []
    effective_n = 0
    for text in variants:
        matched = [x for x in samples if (x.question_text or "").strip() == text]
        if not matched:
            matched = [x for x in samples if text in (x.question_text or "")]
        platform_samples = [x for x in matched if x.platform == s.platform]
        ok_eff = False
        partial = False
        detail = {"samples": len(platform_samples)}
        for sm in platform_samples:
            if mode == "strong_adopt":
                if sm.strong_adopted:
                    ok_eff = True
                elif sm.mention:
                    partial = True
            else:
                if _citation_rank_ok(sm, top_n=top_n):
                    ok_eff = True
                elif sm.mention:
                    partial = True
        if ok_eff:
            effective_n += 1
            q_verdict = "effective"
        elif partial:
            q_verdict = "partial"
        else:
            q_verdict = "ineffective"
        per_q.append({"query": text, "verdict": q_verdict, **detail})

    if effective_n >= 2:
        overall = "effective"
    elif effective_n == 1:
        overall = "partial"
    else:
        overall = "ineffective"

    baseline_compare: dict[str, Any] = {
        "baseline_snapshot_id": str(s.baseline_snapshot_id) if s.baseline_snapshot_id else None,
        "after_snapshot_id": str(s.after_snapshot_id or snap.id),
        "baseline_pending": bool((s.meta or {}).get("baseline_pending")),
        "note": "baseline 无样本时仅作占位对照；正式验收须白号 baseline+after",
    }
    if s.baseline_snapshot_id:
        b_samples = (
            await db.execute(
                select(RealObsSample).where(RealObsSample.snapshot_id == s.baseline_snapshot_id)
            )
        ).scalars().all()
        b_mention = sum(1 for x in b_samples if x.mention and x.platform == s.platform)
        a_mention = sum(1 for x in samples if x.mention and x.platform == s.platform)
        baseline_compare.update(
            {
                "baseline_sample_count": len(b_samples),
                "baseline_mention_count": b_mention,
                "after_sample_count": len(samples),
                "after_mention_count": a_mention,
                "mention_delta": a_mention - b_mention,
            }
        )

    return {
        "suggested_verdict": overall,
        "effective_query_count": effective_n,
        "query_results": per_q,
        "snapshot_id": str(snap.id),
        "snapshot_phase": snap.phase,
        "mode": mode,
        "top_n": top_n,
        "baseline_compare": baseline_compare,
        "account_note": "验收须白号样本；固定查询号不算；本环境可用 fixture 验闸门",
    }


async def confirm_verdict(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    verdict: str | None = None,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer"):
        raise PermissionError("需要 reviewer 确认策略判定")
    if s.status not in ("deployed", "observing", "effective", "partial", "ineffective"):
        raise ValueError("须先已投放并完成观测")
    suggestion = await compute_verdict_suggestion(db, s)
    final = verdict or suggestion["suggested_verdict"]
    if final not in ("effective", "partial", "ineffective"):
        raise ValueError("verdict 须为 effective|partial|ineffective")
    s.verdict = final
    s.verdict_detail = suggestion
    s.judged_by = actor.id
    s.judged_at = datetime.utcnow()
    s.status = final
    if final == "effective":
        s.promote_suggestion = "promote"
    else:
        s.promote_suggestion = "hold"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def fork_new_version(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    """⑧ 判定后迭代：开新版本。"""
    if s.status not in ("effective", "partial", "ineffective", "archived"):
        raise ValueError("仅判定后的策略可开新版本")
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    child = GeoStrategy(
        title=s.title,
        platform=s.platform,
        question_class=s.question_class,
        query_variants=list(s.query_variants or []),
        content_orientation=s.content_orientation or "",
        channel_matrix=dict(s.channel_matrix or {}),
        success_signal=dict(s.success_signal or {}),
        knowledge_document_ids=list(s.knowledge_document_ids or []),
        knowledge_tag_pack=dict(s.knowledge_tag_pack or {}),
        knowledge_base_id=s.knowledge_base_id,
        geo_run_id=s.geo_run_id,
        version=(s.version or 1) + 1,
        parent_strategy_id=s.id,
        status="draft",
        created_by=actor.id,
        gap_note=f"迭代自 v{s.version}（{s.verdict or s.status}）",
        force_status="none",
        meta={"forked_from": str(s.id)},
    )
    db.add(child)
    await db.flush()
    return child


async def force_initiate(db: AsyncSession, s: GeoStrategy, *, actor: User, reason: str) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer"):
        raise PermissionError("需要 reviewer 发起强制沉淀")
    if not (reason or "").strip():
        raise ValueError("强制沉淀必须填写理由")
    s.force_reason = reason.strip()
    s.force_initiated_by = actor.id
    s.force_business_confirmed_by = None
    s.force_admin_confirmed_by = None
    s.force_status = "pending_business"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def force_business_confirm(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer"):
        raise PermissionError("需要另一业务人确认")
    if s.force_status != "pending_business":
        raise ValueError("当前不在待业务确认状态")
    if s.force_initiated_by and s.force_initiated_by == actor.id:
        raise PermissionError("发起人不可作为业务确认人")
    s.force_business_confirmed_by = actor.id
    s.force_status = "pending_admin"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def force_admin_confirm(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    if not is_platform_admin(actor):
        raise PermissionError("需要 admin 终确强制沉淀")
    if s.force_status != "pending_admin":
        raise ValueError("当前不在待 admin 终确状态")
    s.force_admin_confirmed_by = actor.id
    s.force_status = "done"
    s.promote_suggestion = "promote"
    s.verdict = s.verdict or "effective"
    s.verdict_detail = {
        **dict(s.verdict_detail or {}),
        "forced": True,
        "force_reason": s.force_reason,
    }
    s.status = "effective"
    s.judged_by = actor.id
    s.judged_at = datetime.utcnow()
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def confirm_promote_l2(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    kb: KnowledgeBase,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer"):
        raise PermissionError("需要 reviewer 确认沉淀")
    if s.promote_suggestion != "promote" and s.force_status != "done":
        raise ValueError("无沉淀建议或未完成强制沉淀")
    if s.status not in ("effective",) and s.force_status != "done":
        raise ValueError("仅生效策略可确认沉淀（或强制完成）")
    tasks = (
        await db.execute(
            select(ContentTask).where(
                ContentTask.strategy_id == s.id,
                ContentTask.workflow_status == "ready",
            )
        )
    ).scalars().all()
    promoted: list[str] = list(s.promoted_document_ids or [])
    for task in tasks:
        try:
            task = await gkb.confirm_promote(db, task, actor=actor, kb=kb)
            if task.promoted_document_id:
                promoted.append(str(task.promoted_document_id))
        except Exception:
            # 单篇失败不阻断其余；记录在 meta
            meta = dict(s.meta or {})
            fails = list(meta.get("promote_failures") or [])
            fails.append(str(task.id))
            meta["promote_failures"] = fails
            s.meta = meta
    s.promoted_document_ids = promoted
    s.promote_suggestion = "promoted"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def list_strategies(
    db: AsyncSession,
    *,
    status: str | None = None,
    platform: str | None = None,
    limit: int = 50,
) -> list[GeoStrategy]:
    q = select(GeoStrategy).order_by(GeoStrategy.created_at.desc()).limit(min(limit, 100))
    if status:
        q = q.where(GeoStrategy.status == status)
    if platform:
        q = q.where(GeoStrategy.platform == platform)
    return list((await db.execute(q)).scalars().all())
