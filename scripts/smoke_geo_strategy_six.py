#!/usr/bin/env python3
"""W6–W7：2 问题类 × 三平台 = 6 条策略闸门闭环（fixture 白号样本，不跑浏览器）。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

PLATFORMS = ("doubao", "yuanbao", "deepseek")
QUESTION_CLASSES = (
    "第一现场是什么栏目",
    "第一现场哪里看官方内容",
)


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
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
    from app.models.user import User, UserRole
    from app.services import geo_kb as gkb
    from app.services import geo_strategy_svc as svc
    from app.services import real_obs as real_obs_svc
    from app.services import white_hat_pool as pool
    from app.services.content_engine import ensure_default_prompts
    from app.services.runtime_settings import invalidate_runtime_settings_cache

    await invalidate_runtime_settings_cache()
    sample_path = ROOT / "docs" / "pilot-demo" / "dangqun-geo-kb" / "sample-l2-story.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))

    def hash_pw(p: str) -> str:
        return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    async with async_session() as db:
        async def ensure_user(email: str, username: str, geo_role: str, role: UserRole = UserRole.USER) -> User:
            row = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if row:
                row.geo_role = geo_role
                row.is_active = True
                row.hashed_password = hash_pw("SmokeTest!234")
                await db.flush()
                return row
            u = User(
                email=email,
                username=username,
                hashed_password=hash_pw("SmokeTest!234"),
                role=role,
                geo_role=geo_role,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            return u

        editor = await ensure_user("smoke-editor@georank.local", "smoke_editor", "editor")
        reviewer = await ensure_user("smoke-reviewer@georank.local", "smoke_reviewer", "reviewer")
        admin = await ensure_user("smoke-admin@georank.local", "smoke_admin", "admin", UserRole.ADMIN)
        await pool.seed_minimum_pool(db, actor=admin)
        await ensure_default_prompts(db)

        slug = f"six-kb-{uuid.uuid4().hex[:8]}"
        kb = KnowledgeBase(name="六策验收知识库", slug=slug, description="W6-W7")
        db.add(kb)
        await db.flush()

        doc = await gkb.ingest_tagged(
            db,
            kb=kb,
            title="六策·栏目说明",
            body="第一现场是广电官方栏目。" + str(sample.get("body") or ""),
            tier="L2",
            tags={
                "site_id": "diyixianchang",
                "task_bajua": "栏目认知",
                "doc_type": "栏目说明",
                "theme": "栏目认知",
            },
            external_approved=True,
            submitted_by=editor.id,
        )

        report = DiagnosticReport(
            url="https://example.local/six-strategy-diag",
            status=DiagnosticStatus.COMPLETED,
            overall_score=72.0,
            recommendations={"gaps": ["缺 FAQ"], "source": "smoke-six"},
            user_id=editor.id,
        )
        db.add(report)
        await db.flush()

        results: list[dict] = []
        for qc in QUESTION_CLASSES:
            for platform in PLATFORMS:
                run = GeoRun(
                    title=f"六策-{platform}-{qc[:8]}",
                    entity="第一现场",
                    competitor="",
                    url="https://example.local/six-strategy-diag",
                    platforms=[platform],
                    status="active",
                    artifacts={"smoke": "six", "knowledge_base_id": str(kb.id)},
                )
                db.add(run)
                await db.flush()
                s = await svc.create_from_seed(
                    db,
                    actor=editor,
                    platform=platform,
                    question_class=qc,
                    gap_note=f"六策验收缺口：{qc}@{platform}",
                    knowledge_base_id=kb.id,
                    geo_run_id=run.id,
                )
                variants = [qc, f"{qc}怎么理解", f"官方如何介绍相关栏目"]
                s = await svc.update_draft(
                    db,
                    s,
                    actor=editor,
                    content_orientation="1篇栏目说明 + 1篇常见问答",
                    query_variants=variants,
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
                s = await svc.record_obs_samples(
                    db,
                    s,
                    actor=editor,
                    phase="baseline",
                    account_label="seed-smoke",
                    samples=[
                        {"question_text": variants[0], "question_id": "bq1", "mention": False},
                        {"question_text": variants[1], "question_id": "bq2", "mention": False},
                        {"question_text": variants[2], "question_id": "bq3", "mention": False},
                    ],
                )
                s = await svc.submit_for_approval(db, s, actor=editor)
                s = await svc.approve_executable(db, s, actor=reviewer)
                t1 = await svc.attach_task(
                    db, s, actor=editor, title=f"{qc}·深文", content_kind="deep"
                )
                t2 = await svc.attach_task(
                    db, s, actor=editor, title=f"{qc}·FAQ", content_kind="faq"
                )
                t1.template_draft_body = f"【六策草稿】{qc} 栏目说明（{platform}）"
                t1.channel_draft_body = t1.template_draft_body
                t1.workflow_status = "in_review"
                t2.template_draft_body = f"【六策草稿】{qc} 常见问答（{platform}）"
                t2.channel_draft_body = t2.template_draft_body
                t2.workflow_status = "in_review"
                await db.flush()
                await gkb.approve_ready(db, t1, actor=reviewer)
                await gkb.approve_ready(db, t2, actor=reviewer)
                s = await svc.mark_deployed(
                    db,
                    s,
                    actor=editor,
                    site_url=f"https://example.local/site/{platform}",
                    media_channel_type="wechat",
                    media_url=f"https://example.local/wechat/{platform}",
                )
                questions = [{"id": f"aq{i+1}", "text": t} for i, t in enumerate(variants)]
                snap = await real_obs_svc.create_snapshot(
                    db,
                    run,
                    phase="after",
                    platforms=[platform],
                    questions=questions,
                    prompt_pack_version="six-after",
                    strategy_id=s.id,
                )
                s.after_snapshot_id = snap.id
                s.status = "observing"
                await db.flush()
                s = await svc.record_obs_samples(
                    db,
                    s,
                    actor=editor,
                    phase="after",
                    account_label="seed-smoke",
                    samples=[
                        {
                            "question_text": variants[0],
                            "question_id": "aq1",
                            "mention": True,
                            "citation_rank": 2,
                            "owned_citation": True,
                            "strong_adopted": True,
                        },
                        {
                            "question_text": variants[1],
                            "question_id": "aq2",
                            "mention": True,
                            "citation_rank": 4,
                            "owned_citation": True,
                        },
                        {
                            "question_text": variants[2],
                            "question_id": "aq3",
                            "mention": True,
                            "citation_rank": 8,
                        },
                    ],
                )
                s = await svc.confirm_verdict(db, s, actor=reviewer)
                results.append(
                    {
                        "id": str(s.id),
                        "platform": platform,
                        "question_class": qc,
                        "status": s.status,
                        "verdict": s.verdict,
                    }
                )

        await db.commit()
        pool_sum = await pool.pool_summary(db)

    ok = len(results) == 6 and all(r.get("verdict") == "effective" for r in results)
    print(
        json.dumps(
            {
                "ok": ok,
                "count": len(results),
                "formal_white_pool": pool_sum.get("formal_ready"),
                "strategies": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
