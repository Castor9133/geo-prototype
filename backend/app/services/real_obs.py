"""真实点名观测：规则打标、快照编排、前后对比与归因卡（独立于 trust_obs）。"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo_run import GeoRun
from app.models.real_obs import (
    DIAGNOSIS_TYPES,
    REAL_OBS_PLATFORMS,
    RealObsSample,
    RealObsSnapshot,
)

NEGATIVE_HINTS = (
    "坑",
    "翻车",
    "不推荐",
    "别买",
    "避雷",
    "负面",
    "丑闻",
    "造假",
    "虚假",
    "投诉",
    "差评如潮",
)

SAMPLE_SHEET_HEADERS = (
    "question_id",
    "question_text",
    "platform",
    "attempt",
    "mention",
    "competitor_mention",
    "owned_citation",
    "citation_rank",
    "diagnosis_type",
    "answer_text",
    "ok",
    "notes",
)

METHOD_NOTE = (
    "约定账号网页端点名抽样（半自动浏览器）；"
    "非 API 探针、非全网引用率、非平台官方检索台账；"
    "强采纳 = 本品提及 + 自有域/事实源命中。"
)

ECOMMERCE_HINTS = (
    "tmall.com",
    "taobao.com",
    "jd.com",
    "pinduoduo.com",
    "suning.com",
    "amazon.",
    "douyin.com",
    "tiktok.com",
)

URL_RE = re.compile(r"https?://[^\s\)\]\>\"'<>]+", re.I)


def _norm_host(value: str) -> str:
    host = (value or "").strip().lower()
    if host.startswith("http://") or host.startswith("https://"):
        host = urlparse(host).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host.rstrip(".")


def _domain_match(host: str, owned: list[str]) -> bool:
    h = _norm_host(host)
    if not h:
        return False
    for d in owned:
        od = _norm_host(d)
        if not od:
            continue
        if h == od or h.endswith("." + od):
            return True
    return False


def extract_citations_from_text(answer: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url in URL_RE.findall(answer or ""):
        clean = url.rstrip(".,;）)」』\"'")
        if clean in seen:
            continue
        seen.add(clean)
        host = _norm_host(clean)
        found.append(
            {
                "url": clean,
                "domain": host,
                "title": None,
                "source": "body_extract",
            }
        )
    return found


def normalize_citations(raw: list[Any] | None, *, answer: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw or []:
        if isinstance(item, str):
            url = item.strip()
            title = None
            source = "structured"
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("href") or "").strip()
            title = item.get("title")
            source = str(item.get("source") or "structured")
        else:
            continue
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(
            {
                "url": url,
                "domain": _norm_host(url),
                "title": title,
                "source": source if source in ("structured", "body_extract") else "structured",
            }
        )
    if answer:
        for c in extract_citations_from_text(answer):
            if c["url"] not in seen:
                seen.add(c["url"])
                out.append(c)
    return out


def find_hit_snippet(text: str, names: list[str], max_len: int = 120) -> str | None:
    lowered = (text or "").lower()
    for name in names:
        n = (name or "").strip()
        if not n:
            continue
        idx = lowered.find(n.lower())
        if idx < 0:
            continue
        start = max(0, idx - 24)
        end = min(len(text), idx + len(n) + 48)
        snippet = text[start:end].strip()
        if len(snippet) > max_len:
            snippet = snippet[: max_len - 1] + "…"
        return snippet
    return None


def classify_sample(
    answer: str | None,
    *,
    entity_name: str,
    aliases: list[str] | None = None,
    competitor: str | None = None,
    owned_domains: list[str] | None = None,
    fact_source_urls: list[str] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = (answer or "").strip()
    names = [entity_name, *(aliases or [])]
    names = [n for n in names if isinstance(n, str) and n.strip()]
    owned = [d for d in (owned_domains or []) if isinstance(d, str) and d.strip()]
    fact_urls = [u for u in (fact_source_urls or []) if isinstance(u, str) and u.strip()]
    fact_hosts = [_norm_host(u) for u in fact_urls]
    cites = normalize_citations(citations, answer=text)

    mention = any(n.lower() in text.lower() for n in names if n)
    competitor_mention = bool(competitor and competitor.strip() and competitor.lower() in text.lower())

    owned_citation = False
    for c in cites:
        host = c.get("domain") or _norm_host(str(c.get("url") or ""))
        if _domain_match(host, owned) or _domain_match(host, fact_hosts):
            owned_citation = True
            break
        url = str(c.get("url") or "")
        if any(fu and fu in url for fu in fact_urls):
            owned_citation = True
            break

    strong_adopted = bool(mention and owned_citation and text)
    return {
        "mention": mention,
        "competitor_mention": competitor_mention,
        "owned_citation": owned_citation,
        "strong_adopted": strong_adopted,
        "citations": cites,
        "hit_snippet": find_hit_snippet(text, names) if mention else None,
    }


def _citation_rank(citations: list[Any] | None, raw_meta: dict[str, Any] | None = None) -> int | None:
    if raw_meta and raw_meta.get("citation_rank") is not None:
        try:
            return int(raw_meta["citation_rank"])
        except (TypeError, ValueError):
            pass
    for c in citations or []:
        if isinstance(c, dict) and c.get("rank") is not None:
            try:
                return int(c["rank"])
            except (TypeError, ValueError):
                continue
    return None


def infer_diagnosis_type(
    *,
    mention: bool,
    competitor_mention: bool,
    owned_citation: bool,
    answer_text: str | None = None,
    citations: list[Any] | None = None,
    raw_meta: dict[str, Any] | None = None,
    diagnosis_override: str | None = None,
) -> str | None:
    """问题向分型；健康提及返回 None。优先级：负面 > 竞品主导 > 缺席 > 靠后。"""
    if diagnosis_override:
        key = str(diagnosis_override).strip().lower()
        if key in DIAGNOSIS_TYPES:
            return key
        if key in ("", "ok", "none", "null"):
            return None
    text = (answer_text or "").lower()
    if text and any(h in text for h in NEGATIVE_HINTS):
        return "suspected_negative"
    if competitor_mention and not mention:
        return "competitor_dominated"
    if competitor_mention and mention and not owned_citation:
        return "competitor_dominated"
    if not mention:
        return "absent"
    rank = _citation_rank(citations, raw_meta)
    if rank is not None and rank > 10:
        return "low_ranked"
    if mention and not owned_citation:
        return "low_ranked"
    return None


def diagnosis_type_label(key: str | None) -> str:
    return {
        "absent": "完全没提",
        "competitor_dominated": "竞品抢戏",
        "low_ranked": "提了但靠后",
        "suspected_negative": "疑似负面",
    }.get(key or "", "正常/未标")


def build_sample_sheet_csv(snap: RealObsSnapshot, *, platform: str | None = None) -> str:
    """导出空表（或带平台列）供人工填写后回灌。"""
    platforms = [platform] if platform else list(snap.platforms or REAL_OBS_PLATFORMS)
    platforms = [str(p).strip().lower() for p in platforms if str(p).strip()]
    if not platforms:
        platforms = list(REAL_OBS_PLATFORMS)
    buf = io.StringIO()
    buf.write("# 填写说明: mention/competitor_mention/owned_citation/ok 填 1/0 或 true/false\n")
    buf.write(
        "# diagnosis_type 可选: absent|competitor_dominated|low_ranked|suspected_negative|（空=自动推断）\n"
    )
    writer = csv.DictWriter(buf, fieldnames=list(SAMPLE_SHEET_HEADERS), extrasaction="ignore")
    writer.writeheader()
    for q in snap.questions or []:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("id") or "").strip()
        qtext = str(q.get("text") or "").strip()
        if not qid or not qtext:
            continue
        for plat in platforms:
            writer.writerow(
                {
                    "question_id": qid,
                    "question_text": qtext,
                    "platform": plat,
                    "attempt": 1,
                    "mention": "",
                    "competitor_mention": "",
                    "owned_citation": "",
                    "citation_rank": "",
                    "diagnosis_type": "",
                    "answer_text": "",
                    "ok": "1",
                    "notes": "",
                }
            )
    return buf.getvalue()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value or "").strip().lower()
    return s in {"1", "true", "yes", "y", "是", "有"}


def parse_sample_sheet_csv(content: str) -> list[dict[str, Any]]:
    """解析人工填写的采样表为 upsert_sample 参数列表。"""
    text = (content or "").lstrip("\ufeff")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        raise ValueError("CSV 为空")
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames or "question_id" not in reader.fieldnames:
        raise ValueError("CSV 须含表头 question_id / platform 等列")
    out: list[dict[str, Any]] = []
    for i, row in enumerate(reader, start=2):
        qid = str(row.get("question_id") or "").strip()
        plat = str(row.get("platform") or "").strip().lower()
        if not qid or not plat:
            raise ValueError(f"第 {i} 行缺少 question_id 或 platform")
        rank_raw = str(row.get("citation_rank") or "").strip()
        rank = int(rank_raw) if rank_raw.isdigit() else None
        citations: list[dict[str, Any]] = []
        if rank is not None:
            citations.append({"rank": rank, "url": "", "owned": _truthy(row.get("owned_citation"))})
        raw_meta: dict[str, Any] = {"source": "sample_sheet_csv", "notes": str(row.get("notes") or "")}
        if rank is not None:
            raw_meta["citation_rank"] = rank
        dtype = str(row.get("diagnosis_type") or "").strip().lower() or None
        out.append(
            {
                "question_id": qid,
                "platform": plat,
                "attempt": int(row.get("attempt") or 1) or 1,
                "answer_text": str(row.get("answer_text") or "").strip() or None,
                "citations": citations,
                "ok": _truthy(row.get("ok")) if str(row.get("ok") or "").strip() != "" else True,
                "raw_meta": {
                    **raw_meta,
                    "sheet_mention": _truthy(row.get("mention")),
                    "sheet_competitor_mention": _truthy(row.get("competitor_mention")),
                    "sheet_owned_citation": _truthy(row.get("owned_citation")),
                    "diagnosis_override": dtype,
                },
            }
        )
    if not out:
        raise ValueError("CSV 无有效数据行")
    return out


def serialize_snapshot(snap: RealObsSnapshot) -> dict[str, Any]:
    return {
        "id": str(snap.id),
        "geo_run_id": str(snap.geo_run_id),
        "strategy_id": str(snap.strategy_id) if getattr(snap, "strategy_id", None) else None,
        "phase": snap.phase,
        "prompt_pack_version": snap.prompt_pack_version,
        "platforms": snap.platforms or [],
        "questions": snap.questions or [],
        "status": snap.status,
        "owned_domains": snap.owned_domains or [],
        "fact_source_urls": snap.fact_source_urls or [],
        "entity_aliases": snap.entity_aliases or [],
        "published_at": snap.published_at.isoformat() + "Z" if snap.published_at else None,
        "probe_after_at": snap.probe_after_at.isoformat() + "Z" if snap.probe_after_at else None,
        "method_note": snap.method_note or METHOD_NOTE,
        "error_message": snap.error_message,
        "created_at": snap.created_at.isoformat() + "Z" if snap.created_at else None,
        "updated_at": snap.updated_at.isoformat() + "Z" if snap.updated_at else None,
        "started_at": snap.started_at.isoformat() + "Z" if snap.started_at else None,
        "finished_at": snap.finished_at.isoformat() + "Z" if snap.finished_at else None,
        "hours_since_publish": _hours_since(snap.published_at),
    }


def serialize_sample(sample: RealObsSample) -> dict[str, Any]:
    dtype = getattr(sample, "diagnosis_type", None)
    return {
        "id": str(sample.id),
        "snapshot_id": str(sample.snapshot_id),
        "geo_run_id": str(sample.geo_run_id),
        "question_id": sample.question_id,
        "question_text": sample.question_text,
        "platform": sample.platform,
        "attempt": sample.attempt,
        "answer_text": sample.answer_text,
        "citations": sample.citations or [],
        "mention": bool(sample.mention),
        "competitor_mention": bool(sample.competitor_mention),
        "owned_citation": bool(sample.owned_citation),
        "strong_adopted": bool(sample.strong_adopted),
        "diagnosis_type": dtype,
        "diagnosis_label": diagnosis_type_label(dtype),
        "hit_snippet": sample.hit_snippet,
        "label_source": sample.label_source,
        "ok": bool(sample.ok),
        "error_message": sample.error_message,
        "raw_meta": sample.raw_meta or {},
        "sampled_at": sample.sampled_at.isoformat() + "Z" if sample.sampled_at else None,
        "created_at": sample.created_at.isoformat() + "Z" if sample.created_at else None,
        "updated_at": sample.updated_at.isoformat() + "Z" if sample.updated_at else None,
    }


def _hours_since(published_at: datetime | None) -> float | None:
    if not published_at:
        return None
    return round((datetime.utcnow() - published_at).total_seconds() / 3600.0, 2)


def _append_run_step(run: GeoRun, kind: str, meta: dict[str, Any]) -> None:
    artifacts = dict(run.artifacts or {})
    steps = list(artifacts.get("steps") or [])
    steps.append(
        {
            "kind": kind,
            "source": "real_obs",
            "at": datetime.utcnow().isoformat() + "Z",
            "meta": meta,
        }
    )
    artifacts["steps"] = steps[-60:]
    run.artifacts = artifacts
    run.updated_at = datetime.utcnow()


def _default_questions(run: GeoRun, custom: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if custom:
        out: list[dict[str, str]] = []
        for i, q in enumerate(custom):
            if isinstance(q, str) and q.strip():
                out.append({"id": f"q{i + 1}", "text": q.strip()})
            elif isinstance(q, dict):
                text = str(q.get("text") or q.get("question") or "").strip()
                if not text:
                    continue
                qid = str(q.get("id") or f"q{i + 1}")
                out.append({"id": qid, "text": text})
        if out:
            return out[:12]
    entity = run.entity or "本品"
    competitor = run.competitor or "竞品"
    selected = list((run.artifacts or {}).get("selected_keywords") or [])
    if selected:
        return [{"id": f"kw{i + 1}", "text": str(kw)} for i, kw in enumerate(selected[:6])]
    return [
        {"id": "q1", "text": f"{entity} 和 {competitor} 怎么选？各自适合什么场景？"},
        {"id": "q2", "text": f"{entity} 核心参数与购买注意点有哪些？请给出可核对来源。"},
        {"id": "q3", "text": f"有没有权威资料对比 {entity} 与 {competitor}？"},
    ]


def _normalize_platforms(raw: list[str] | None) -> list[str]:
    allowed = set(REAL_OBS_PLATFORMS)
    if not raw:
        return list(REAL_OBS_PLATFORMS)
    out: list[str] = []
    for p in raw:
        key = str(p).strip().lower()
        mapping = {
            "豆包": "doubao",
            "元宝": "yuanbao",
            "deepseek": "deepseek",
            "doubao": "doubao",
            "yuanbao": "yuanbao",
        }
        key = mapping.get(key, key)
        if key in allowed and key not in out:
            out.append(key)
    return out or list(REAL_OBS_PLATFORMS)


async def create_snapshot(
    db: AsyncSession,
    run: GeoRun,
    *,
    phase: str = "after",
    platforms: list[str] | None = None,
    questions: list[dict[str, Any]] | None = None,
    owned_domains: list[str] | None = None,
    fact_source_urls: list[str] | None = None,
    entity_aliases: list[str] | None = None,
    published_at: datetime | None = None,
    prompt_pack_version: str = "manual-v1",
    strategy_id: UUID | None = None,
) -> RealObsSnapshot:
    if phase not in ("baseline", "after"):
        raise ValueError("phase 须为 baseline 或 after")
    plats = _normalize_platforms(platforms)
    qs = _default_questions(run, questions)
    domains = owned_domains
    if not domains and run.url:
        host = _norm_host(run.url)
        domains = [host] if host else []
    if not domains:
        domains = ["localhost", "georank.local", "dji.com"]

    pub = published_at or (datetime.utcnow() if phase == "after" else None)
    probe_after = (pub + timedelta(hours=2)) if pub else None

    snap = RealObsSnapshot(
        id=uuid4(),
        geo_run_id=run.id,
        strategy_id=strategy_id,
        phase=phase,
        prompt_pack_version=prompt_pack_version or "manual-v1",
        platforms=plats,
        questions=qs,
        status="pending",
        owned_domains=domains,
        fact_source_urls=fact_source_urls or [],
        entity_aliases=entity_aliases or [],
        published_at=pub,
        probe_after_at=probe_after,
        method_note=METHOD_NOTE,
    )
    db.add(snap)
    _append_run_step(
        run,
        "real_obs_snapshot_created",
        {
            "snapshot_id": str(snap.id),
            "phase": phase,
            "platforms": plats,
            "question_count": len(qs),
        },
    )
    # 只 flush：由调用方（API 路由 / 业务服务）统一 commit，避免中途提交打散事务
    await db.flush()
    await db.refresh(snap)
    return snap


async def list_snapshots(db: AsyncSession, run_id: UUID) -> list[RealObsSnapshot]:
    rows = (
        await db.execute(
            select(RealObsSnapshot)
            .where(RealObsSnapshot.geo_run_id == run_id)
            .order_by(RealObsSnapshot.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def get_snapshot(db: AsyncSession, snapshot_id: UUID) -> RealObsSnapshot | None:
    return await db.get(RealObsSnapshot, snapshot_id)


async def list_samples(db: AsyncSession, snapshot_id: UUID) -> list[RealObsSample]:
    rows = (
        await db.execute(
            select(RealObsSample)
            .where(RealObsSample.snapshot_id == snapshot_id)
            .order_by(RealObsSample.platform.asc(), RealObsSample.question_id.asc(), RealObsSample.attempt.asc())
        )
    ).scalars().all()
    return list(rows)


def build_probe_job(run: GeoRun, snap: RealObsSnapshot) -> dict[str, Any]:
    """供 scripts/browser-probe 拉取的任务契约。"""
    units: list[dict[str, Any]] = []
    for platform in snap.platforms or []:
        for q in snap.questions or []:
            units.append(
                {
                    "question_id": q.get("id"),
                    "question_text": q.get("text"),
                    "platform": platform,
                    "attempt": 1,
                }
            )
    return {
        "task_id": str(snap.id),
        "geo_run_id": str(run.id),
        "snapshot_id": str(snap.id),
        "phase": snap.phase,
        "callback_path": f"/api/geo-runs/{run.id}/real-obs/snapshots/{snap.id}/samples",
        "platforms": snap.platforms or [],
        "questions": snap.questions or [],
        "units": units,
        "entity": run.entity,
        "competitor": run.competitor,
        "owned_domains": snap.owned_domains or [],
        "fact_source_urls": snap.fact_source_urls or [],
        "method_note": METHOD_NOTE,
    }


async def mark_sampling(db: AsyncSession, snap: RealObsSnapshot, run: GeoRun | None = None) -> RealObsSnapshot:
    if snap.status == "pending":
        snap.status = "sampling"
        snap.started_at = datetime.utcnow()
        snap.updated_at = datetime.utcnow()
        if run:
            _append_run_step(run, "real_obs_sampling", {"snapshot_id": str(snap.id)})
        await db.commit()
        await db.refresh(snap)
    return snap


async def refresh_snapshot_status(db: AsyncSession, snap: RealObsSnapshot) -> RealObsSnapshot:
    samples = await list_samples(db, snap.id)
    expected = len(snap.platforms or []) * len(snap.questions or [])
    ok_count = sum(1 for s in samples if s.ok and (s.answer_text or "").strip())
    fail_count = sum(1 for s in samples if not s.ok)
    if expected <= 0:
        snap.status = "failed"
        snap.error_message = "快照无平台或问法"
    elif ok_count >= expected:
        snap.status = "completed"
        snap.finished_at = datetime.utcnow()
        snap.error_message = None
    elif ok_count > 0 or fail_count > 0:
        if ok_count + fail_count >= expected:
            snap.status = "partial" if ok_count else "failed"
            snap.finished_at = datetime.utcnow()
        else:
            snap.status = "sampling"
    else:
        snap.status = snap.status if snap.status != "pending" else "pending"
    snap.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(snap)
    return snap


async def upsert_sample(
    db: AsyncSession,
    run: GeoRun,
    snap: RealObsSnapshot,
    *,
    question_id: str,
    platform: str,
    attempt: int = 1,
    answer_text: str | None = None,
    citations: list[Any] | None = None,
    ok: bool = True,
    error_message: str | None = None,
    raw_meta: dict[str, Any] | None = None,
    sampled_at: datetime | None = None,
) -> RealObsSample:
    platform = str(platform).strip().lower()
    if platform not in REAL_OBS_PLATFORMS:
        raise ValueError(f"不支持的平台: {platform}")
    qmap = {str(q.get("id")): str(q.get("text") or "") for q in (snap.questions or []) if isinstance(q, dict)}
    if question_id not in qmap:
        raise ValueError(f"未知问法编号: {question_id}")

    existing = (
        await db.execute(
            select(RealObsSample).where(
                RealObsSample.snapshot_id == snap.id,
                RealObsSample.question_id == question_id,
                RealObsSample.platform == platform,
                RealObsSample.attempt == attempt,
            )
        )
    ).scalar_one_or_none()

    labels = classify_sample(
        answer_text if ok else None,
        entity_name=run.entity,
        aliases=snap.entity_aliases or [],
        competitor=run.competitor,
        owned_domains=snap.owned_domains or [],
        fact_source_urls=snap.fact_source_urls or [],
        citations=citations,
    )
    meta = dict(raw_meta or {})
    # CSV 表单显式勾选可覆盖规则（仍保留规则 citations）
    if "sheet_mention" in meta:
        labels["mention"] = bool(meta.get("sheet_mention"))
    if "sheet_competitor_mention" in meta:
        labels["competitor_mention"] = bool(meta.get("sheet_competitor_mention"))
    if "sheet_owned_citation" in meta:
        labels["owned_citation"] = bool(meta.get("sheet_owned_citation"))
        labels["strong_adopted"] = bool(labels["mention"] and labels["owned_citation"])

    if existing:
        sample = existing
    else:
        sample = RealObsSample(
            id=uuid4(),
            snapshot_id=snap.id,
            geo_run_id=run.id,
            question_id=question_id,
            question_text=qmap[question_id],
            platform=platform,
            attempt=attempt,
        )
        db.add(sample)

    sample.question_text = qmap[question_id]
    sample.answer_text = answer_text
    sample.citations = labels["citations"]
    sample.mention = labels["mention"]
    sample.competitor_mention = labels["competitor_mention"]
    sample.owned_citation = labels["owned_citation"]
    sample.strong_adopted = labels["strong_adopted"]
    sample.hit_snippet = labels["hit_snippet"]
    sample.diagnosis_type = infer_diagnosis_type(
        mention=labels["mention"],
        competitor_mention=labels["competitor_mention"],
        owned_citation=labels["owned_citation"],
        answer_text=answer_text if ok else None,
        citations=labels["citations"],
        raw_meta=meta,
        diagnosis_override=meta.get("diagnosis_override"),
    )
    sample.label_source = "rule"
    sample.ok = bool(ok)
    sample.error_message = error_message
    sample.raw_meta = meta
    sample.sampled_at = sampled_at or datetime.utcnow()
    sample.updated_at = datetime.utcnow()

    if snap.status == "pending":
        snap.status = "sampling"
        snap.started_at = snap.started_at or datetime.utcnow()

    await db.flush()
    await refresh_snapshot_status(db, snap)
    _append_run_step(
        run,
        "real_obs_sample_upsert",
        {
            "snapshot_id": str(snap.id),
            "sample_id": str(sample.id),
            "platform": platform,
            "question_id": question_id,
            "strong_adopted": sample.strong_adopted,
            "ok": sample.ok,
        },
    )
    await db.commit()
    await db.refresh(sample)
    return sample


async def override_sample_labels(
    db: AsyncSession,
    sample: RealObsSample,
    *,
    mention: bool | None = None,
    owned_citation: bool | None = None,
    strong_adopted: bool | None = None,
    competitor_mention: bool | None = None,
    diagnosis_type: str | None = None,
) -> RealObsSample:
    if mention is not None:
        sample.mention = bool(mention)
    if owned_citation is not None:
        sample.owned_citation = bool(owned_citation)
    if competitor_mention is not None:
        sample.competitor_mention = bool(competitor_mention)
    if strong_adopted is not None:
        sample.strong_adopted = bool(strong_adopted)
    else:
        sample.strong_adopted = bool(sample.mention and sample.owned_citation)
    if diagnosis_type is not None:
        key = str(diagnosis_type).strip().lower()
        if key in ("", "ok", "none", "null"):
            sample.diagnosis_type = None
        elif key in DIAGNOSIS_TYPES:
            sample.diagnosis_type = key
        else:
            raise ValueError(
                "diagnosis_type 须为 absent|competitor_dominated|low_ranked|suspected_negative 或清空"
            )
    else:
        sample.diagnosis_type = infer_diagnosis_type(
            mention=sample.mention,
            competitor_mention=sample.competitor_mention,
            owned_citation=sample.owned_citation,
            answer_text=sample.answer_text,
            citations=sample.citations,
            raw_meta=sample.raw_meta,
        )
    sample.label_source = "human"
    sample.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(sample)
    return sample


def _phase_stats(samples: list[RealObsSample]) -> dict[str, Any]:
    usable = [s for s in samples if s.ok]
    total = len(usable) or 1
    mention_n = sum(1 for s in usable if s.mention)
    owned_n = sum(1 for s in usable if s.owned_citation)
    strong_n = sum(1 for s in usable if s.strong_adopted)
    domains: set[str] = set()
    for s in usable:
        for c in s.citations or []:
            if isinstance(c, dict) and c.get("domain"):
                domains.add(str(c["domain"]).lower())
    return {
        "sample_count": len(usable),
        "mention_rate": round(mention_n / total, 4),
        "owned_citation_rate": round(owned_n / total, 4),
        "strong_adopted_rate": round(strong_n / total, 4),
        "mention_count": mention_n,
        "owned_citation_count": owned_n,
        "strong_adopted_count": strong_n,
        "domains": sorted(domains),
    }


def build_action_cards(
    *,
    after_stats: dict[str, Any],
    owned_domains: list[str],
    samples: list[RealObsSample],
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    owned_norm = [_norm_host(d) for d in owned_domains]
    domains = set(after_stats.get("domains") or [])
    owned_hit = any(_domain_match(d, owned_norm) for d in domains)

    ecommerce_only = False
    if domains and not owned_hit:
        ecommerce_only = all(any(h in d for h in ECOMMERCE_HINTS) for d in domains)

    if after_stats.get("mention_count", 0) == 0:
        cards.append(
            {
                "code": "no_mention",
                "title": "本品未被点名",
                "severity": "约定账号抽样下，答案正文未出现本品别名。建议回到拓词核对问法是否贴近真实决策问题，并补强知识库事实卡。",
                "cta": [{"label": "打开知识库", "href": "/knowledge"}, {"label": "去拓词", "href": "/keywords"}],
            }
        )
    elif after_stats.get("owned_citation_count", 0) == 0:
        cards.append(
            {
                "code": "mention_without_owned",
                "title": "被点名但未挂上自有信源",
                "severity": "本品有提及，但引用/外链未命中自有域或指定事实源——仍在吃别人的信源。建议补官网可引用规格/参数/FAQ 段落并确保可抓取。",
                "cta": [
                    {"label": "打开知识库", "href": "/knowledge"},
                    {"label": "内容引擎", "href": "/admin/content-engine"},
                ],
            }
        )

    if not owned_hit and ecommerce_only:
        cards.append(
            {
                "code": "ecommerce_only",
                "title": "引用偏电商详情",
                "severity": "当前抽到的域名多为电商详情页。建议补权威评测或结构化 FAQ，降低「只有货架页」的信源结构。",
                "cta": [{"label": "内容引擎", "href": "/admin/content-engine"}],
            }
        )

    if after_stats.get("strong_adopted_count", 0) > 0:
        cards.append(
            {
                "code": "strong_ok",
                "title": "存在强采纳样本",
                "severity": f"已有 {after_stats['strong_adopted_count']} 条样本同时满足提及 + 自有源命中（约定账号抽样，≠ 全网引用率）。",
                "cta": [{"label": "继续观测", "href": "/suite?step=measure"}],
            }
        )

    if not cards:
        weak = sum(1 for s in samples if s.ok and s.mention and not s.strong_adopted)
        cards.append(
            {
                "code": "review",
                "title": "建议人工复核",
                "severity": f"有 {weak} 条弱提及或未完成单元，请核对答案与引用抽取是否完整。",
                "cta": [{"label": "打开知识库", "href": "/knowledge"}],
            }
        )
    return cards


async def compare_run(db: AsyncSession, run: GeoRun) -> dict[str, Any]:
    snaps = await list_snapshots(db, run.id)
    baseline = next((s for s in snaps if s.phase == "baseline" and s.status in ("completed", "partial")), None)
    after = next((s for s in snaps if s.phase == "after" and s.status in ("completed", "partial", "sampling")), None)
    if not after:
        after = next((s for s in snaps if s.phase == "after"), None)

    baseline_samples = await list_samples(db, baseline.id) if baseline else []
    after_samples = await list_samples(db, after.id) if after else []
    b_stats = _phase_stats(baseline_samples) if baseline_samples else None
    a_stats = _phase_stats(after_samples) if after_samples else {
        "sample_count": 0,
        "mention_rate": 0,
        "owned_citation_rate": 0,
        "strong_adopted_rate": 0,
        "mention_count": 0,
        "owned_citation_count": 0,
        "strong_adopted_count": 0,
        "domains": [],
    }

    b_domains = set((b_stats or {}).get("domains") or [])
    a_domains = set(a_stats.get("domains") or [])
    delta = None
    if b_stats:
        delta = {
            "mention_rate": round(a_stats["mention_rate"] - b_stats["mention_rate"], 4),
            "owned_citation_rate": round(a_stats["owned_citation_rate"] - b_stats["owned_citation_rate"], 4),
            "strong_adopted_rate": round(a_stats["strong_adopted_rate"] - b_stats["strong_adopted_rate"], 4),
            "domains_added": sorted(a_domains - b_domains),
            "domains_lost": sorted(b_domains - a_domains),
            "domains_kept": sorted(a_domains & b_domains),
        }

    owned = (after.owned_domains if after else None) or []
    cards = build_action_cards(after_stats=a_stats, owned_domains=owned, samples=after_samples)

    return {
        "geo_run_id": str(run.id),
        "method_note": METHOD_NOTE,
        "baseline": serialize_snapshot(baseline) if baseline else None,
        "after": serialize_snapshot(after) if after else None,
        "baseline_stats": b_stats,
        "after_stats": a_stats,
        "delta": delta,
        "action_cards": cards,
        "knowledge_href": "/knowledge",
        "content_engine_href": "/admin/content-engine",
    }
