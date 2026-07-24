"""
可信观测：启发式标注 + 运行编排
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trust_obs import TrustObsProbe, TrustObsRun, TrustObsSample
from app.services.ai_client import chat_completion
from app.services.runtime_settings import get_ai_runtime_config

ENTITY_DEFAULT = "GEO 示范栏目"
DEFAULT_DOMAINS = ["localhost", "georank.local", "example.com"]
DEFAULT_ALIASES = ["GEO示范栏目", "GEO Demo Column", "示范栏目"]

METHOD_NOTE = (
    "API 自动采样（OpenAI-compatible），非网页抓取；"
    "标签由规则启发式粗分，可在后台人工改标；"
    "本结果不等于全网 AI 搜索引用率。"
)


def classify_answer(
    answer: str,
    *,
    entity_name: str,
    aliases: list[str] | None = None,
    owned_domains: list[str] | None = None,
    competitors: list[str] | None = None,
) -> dict[str, Any]:
    text = (answer or "").strip()
    lowered = text.lower()
    names = [entity_name, *(aliases or [])]
    names = [n for n in names if isinstance(n, str) and n.strip()]
    domains = [d.lower().strip() for d in (owned_domains or []) if isinstance(d, str) and d.strip()]
    comps = [c for c in (competitors or []) if isinstance(c, str) and c.strip()]

    mentioned = any(n.lower() in lowered for n in names if n)
    urls = re.findall(r"https?://[^\s\)\]\>\"']+", text)
    owned_hit = False
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if any(host == d or host.endswith("." + d) for d in domains):
            owned_hit = True
            break

    co_mention = mentioned and any(c.lower() in lowered for c in comps)
    recommend_tokens = ("推荐", "建议关注", "建议收看", "首选", "recommend", "should follow")
    recommendation = mentioned and any(tok.lower() in lowered for tok in recommend_tokens)

    error = False
    if mentioned:
        error_tokens = ("已停播", "已关闭", "不存在", "虚假", "造假")
        error = any(tok in text for tok in error_tokens)

    if not text:
        primary = "absent"
    elif error:
        primary = "error"
    elif owned_hit:
        primary = "citation"
    elif recommendation:
        primary = "recommendation"
    elif co_mention:
        primary = "co_mention"
    elif mentioned:
        primary = "mention"
    else:
        primary = "absent"

    labels = [primary]
    if co_mention and primary != "co_mention":
        labels.append("co_mention")
    if recommendation and primary != "recommendation":
        labels.append("recommendation")

    return {
        "primary_label": primary,
        "labels": labels,
        "classifier_meta": {
            "mentioned": mentioned,
            "owned_url_hit": owned_hit,
            "url_count": len(urls),
            "urls": urls[:8],
            "co_mention": co_mention,
            "recommendation": recommendation,
            "error_flag": error,
        },
    }


def aggregate_labels(samples: list[TrustObsSample]) -> dict[str, Any]:
    counter = Counter(s.primary_label for s in samples)
    total = sum(counter.values()) or 1
    return {
        "total_samples": sum(counter.values()),
        "counts": dict(counter),
        "rates": {k: round(v / total, 4) for k, v in counter.items()},
        "mention": counter.get("mention", 0),
        "citation": counter.get("citation", 0),
        "recommendation": counter.get("recommendation", 0),
        "co_mention": counter.get("co_mention", 0),
        "absent": counter.get("absent", 0),
        "error": counter.get("error", 0),
    }


async def ensure_default_probes(db: AsyncSession) -> list[TrustObsProbe]:
    result = await db.execute(select(TrustObsProbe).order_by(TrustObsProbe.sort_order.asc()))
    existing = list(result.scalars().all())
    if existing:
        return existing
    return await _seed_probes(db)


async def _seed_probes(db: AsyncSession) -> list[TrustObsProbe]:
    entity = ENTITY_DEFAULT
    seeds = [
        ("Q1", f"{entity}是什么？主要做什么内容？", 10),
        ("Q2", f"介绍一下{entity}的官方背景与所属机构", 20),
        ("Q3", f"{entity}最近有哪些代表性节目或报道？", 30),
        ("Q4", f"和「竞品示范栏目」相比，{entity}有什么特点？", 40),
        ("Q5", f"哪里可以找到{entity}的官方入口？", 50),
    ]
    created: list[TrustObsProbe] = []
    for key, question, order in seeds:
        probe = TrustObsProbe(
            probe_key=key,
            prompt_version="probe-v1",
            question=question,
            entity_name=entity,
            entity_aliases=list(DEFAULT_ALIASES),
            owned_domains=list(DEFAULT_DOMAINS),
            competitor_names=["竞品示范栏目"],
            is_active=True,
            sort_order=order,
        )
        db.add(probe)
        created.append(probe)
    await db.commit()
    for item in created:
        await db.refresh(item)
    return created


async def list_probes(db: AsyncSession, *, active_only: bool = False) -> list[TrustObsProbe]:
    await ensure_default_probes(db)
    stmt = select(TrustObsProbe).order_by(TrustObsProbe.sort_order.asc())
    if active_only:
        stmt = stmt.where(TrustObsProbe.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


def serialize_probe(probe: TrustObsProbe) -> dict[str, Any]:
    return {
        "id": str(probe.id),
        "probe_key": probe.probe_key,
        "prompt_version": probe.prompt_version,
        "question": probe.question,
        "entity_name": probe.entity_name,
        "entity_aliases": probe.entity_aliases or [],
        "owned_domains": probe.owned_domains or [],
        "competitor_names": probe.competitor_names or [],
        "is_active": bool(probe.is_active),
        "sort_order": probe.sort_order,
    }


def serialize_sample(sample: TrustObsSample) -> dict[str, Any]:
    return {
        "id": str(sample.id),
        "run_id": str(sample.run_id),
        "probe_id": str(sample.probe_id),
        "probe_key": sample.probe_key,
        "sample_index": sample.sample_index,
        "question": sample.question,
        "raw_answer": sample.raw_answer,
        "primary_label": sample.primary_label,
        "labels": sample.labels or [],
        "classifier_meta": sample.classifier_meta or {},
        "manual_override": bool(sample.manual_override),
        "created_at": sample.created_at.isoformat() if sample.created_at else None,
    }


def serialize_run(run: TrustObsRun, samples: list[TrustObsSample] | None = None) -> dict[str, Any]:
    payload = {
        "id": str(run.id),
        "status": run.status,
        "prompt_version": run.prompt_version,
        "locale": run.locale,
        "device": run.device,
        "login_state": run.login_state,
        "model_name": run.model_name,
        "repeats": run.repeats,
        "aggregate": run.aggregate or {},
        "method_note": run.method_note,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "badge": "API 自动采样（非网页抓取）",
    }
    if samples is not None:
        payload["samples"] = [serialize_sample(s) for s in samples]
    return payload


async def execute_run(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    repeats: int = 2,
    locale: str = "zh-CN",
    device: str = "api",
    login_state: str = "api-key",
) -> TrustObsRun:
    probes = await list_probes(db, active_only=True)
    llm = await get_ai_runtime_config()
    model_name = str(llm.get("llm_model") or "")

    run = TrustObsRun(
        status="running",
        prompt_version="probe-v1",
        locale=locale,
        device=device,
        login_state=login_state,
        model_name=model_name,
        repeats=max(1, min(int(repeats or 2), 3)),
        method_note=METHOD_NOTE,
        created_by=user_id,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    samples: list[TrustObsSample] = []
    try:
        for probe in probes:
            for idx in range(1, run.repeats + 1):
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "你是通用问答助手。请根据公开常识如实回答。"
                            "若不确定请明确说明不确定，不要编造权威背书。"
                        ),
                    },
                    {"role": "user", "content": probe.question},
                ]
                answer = await chat_completion(messages, temperature=0.2, max_tokens=800)
                classified = classify_answer(
                    answer,
                    entity_name=probe.entity_name,
                    aliases=list(probe.entity_aliases or []),
                    owned_domains=list(probe.owned_domains or []),
                    competitors=list(probe.competitor_names or []),
                )
                sample = TrustObsSample(
                    run_id=run.id,
                    probe_id=probe.id,
                    probe_key=probe.probe_key,
                    sample_index=idx,
                    question=probe.question,
                    raw_answer=answer,
                    primary_label=classified["primary_label"],
                    labels=classified["labels"],
                    classifier_meta=classified["classifier_meta"],
                )
                db.add(sample)
                samples.append(sample)
        run.aggregate = aggregate_labels(samples)
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        await db.commit()
        await db.refresh(run)
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error_message = str(exc)[:2000]
        run.finished_at = datetime.utcnow()
        run.aggregate = aggregate_labels(samples) if samples else {}
        await db.commit()
        await db.refresh(run)
    return run


async def get_latest_completed_run(db: AsyncSession) -> tuple[TrustObsRun | None, list[TrustObsSample]]:
    result = await db.execute(
        select(TrustObsRun)
        .where(TrustObsRun.status == "completed")
        .order_by(TrustObsRun.created_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        return None, []
    samples_result = await db.execute(
        select(TrustObsSample)
        .where(TrustObsSample.run_id == run.id)
        .order_by(TrustObsSample.probe_key.asc(), TrustObsSample.sample_index.asc())
    )
    return run, list(samples_result.scalars().all())


async def get_run_with_samples(db: AsyncSession, run_id: UUID) -> tuple[TrustObsRun | None, list[TrustObsSample]]:
    run = await db.get(TrustObsRun, run_id)
    if not run:
        return None, []
    samples_result = await db.execute(
        select(TrustObsSample)
        .where(TrustObsSample.run_id == run.id)
        .order_by(TrustObsSample.probe_key.asc(), TrustObsSample.sample_index.asc())
    )
    return run, list(samples_result.scalars().all())
