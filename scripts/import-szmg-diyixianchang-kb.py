"""Import SZMG × 第一现场 demo KB (fact cards + L2 stories) for keyword expand demos."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select

from app.core.database import async_session
from app.models.content_engine import KnowledgeBase, KnowledgeDocument
from app.services.content_engine import (
    add_document_and_chunk,
    create_knowledge_base,
    delete_document,
    refresh_kb_stats,
)
from app.services.geo_kb import ingest_tagged

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "pilot-demo" / "szmg-diyixianchang-kb"
INGEST_DIR = PACK / "ingest"
STORIES_DIR = PACK / "stories"
KB_SLUG = "szmg-diyixianchang-demo"
KB_NAME = "深圳广电×第一现场·拓词示范库"


async def _replace_by_title(db, kb_id, title: str) -> None:
    existing = await db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.knowledge_base_id == kb_id,
            KnowledgeDocument.title == title,
        )
    )
    if existing:
        await delete_document(db, doc_id=existing.id)


async def main() -> None:
    ingest_files = sorted(INGEST_DIR.glob("*.json"))
    story_files = sorted(STORIES_DIR.glob("*.md"))
    if not ingest_files:
        raise SystemExit(f"no ingest json under {INGEST_DIR}")

    async with async_session() as db:
        kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == KB_SLUG))
        if kb is None:
            kb = await create_knowledge_base(
                db,
                name=KB_NAME,
                slug=KB_SLUG,
                description="演示样例：事实卡定隶属 + L2 故事切片，供拓词选库。",
            )

        imported: list[dict] = []
        for path in ingest_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            title = payload["title"]
            await _replace_by_title(db, kb.id, title)
            doc = await ingest_tagged(
                db,
                kb=kb,
                title=title,
                body=payload["body"],
                tier=payload.get("tier") or "L2",
                tags=payload.get("tags") or {},
                fact_cards=payload.get("fact_cards") or [],
                source_url=payload.get("source_url"),
                external_id=payload.get("external_id"),
                external_approved=bool(payload.get("external_approved", True)),
            )
            imported.append(
                {
                    "title": doc.title,
                    "id": str(doc.id),
                    "tier": doc.tier,
                    "fact_cards": len(doc.fact_cards or []),
                    "chunks": doc.chunk_count,
                }
            )

        for path in story_files:
            title = f"story:{path.stem}"
            body = path.read_text(encoding="utf-8")
            await _replace_by_title(db, kb.id, title)
            doc = await add_document_and_chunk(
                db,
                kb=kb,
                title=title,
                body=body,
                source_path=str(path.relative_to(ROOT)).replace("\\", "/"),
                embed=True,
            )
            doc.tier = "L2"
            doc.tags = {
                "site_id": "szmg-demo",
                "task_bajua": "融媒传播",
                "doc_type": "故事正文",
                "source_org": "演示样例",
            }
            doc.review_state = "approved"
            doc.fact_cards = []
            await db.flush()
            imported.append(
                {
                    "title": doc.title,
                    "id": str(doc.id),
                    "tier": doc.tier,
                    "fact_cards": 0,
                    "chunks": doc.chunk_count,
                }
            )

        await refresh_kb_stats(db, kb.id)
        await db.commit()
        await db.refresh(kb)
        print(
            {
                "knowledge_base_id": str(kb.id),
                "slug": kb.slug,
                "doc_count": kb.doc_count,
                "chunk_count": kb.chunk_count,
                "imported": imported,
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
