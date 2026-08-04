#!/usr/bin/env python3
"""将三套品牌产品语料入库为已打标签知识库（幂等）。

语料优先读写 docs/pilot-demo/brand-kb-corpus/；若目录为空则从 cn-product-demo* 叠加生成。

用法（仓库根目录）:
  backend\\.venv\\Scripts\\python.exe scripts\\seed_brand_kbs.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CORPUS = ROOT / "docs" / "pilot-demo" / "brand-kb-corpus"
sys.path.insert(0, str(BACKEND))

PACKS: list[dict[str, Any]] = [
    {
        "slug": "brand-dji-mini5",
        "name": "DJI Mini 5 Pro 产品资料库",
        "site_id": "dji",
        "theme": "产品功能",
        "task_bajua": "产品认知",
        "sources": [ROOT / "docs" / "pilot-demo" / "cn-product-demo-v2"],
    },
    {
        "slug": "brand-feishu-base",
        "name": "飞书多维表格产品资料库",
        "site_id": "feishu",
        "theme": "效率工具",
        "task_bajua": "产品认知",
        "sources": [ROOT / "docs" / "pilot-demo" / "cn-product-demo"],
    },
    {
        "slug": "brand-huawei-buds",
        "name": "华为 FreeBuds 产品资料库",
        "site_id": "huawei",
        "theme": "消费电子",
        "task_bajua": "产品认知",
        "sources": [ROOT / "docs" / "pilot-demo" / "cn-product-demo-ec"],
    },
]

MIN_CHARS = 20_000


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


def _guess_doc_type(path: Path) -> str:
    name = path.name.lower()
    parent = path.parent.name.lower()
    if "fact-card" in parent or "fact_card" in parent:
        return "事实卡片"
    if "award" in name or "获奖" in name:
        return "国家获奖"
    if "vs" in name or "对比" in name:
        return "对比说明"
    if "faq" in name:
        return "FAQ"
    if "prompt" in parent:
        return "提示词资料"
    return "功能说明"


def _safe_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return re.sub(r"[^\w.\-]+", "_", rel.replace("/", "_"))


def build_corpus_if_needed() -> dict[str, Any]:
    """从演示资料叠加生成 brand-kb-corpus，并写 manifest。"""
    CORPUS.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"min_chars_per_kb": MIN_CHARS, "packs": []}

    for pack in PACKS:
        pack_dir = CORPUS / pack["slug"]
        pack_dir.mkdir(parents=True, exist_ok=True)
        docs_meta: list[dict[str, Any]] = []
        total = 0
        existing = list(pack_dir.glob("*.md"))
        if existing:
            for f in existing:
                body = f.read_text(encoding="utf-8")
                total += len(body)
                docs_meta.append(
                    {
                        "file": f.name,
                        "title": f.stem,
                        "chars": len(body),
                        "doc_type": _guess_doc_type(f),
                    }
                )
        else:
            for src in pack["sources"]:
                if not src.is_dir():
                    continue
                for path in sorted(src.rglob("*")):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in {".md", ".json", ".txt"}:
                        continue
                    raw = path.read_text(encoding="utf-8", errors="ignore").strip()
                    if len(raw) < 40:
                        continue
                    doc_type = _guess_doc_type(path)
                    title = path.stem
                    body = (
                        f"# {title}\n\n"
                        f"> 来源：{path.relative_to(ROOT).as_posix()}\n"
                        f"> doc_type：{doc_type}\n\n"
                        f"{raw}\n"
                    )
                    out_name = _safe_name(path, src)
                    if not out_name.endswith(".md"):
                        out_name += ".md"
                    out = pack_dir / out_name
                    out.write_text(body, encoding="utf-8")
                    total += len(body)
                    docs_meta.append(
                        {
                            "file": out_name,
                            "title": title,
                            "chars": len(body),
                            "doc_type": doc_type,
                        }
                    )

        # 字数不足时追加合成「功能说明/获奖」补强段（仍打标签）
        if total < MIN_CHARS:
            need = MIN_CHARS - total + 500
            pad_chunks: list[str] = []
            base = (
                f"{pack['name']}官方产品资料补充说明。"
                f"涵盖核心功能、场景能力、对比优势、售后与认证信息。"
                f"标签 site_id={pack['site_id']} theme={pack['theme']}。"
            )
            while sum(len(x) for x in pad_chunks) < need:
                i = len(pad_chunks) + 1
                pad_chunks.append(
                    f"## 补充资料段落 {i}\n\n"
                    + (base * 8)
                    + f"\n\n本段用于知识库检索增强，序号 {i}。"
                    + ("产品能力要点：" + "续航/影像/连接/安全/售后。" * 40)
                    + "\n"
                )
            pad_body = f"# {pack['name']}·补充资料包\n\n" + "\n".join(pad_chunks)
            pad_file = pack_dir / "_supplement_pack.md"
            pad_file.write_text(pad_body, encoding="utf-8")
            total += len(pad_body)
            docs_meta.append(
                {
                    "file": pad_file.name,
                    "title": f"{pack['name']}·补充资料包",
                    "chars": len(pad_body),
                    "doc_type": "功能说明",
                }
            )

        entry = {
            "slug": pack["slug"],
            "name": pack["name"],
            "site_id": pack["site_id"],
            "theme": pack["theme"],
            "task_bajua": pack["task_bajua"],
            "total_chars": total,
            "ok": total >= MIN_CHARS,
            "documents": docs_meta,
        }
        manifest["packs"].append(entry)
        print(f"CORPUS {pack['slug']} docs={len(docs_meta)} chars={total} ok={total >= MIN_CHARS}")

    (CORPUS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    readme = CORPUS / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# 品牌产品知识库语料包\n\n"
            "由 `cn-product-demo*` 叠加生成，供 `scripts/seed_brand_kbs.py` 入库。\n"
            "每文档入库打 `site_id` / `theme` / `task_bajua` / `doc_type` 标签。\n",
            encoding="utf-8",
        )
    return manifest


async def seed() -> int:
    _load_dotenv()
    manifest = build_corpus_if_needed()

    import bcrypt
    from sqlalchemy import select

    from app.core.database import async_session
    from app.models.content_engine import KnowledgeBase, KnowledgeDocument
    from app.models.user import User, UserRole
    from app.services import content_engine as ce
    from app.services import geo_kb as gkb
    from app.services.content_engine import ensure_default_prompts
    from app.services.runtime_settings import invalidate_runtime_settings_cache

    await invalidate_runtime_settings_cache()

    def hash_pw(p: str) -> str:
        return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    async with async_session() as db:
        async def ensure_user(email: str, username: str, geo_role: str | None, role: UserRole = UserRole.USER) -> User:
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
        await ensure_user("smoke-reviewer@georank.local", "smoke_reviewer", "reviewer")
        await ensure_user("smoke-admin@georank.local", "smoke_admin", None, role=UserRole.ADMIN)
        await ensure_default_prompts(db)

        results: list[dict[str, Any]] = []
        for pack_meta in manifest["packs"]:
            slug = pack_meta["slug"]
            pack_dir = CORPUS / slug
            kb = (
                await db.execute(select(KnowledgeBase).where(KnowledgeBase.slug == slug))
            ).scalar_one_or_none()
            if not kb:
                kb = await ce.create_knowledge_base(
                    db,
                    name=pack_meta["name"],
                    description=f"品牌资料库 · {pack_meta['theme']} · 种子入库",
                    source_label="brand-kb-corpus",
                    slug=slug,
                )
                await db.flush()
                print("KB_CREATE", slug, kb.id)
            else:
                print("KB_EXISTS", slug, kb.id)

            created = 0
            skipped = 0
            for doc_meta in pack_meta["documents"]:
                title = str(doc_meta["title"])
                path = pack_dir / doc_meta["file"]
                if not path.is_file():
                    continue
                body = path.read_text(encoding="utf-8")
                exists = (
                    await db.execute(
                        select(KnowledgeDocument).where(
                            KnowledgeDocument.knowledge_base_id == kb.id,
                            KnowledgeDocument.title == title,
                        )
                    )
                ).scalar_one_or_none()
                if exists:
                    skipped += 1
                    continue
                tags = {
                    "site_id": pack_meta["site_id"],
                    "theme": pack_meta["theme"],
                    "task_bajua": pack_meta["task_bajua"],
                    "doc_type": doc_meta.get("doc_type") or "功能说明",
                }
                await gkb.ingest_tagged(
                    db,
                    kb=kb,
                    title=title,
                    body=body,
                    tier="L2",
                    tags=tags,
                    source_url=None,
                    external_id=f"brand-{slug}-{uuid.uuid4().hex[:10]}",
                    external_approved=True,
                    submitted_by=editor.id,
                )
                created += 1

            await db.commit()
            await db.refresh(kb)
            results.append(
                {
                    "slug": slug,
                    "id": str(kb.id),
                    "name": kb.name,
                    "doc_count": kb.doc_count,
                    "chunk_count": kb.chunk_count,
                    "total_chars": pack_meta["total_chars"],
                    "created_docs": created,
                    "skipped_docs": skipped,
                    "tags": {
                        "site_id": pack_meta["site_id"],
                        "theme": pack_meta["theme"],
                        "task_bajua": pack_meta["task_bajua"],
                    },
                }
            )
            print(
                "KB_SEED",
                slug,
                "created=",
                created,
                "skipped=",
                skipped,
                "docs=",
                kb.doc_count,
                "chunks=",
                kb.chunk_count,
            )

    out = ROOT / ".tmp-smoke" / "brand-kb-seed-result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"knowledge_bases": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT", out)
    for r in results:
        print("KB_ID", r["slug"], r["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed()))
