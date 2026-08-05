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
from app.core.config import settings
from app.services import geo_kb as gkb
from app.services.geo_roles import has_business_geo_role, is_platform_admin
from app.services.real_obs import infer_diagnosis_type


def demo_metrics_enabled() -> bool:
    """领导 demo 可开；正式环境须关（未测不编数 + 观测硬样本）。"""
    return bool(getattr(settings, "GEORANK_DEMO_METRICS", False))


def _as_uuid_list(raw: list | None) -> list[str]:
    out: list[str] = []
    for item in raw or []:
        out.append(str(item))
    return out


def query_variant_list(s: GeoStrategy) -> list[str]:
    return [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]


def is_query_pack_confirmed(s: GeoStrategy) -> bool:
    """拓词确认：meta 标记且问法 ≥3。"""
    meta = dict(s.meta or {})
    if not meta.get("query_pack_confirmed"):
        return False
    return len(query_variant_list(s)) >= 3


def is_knowledge_bound(s: GeoStrategy) -> bool:
    return bool(s.knowledge_document_ids) and bool(s.knowledge_tag_pack)


def is_active_work_status(status: str | None) -> bool:
    return (status or "") in (
        "draft",
        "pending_review",
        "executable",
        "deployed",
        "observing",
    )


def _strategy_href(
    strategy_id: uuid.UUID | str,
    *,
    tab: str | None = None,
    pipe: str | None = None,
    path: str = "/strategies",
) -> str:
    sid = str(strategy_id)
    if path == "/keywords":
        return f"/keywords?strategy={sid}"
    if path == "/knowledge":
        return f"/knowledge?strategy={sid}"
    if path == "/observe":
        phase = "baseline" if pipe == "baseline" else ("after" if pipe == "after" else "")
        q = f"/observe?strategy={sid}"
        return f"{q}&phase={phase}" if phase else q
    if path == "/diagnostic":
        return "/diagnostic"
    parts = [f"strategy={sid}"]
    if tab:
        parts.append(f"tab={tab}")
    if pipe:
        parts.append(f"pipe={pipe}")
    return "/strategies?" + "&".join(parts)


def compute_next_action(s: GeoStrategy, *, task_summary: dict | None = None) -> dict[str, Any]:
    """编辑岗「下一步」：只亮一个动作（见产品实施说明）。"""
    ts = task_summary or {}
    sid = s.id
    orientation_ok = bool((s.content_orientation or "").strip())
    matrix = s.channel_matrix or {}
    media_types = matrix.get("media_types") or matrix.get("media") or []
    craft_basics_ok = orientation_ok and bool(media_types)
    draftish = s.status in ("draft", "pending_review")

    if not s.diagnostic_report_id:
        return {
            "key": "diagnostic",
            "label": "去挂查页面结果",
            "href": _strategy_href(sid, tab="craft"),
            "tab": "craft",
            "pipe": None,
        }
    if not s.baseline_snapshot_id:
        return {
            "key": "baseline",
            "label": "去做投放前摸底",
            "href": _strategy_href(sid, path="/observe", pipe="baseline"),
            "tab": "craft",
            "pipe": "baseline",
        }
    if draftish:
        if not craft_basics_ok or len(query_variant_list(s)) < 3:
            return {
                "key": "craft",
                "label": "去补全策略",
                "href": _strategy_href(sid, tab="craft"),
                "tab": "craft",
                "pipe": None,
            }
        if s.status == "draft":
            return {
                "key": "craft",
                "label": "去送审",
                "href": _strategy_href(sid, tab="craft"),
                "tab": "craft",
                "pipe": None,
            }
        return {
            "key": "craft",
            "label": "去批准",
            "href": _strategy_href(sid, tab="craft"),
            "tab": "craft",
            "pipe": None,
        }
    if s.status in ("executable", "deployed", "observing") or s.verdict:
        if s.status == "executable" and not is_query_pack_confirmed(s):
            return {
                "key": "expand",
                "label": "去确认观测问法",
                "href": _strategy_href(sid, path="/keywords"),
                "tab": None,
                "pipe": None,
            }
        if s.status == "executable" and not is_knowledge_bound(s):
            return {
                "key": "knowledge",
                "label": "去备知识",
                "href": _strategy_href(sid, path="/knowledge"),
                "tab": None,
                "pipe": None,
            }
        if s.status == "executable" and not ts.get("all_ready"):
            return {
                "key": "write",
                "label": "去写稿",
                "href": _strategy_href(sid, tab="write"),
                "tab": "write",
                "pipe": None,
            }
        if not (s.site_url and s.media_url and s.deployed_at):
            return {
                "key": "deploy",
                "label": "去登记发布",
                "href": _strategy_href(sid, tab="publish", pipe="register"),
                "tab": "publish",
                "pipe": "register",
            }
        if not s.after_snapshot_id:
            return {
                "key": "after",
                "label": "去做投放后复测",
                "href": _strategy_href(sid, tab="publish", pipe="after"),
                "tab": "publish",
                "pipe": "after",
            }
        if s.verdict not in ("effective", "partial", "ineffective"):
            return {
                "key": "verdict",
                "label": "去看效果与留档",
                "href": _strategy_href(sid, tab="publish", pipe="after"),
                "tab": "publish",
                "pipe": "after",
            }
    return {
        "key": "done",
        "label": "查看本条选题",
        "href": _strategy_href(sid, tab="publish", pipe="after"),
        "tab": "publish",
        "pipe": "after",
    }


def serialize_strategy(s: GeoStrategy, *, task_summary: dict | None = None) -> dict[str, Any]:
    checklist = handoff_checklist(s, task_summary=task_summary)
    next_action = compute_next_action(s, task_summary=task_summary)
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
        "query_pack_confirmed": is_query_pack_confirmed(s),
        "next_action": next_action,
    }


def validate_six_tuple(s: GeoStrategy, *, for_executable: bool = False) -> None:
    """基本六元组。for_executable=批准可开工：不再要求知识绑定与拓词终稿。"""
    if s.platform not in STRATEGY_PLATFORMS:
        raise ValueError(f"platform 须为 {', '.join(STRATEGY_PLATFORMS)}")
    if not (s.question_class or "").strip():
        raise ValueError("问题类不能为空")
    if not (s.content_orientation or "").strip():
        raise ValueError("内容供给取向不能为空")
    if for_executable:
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
        # 草案改动后需重新确认拓词，避免未再确认就写稿
        meta = dict(s.meta or {})
        if meta.get("query_pack_confirmed"):
            meta["query_pack_confirmed"] = False
            meta.pop("query_pack_confirmed_at", None)
            meta.pop("query_pack_confirmed_by", None)
            s.meta = meta
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


async def _assert_knowledge_rag_eligible(db: AsyncSession, s: GeoStrategy) -> None:
    """可执行前：绑定文档须全部可 RAG。"""
    from app.models.content_engine import KnowledgeDocument

    ids = [str(x) for x in (s.knowledge_document_ids or []) if str(x).strip()]
    if not ids:
        raise ValueError("知识绑定：文档集不能为空")
    missing: list[str] = []
    ineligible: list[str] = []
    for raw in ids:
        try:
            doc_id = uuid.UUID(raw)
        except ValueError:
            missing.append(raw)
            continue
        doc = await db.get(KnowledgeDocument, doc_id)
        if not doc:
            missing.append(raw)
            continue
        if not gkb.is_rag_eligible(doc):
            ineligible.append(f"{doc.title or raw}({doc.review_state}/{doc.tier})")
    if missing:
        raise ValueError(f"知识绑定文档不存在: {', '.join(missing[:5])}")
    if ineligible:
        raise ValueError(f"知识绑定文档未过门禁/不可检索: {', '.join(ineligible[:5])}")


async def submit_for_approval(db: AsyncSession, s: GeoStrategy, *, actor: User) -> GeoStrategy:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor 提交审批")
    if s.status not in ("draft", "pending_review"):
        raise ValueError("仅草稿可提交审批")
    if not s.diagnostic_report_id:
        raise ValueError("须先挂接查页面结果")
    if not s.baseline_snapshot_id:
        raise ValueError("须先登记投放前摸底")
    if len(query_variant_list(s)) < 3:
        raise ValueError("送审前须有至少 3 条摸底用问法草案")
    validate_six_tuple(s, for_executable=True)
    s.status = "pending_review"
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


def handoff_checklist(s: GeoStrategy, *, task_summary: dict | None = None) -> dict[str, Any]:
    """环间交付物检查表。演示开时可占位；正式须真实样本。"""
    ts = task_summary or {}
    demo = demo_metrics_enabled()
    baseline_samples = int((s.meta or {}).get("baseline_sample_count") or 0)
    after_samples = int((s.meta or {}).get("after_sample_count") or 0)
    baseline_ok = bool(s.baseline_snapshot_id) and (demo or baseline_samples >= 3)
    after_ok = bool(s.after_snapshot_id) and (demo or after_samples >= 3)
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
            "ok": baseline_ok,
            "deliverable": "已登记摸底结果",
            "note": (
                "演示模式：可先占位；正式须≥3条真实样本"
                if demo
                else "正式：须≥3条真实摸底样本（未测不可批准）"
            ),
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
            "step": "④观测问法已确认",
            "key": "expand",
            "ok": is_query_pack_confirmed(s),
            "deliverable": "拓词问法已写回（≥3）",
        },
        {
            "step": "⑤素材已备齐",
            "key": "knowledge",
            "ok": is_knowledge_bound(s),
            "deliverable": "已指定用哪些稿 + 主题标签",
        },
        {
            "step": "⑥稿件已过审",
            "key": "tasks_ready",
            "ok": bool(ts.get("all_ready")),
            "deliverable": "至少2篇且全部过审",
        },
        {
            "step": "⑦已对外发布",
            "key": "deployed",
            "ok": bool(s.site_url and s.media_url and s.deployed_at),
            "deliverable": "官网链接 + 媒体号链接已登记",
        },
        {
            "step": "⑧投放后复测",
            "key": "after",
            "ok": after_ok,
            "deliverable": "已建复测记录",
            "note": (
                "演示模式：可先建快照；正式须≥3条复测样本"
                if demo
                else "正式：须≥3条真实复测样本方可判定"
            ),
        },
        {
            "step": "⑨效果已判定",
            "key": "verdict",
            "ok": s.verdict in ("effective", "partial", "ineffective"),
            "deliverable": "生效 / 部分见效 / 未见效",
        },
    ]
    return {
        "items": items,
        "demo_metrics": demo,
        "ready_for_approve": bool(s.diagnostic_report_id and baseline_ok),
        "ready_for_deploy": bool(ts.get("all_ready")),
        "ready_for_write": bool(
            is_query_pack_confirmed(s) and is_knowledge_bound(s) and s.knowledge_base_id
        ),
        "ready_for_verdict": after_ok and bool(s.site_url and s.media_url),
        "obs_white_hat_deferred": baseline_samples < 3,
        "baseline_sample_count": baseline_samples,
        "after_sample_count": after_samples,
        "white_hat_note": (
            "演示指标开启：可用占位；上线请关 GEORANK_DEMO_METRICS"
            if demo
            else "正式验收：摸底/复测各≥3条真实样本；未测不编数"
        ),
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


async def record_obs_samples(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    phase: str,
    samples: list[dict[str, Any]],
    account_label: str | None = None,
) -> GeoStrategy:
    """②/⑦ 人工回传白号观测样本（半自动：人提问，系统落库）。"""
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer 回传观测样本")
    ph = (phase or "").strip().lower()
    if ph not in ("baseline", "after"):
        raise ValueError("phase 须为 baseline|after")
    if ph == "baseline":
        snap_id = s.baseline_snapshot_id
        if not snap_id:
            raise ValueError("请先登记投放前摸底快照")
    else:
        snap_id = s.after_snapshot_id
        if not snap_id:
            raise ValueError("请先开始投放后复测")
        if s.status not in ("deployed", "observing", "effective", "partial", "ineffective"):
            raise ValueError("须已登记对外发布后才能回传复测样本")
    snap = await db.get(RealObsSnapshot, snap_id)
    if not snap:
        raise ValueError("观测快照不存在")
    if not samples:
        raise ValueError("至少回传 1 条样本")
    variants = [str(v).strip() for v in (s.query_variants or []) if str(v).strip()]
    written = 0
    for i, raw in enumerate(samples):
        text = str(raw.get("question_text") or raw.get("query") or "").strip()
        if not text and i < len(variants):
            text = variants[i]
        if not text:
            raise ValueError(f"第 {i+1} 条样本缺少问法文本")
        qid = str(raw.get("question_id") or f"q{i+1}")
        mention = bool(raw.get("mention"))
        rank = raw.get("citation_rank")
        citations: list[dict[str, Any]] = []
        if rank is not None:
            citations.append(
                {
                    "rank": int(rank),
                    "url": str(raw.get("citation_url") or s.site_url or ""),
                    "owned": bool(raw.get("owned_citation")),
                }
            )
        elif raw.get("citations"):
            citations = list(raw.get("citations") or [])
        owned = bool(raw.get("owned_citation") or raw.get("strong_adopted"))
        strong = bool(raw.get("strong_adopted") or (owned and mention and citations))
        # upsert by unique (snapshot, question_id, platform, attempt)
        existing = (
            await db.execute(
                select(RealObsSample).where(
                    RealObsSample.snapshot_id == snap.id,
                    RealObsSample.question_id == qid,
                    RealObsSample.platform == s.platform,
                    RealObsSample.attempt == 1,
                )
            )
        ).scalar_one_or_none()
        meta = {
            "account_type": "white",
            "account_label": account_label or "manual-white",
            "recorded_by": str(actor.id),
            "informal": bool(raw.get("informal")),
        }
        competitor_mention = bool(raw.get("competitor_mention"))
        dtype = infer_diagnosis_type(
            mention=mention,
            competitor_mention=competitor_mention,
            owned_citation=owned,
            answer_text=str(raw.get("answer_text") or "") or None,
            citations=citations,
            raw_meta={**meta, "citation_rank": rank, "diagnosis_override": raw.get("diagnosis_type")},
            diagnosis_override=str(raw.get("diagnosis_type") or "").strip() or None,
        )
        if existing:
            existing.question_text = text
            existing.answer_text = str(raw.get("answer_text") or "")[:8000] or None
            existing.citations = citations
            existing.mention = mention
            existing.competitor_mention = competitor_mention
            existing.owned_citation = owned
            existing.strong_adopted = strong
            existing.diagnosis_type = dtype
            existing.ok = True
            existing.label_source = "human"
            existing.raw_meta = {**(existing.raw_meta or {}), **meta}
            existing.sampled_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                RealObsSample(
                    snapshot_id=snap.id,
                    geo_run_id=snap.geo_run_id,
                    question_id=qid,
                    question_text=text,
                    platform=s.platform,
                    attempt=1,
                    answer_text=str(raw.get("answer_text") or "")[:8000] or None,
                    citations=citations,
                    mention=mention,
                    competitor_mention=competitor_mention,
                    owned_citation=owned,
                    strong_adopted=strong,
                    diagnosis_type=dtype,
                    ok=True,
                    label_source="human",
                    raw_meta=meta,
                    sampled_at=datetime.utcnow(),
                )
            )
        written += 1
    snap.status = "completed" if written >= 3 else "partial"
    snap.finished_at = datetime.utcnow()
    snap.updated_at = datetime.utcnow()
    meta = dict(s.meta or {})
    if ph == "baseline":
        meta["baseline_pending"] = written < 3
        meta["baseline_sample_count"] = written
        meta["baseline_note"] = "已回传白号摸底样本" if written >= 3 else "摸底样本不足 3 条（非正式）"
    else:
        meta["after_sample_count"] = written
        meta["after_note"] = "已回传白号复测样本" if written >= 3 else "复测样本不足 3 条（非正式）"
        if s.status == "deployed":
            s.status = "observing"
    s.meta = meta
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def approve_executable(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    force_reason: str | None = None,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer") and not is_platform_admin(actor):
        raise PermissionError("需要 reviewer 审批策略")
    if s.created_by and s.created_by == actor.id and not is_platform_admin(actor):
        raise PermissionError("起草人不可审批自己的策略")
    if s.status != "pending_review":
        raise ValueError("仅待审策略可批准为可执行")
    if not s.diagnostic_report_id:
        raise ValueError("须先挂接①诊断报告")
    if not s.baseline_snapshot_id:
        raise ValueError("须先挂接②baseline 快照（无白号可先 register-baseline 占位）")
    if len(query_variant_list(s)) < 3:
        raise ValueError("批准前须有至少 3 条摸底用问法草案")
    baseline_samples = int((s.meta or {}).get("baseline_sample_count") or 0)
    if not demo_metrics_enabled() and baseline_samples < 3:
        if is_platform_admin(actor) and (force_reason or "").strip():
            meta = dict(s.meta or {})
            meta["approve_force_reason"] = force_reason.strip()
            meta["approve_forced_by"] = str(actor.id)
            s.meta = meta
        else:
            raise ValueError(
                "正式模式：批准前须有≥3条真实摸底样本（或管理员填写 force_reason 强开）"
            )
    validate_six_tuple(s, for_executable=True)
    s.status = "executable"
    s.approved_by = actor.id
    s.approved_at = datetime.utcnow()
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def confirm_query_pack(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    query_variants: list[str] | None = None,
) -> GeoStrategy:
    """拓词确认：写回观测问法并打标，写稿前置。"""
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor/reviewer")
    variants = [str(v).strip() for v in (query_variants if query_variants is not None else s.query_variants or []) if str(v).strip()]
    if len(variants) < 3:
        raise ValueError("确认观测问法须至少 3 句")
    s.query_variants = variants
    meta = dict(s.meta or {})
    meta["query_pack_confirmed"] = True
    meta["query_pack_confirmed_at"] = datetime.utcnow().isoformat() + "Z"
    meta["query_pack_confirmed_by"] = str(actor.id)
    s.meta = meta
    s.updated_at = datetime.utcnow()
    await db.flush()
    return s


async def create_from_diagnostic(
    db: AsyncSession,
    *,
    actor: User,
    diagnostic_report_id: uuid.UUID,
    platform: str = "doubao",
    question_class: str | None = None,
    title: str | None = None,
) -> GeoStrategy:
    """查页面完成后一键建选题草稿并挂上诊断。"""
    from app.models.diagnostic import DiagnosticReport

    from app.models.diagnostic import DiagnosticStatus

    report = await db.get(DiagnosticReport, diagnostic_report_id)
    if not report:
        raise ValueError("诊断报告不存在")
    if report.status != DiagnosticStatus.COMPLETED:
        raise ValueError("仅已完成的查页面结果可用于新建选题")
    host = (report.url or "").replace("https://", "").replace("http://", "").split("/")[0] or "页面"
    qc = (question_class or "").strip() or f"页面认知 · {host}"
    gaps = ""
    rec = report.recommendations if isinstance(report.recommendations, dict) else {}
    gap_list = rec.get("gaps") or []
    if isinstance(gap_list, list):
        gaps = "；".join(str(x) for x in gap_list[:4] if x)
    summary = rec.get("summary") or {}
    if not gaps and isinstance(summary, dict):
        gaps = str(summary.get("priority_action") or summary.get("overview") or "")
    gap_note = (gaps or f"来自查页面 {report.url}").strip()[:2000]
    s = await create_from_seed(
        db,
        actor=actor,
        platform=platform or "doubao",
        question_class=qc,
        gap_note=gap_note,
        title=title or f"[草稿] {qc} · {platform or 'doubao'}",
    )
    return await attach_diagnostic(db, s, actor=actor, diagnostic_report_id=diagnostic_report_id)


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


async def assert_ready_for_write(db: AsyncSession, s: GeoStrategy) -> None:
    """写稿硬卡：可执行 + 拓词已确认 + 知识可检索。"""
    if s.status not in ("executable", "deployed", "observing"):
        raise ValueError("仅可执行/已投放策略可写稿")
    if not is_query_pack_confirmed(s):
        raise ValueError("请先确认观测问法（拓词写回至少 3 句）后再写稿")
    if not s.knowledge_base_id:
        raise ValueError("策略未绑定知识库")
    if not is_knowledge_bound(s):
        raise ValueError("请先备齐知识素材（文档与主题标签）后再写稿")
    await _assert_knowledge_rag_eligible(db, s)


async def attach_task(
    db: AsyncSession,
    s: GeoStrategy,
    *,
    actor: User,
    title: str,
    content_kind: str = "deep",
    prompt_id: uuid.UUID | None = None,
) -> ContentTask:
    if not has_business_geo_role(actor, "editor", "reviewer"):
        raise PermissionError("需要 editor")
    await assert_ready_for_write(db, s)
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
    force_reason: str | None = None,
) -> GeoStrategy:
    if not has_business_geo_role(actor, "reviewer") and not is_platform_admin(actor):
        raise PermissionError("需要 reviewer 确认策略判定")
    if s.status not in ("deployed", "observing", "effective", "partial", "ineffective"):
        raise ValueError("须先已投放并完成观测")
    after_samples = int((s.meta or {}).get("after_sample_count") or 0)
    if not demo_metrics_enabled() and after_samples < 3:
        if is_platform_admin(actor) and (force_reason or "").strip():
            meta = dict(s.meta or {})
            meta["verdict_force_reason"] = force_reason.strip()
            s.meta = meta
        else:
            raise ValueError(
                "正式模式：判定前须有≥3条真实复测样本（或管理员填写 force_reason 强开）"
            )
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
