#!/usr/bin/env python3
"""策略全流程 E2E（直连服务层）。含真 LLM 生成 + Qwen Embedding 入库；after 用 fixture（不跑白号）。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
    os.environ["POSTGRES_HOST"] = os.environ.get("POSTGRES_HOST") or "127.0.0.1"
    os.environ["REDIS_HOST"] = os.environ.get("REDIS_HOST") or "127.0.0.1"


async def main() -> int:
    _load_dotenv()
    import bcrypt
    from sqlalchemy import select

    from app.core.database import async_session
    from app.models.content_engine import KnowledgeBase
    from app.models.diagnostic import DiagnosticReport, DiagnosticStatus
    from app.models.geo_run import GeoRun
    from app.models.real_obs import RealObsSample
    from app.models.user import User, UserRole
    from app.services import geo_kb as gkb
    from app.services import geo_strategy_svc as svc
    from app.services import real_obs as real_obs_svc
    from app.services.content_engine import ensure_default_prompts
    from app.services.runtime_settings import invalidate_runtime_settings_cache

    await invalidate_runtime_settings_cache()

    sample_path = ROOT / "docs" / "pilot-demo" / "dangqun-geo-kb" / "sample-l2-story.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    # 注入栏目认知语料，便于检索命中「第一现场」
    sample = {
        **sample,
        "tier": "L2",
        "title": "第一现场栏目定位说明·冒烟",
        "body": (
            "第一现场是广电官方栏目，聚焦一线报道与社区民生。"
            "观众可在第一现场官网与公众号查看节目内容与活动报道。"
            "栏目定位：权威、现场、服务群众。"
            + "\n\n"
            + str(sample.get("body") or "")
        ),
        "tags": {
            "site_id": "diyixianchang",
            "task_bajua": "栏目认知",
            "doc_type": "栏目说明",
            "theme": "栏目认知",
        },
    }

    def hash_pw(p: str) -> str:
        return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    async with async_session() as db:
        async def ensure_user(email: str, username: str, geo_role: str, role: UserRole = UserRole.USER) -> User:
            row = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if row:
                row.geo_role = geo_role
                row.is_active = True
                await db.flush()
                return row
            u = User(
                email=email,
                username=username,
                hashed_password=hash_pw("SmokeTest!234"),
                role=role,
                geo_role=geo_role,
                is_active=True,
                is_verified=True,
            )
            db.add(u)
            await db.flush()
            return u

        editor = await ensure_user("smoke-editor@georank.local", "smoke_editor", "editor")
        reviewer = await ensure_user("smoke-reviewer@georank.local", "smoke_reviewer", "reviewer")
        await ensure_user("smoke-admin@georank.local", "smoke_admin", None, role=UserRole.ADMIN)
        await ensure_default_prompts(db)

        kb = KnowledgeBase(
            name=f"smoke-kb-{uuid.uuid4().hex[:8]}",
            slug=f"smoke-kb-{uuid.uuid4().hex[:8]}",
            description="strategy e2e + llm",
        )
        db.add(kb)
        await db.flush()

        doc = await gkb.ingest_tagged(
            db,
            kb=kb,
            title=sample["title"],
            body=sample["body"],
            tier="L2",
            tags=sample["tags"],
            fact_cards=sample.get("fact_cards"),
            source_url=sample.get("source_url"),
            external_id=f"smoke-{uuid.uuid4().hex[:10]}",
            external_approved=True,
            submitted_by=editor.id,
        )
        print("INGEST_OK doc", doc.id, "chunks", doc.chunk_count)

        report = DiagnosticReport(
            url="https://example.local/diyixianchang",
            status=DiagnosticStatus.COMPLETED,
            overall_score=72.0,
            recommendations={"gaps": ["缺 FAQ 结构", "主体 Schema 可加强"], "urgent": []},
            user_id=editor.id,
        )
        db.add(report)
        await db.flush()

        run = GeoRun(
            title="smoke-strategy-run-llm",
            entity="第一现场",
            competitor="",
            url="https://example.local/diyixianchang",
            platforms=["doubao"],
            status="active",
            artifacts={"diagnostic_report_id": str(report.id), "knowledge_base_id": str(kb.id)},
        )
        db.add(run)
        await db.flush()

        s = await svc.create_from_seed(
            db,
            actor=editor,
            platform="doubao",
            question_class="第一现场是什么栏目",
            gap_note="冒烟：诊断显示 FAQ/主体结构化不足",
            title="冒烟·第一现场栏目认知·豆包·LLM",
            knowledge_base_id=kb.id,
            geo_run_id=run.id,
        )
        s = await svc.update_draft(
            db,
            s,
            actor=editor,
            content_orientation="1篇深文说明栏目定位 + 1篇 FAQ 短答",
            query_variants=[
                "第一现场是什么栏目",
                "第一现场主要报道什么内容",
                "哪里看第一现场官方内容",
            ],
            channel_matrix={"site_required": True, "media_types": ["wechat"]},
            success_signal={"mode": "mention_top10", "top_n": 10},
            knowledge_document_ids=[str(doc.id)],
            knowledge_tag_pack={
                "site_id": "diyixianchang",
                "theme": "栏目认知",
                "task_bajua": "栏目认知",
            },
        )
        s = await svc.attach_diagnostic(db, s, actor=editor, diagnostic_report_id=report.id)
        s = await svc.register_baseline_snapshot(db, s, actor=editor, create_pending=True)
        s = await svc.submit_for_approval(db, s, actor=editor)
        s = await svc.approve_executable(db, s, actor=reviewer)
        s = await svc.confirm_query_pack(
            db,
            s,
            actor=editor,
            query_variants=list(s.query_variants or []),
        )

        t1 = await svc.attach_task(db, s, actor=editor, title="深文·栏目定位", content_kind="deep")
        t2 = await svc.attach_task(db, s, actor=editor, title="FAQ·官方入口", content_kind="faq")

        llm_ok_n = 0
        for task in (t1, t2):
            task = await svc.generate_task_draft(db, s, task, actor=editor)
            body = (task.template_draft_body or task.draft_body or "").strip()
            llm_ok = bool((task.meta or {}).get("llm_ok"))
            print(
                "GEN",
                task.title,
                "llm_ok=",
                llm_ok,
                "chars=",
                len(body),
                "err=",
                (task.error_message or "")[:120],
            )
            if not body:
                print("EMPTY_DRAFT", task.id)
                return 1
            if llm_ok:
                llm_ok_n += 1
            # 渠道稿：直接复用模板稿进入审核链
            await gkb.save_channel_draft(db, task, body=body, channel_key="wechat")
            await gkb.submit_for_review(db, task)
            await gkb.approve_ready(db, task, actor=reviewer)

        if llm_ok_n < 1:
            print("LLM_WARN: 两篇均未走通真 LLM（可能降级草稿）；流程闸门仍继续")
        else:
            print("LLM_OK generated", llm_ok_n, "tasks")

        s = await svc.mark_deployed(
            db,
            s,
            actor=editor,
            site_url="https://example.local/diyixianchang/article-smoke",
            media_channel_type="wechat",
            media_url="https://mp.weixin.qq.com/s/smoke-demo",
        )

        variants = list(s.query_variants or [])
        questions = [{"id": f"aq{i+1}", "text": t} for i, t in enumerate(variants)]
        after = await real_obs_svc.create_snapshot(
            db,
            run,
            phase="after",
            platforms=["doubao"],
            questions=questions,
            owned_domains=["example.local"],
            fact_source_urls=[s.site_url],
            published_at=s.deployed_at,
            prompt_pack_version="smoke-after",
            strategy_id=s.id,
        )
        s.after_snapshot_id = after.id
        s.status = "observing"
        await db.flush()

        for i, q in enumerate(questions):
            db.add(
                RealObsSample(
                    id=uuid.uuid4(),
                    snapshot_id=after.id,
                    geo_run_id=run.id,
                    question_id=q["id"],
                    question_text=q["text"],
                    platform="doubao",
                    attempt=1,
                    answer_text="根据公开资料，第一现场是官方栏目。来源见引用。",
                    citations=[{"url": "https://example.local/diyixianchang/article-smoke", "rank": i + 1}],
                    mention=True,
                    owned_citation=True,
                    strong_adopted=True,
                    ok=True,
                    label_source="fixture",
                    raw_meta={"account_type": "fixture", "note": "非白号；仅流程冒烟"},
                    sampled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        await db.flush()

        s = await svc.confirm_verdict(db, s, actor=reviewer)
        s = await svc.confirm_promote_l2(db, s, actor=reviewer, kb=kb)
        checklist = svc.handoff_checklist(s, task_summary=await svc.task_summary_for(db, s.id))
        await db.commit()

        print("STRATEGY_ID", s.id)
        print("STATUS", s.status)
        print("VERDICT", s.verdict)
        print("PROMOTE", s.promote_suggestion)
        print("BASELINE_COMPARE", json.dumps((s.verdict_detail or {}).get("baseline_compare"), ensure_ascii=False))
        missing = [i["step"] for i in checklist["items"] if not i["ok"]]
        if missing:
            print("MISSING", missing)
            return 1
        if s.verdict != "effective":
            print("expected effective, got", s.verdict)
            return 1
        print("E2E_OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
