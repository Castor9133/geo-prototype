"""Import DJI content articles into existing demo KB (chunk + embed)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select

from app.core.database import async_session
from app.models.content_engine import KnowledgeBase, KnowledgeDocument
from app.services.content_engine import add_document_and_chunk, delete_document, refresh_kb_stats

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "docs" / "pilot-demo" / "cn-product-demo-v2" / "content-articles"
KB_SLUG = "dji-mini-5-pro-demo"
SOURCE_URL = "https://www.dji.com/cn/mini-5-pro"


async def main() -> None:
    files = sorted(ARTICLES_DIR.glob("article-*.md"))
    if not files:
        raise SystemExit(f"no articles under {ARTICLES_DIR}")

    async with async_session() as db:
        kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == KB_SLUG))
        if not kb:
            raise SystemExit(f"KB slug={KB_SLUG} not found; import DJI demo package first")

        imported = []
        for path in files:
            title = path.stem
            body = path.read_text(encoding="utf-8")
            existing = await db.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.knowledge_base_id == kb.id,
                    KnowledgeDocument.title == title,
                )
            )
            if existing:
                await delete_document(db, doc_id=existing.id)

            doc = await add_document_and_chunk(
                db,
                kb=kb,
                title=title,
                body=body,
                source_path=str(path.relative_to(ROOT)).replace("\\", "/"),
                source_url=SOURCE_URL,
                embed=True,
            )
            imported.append({"title": doc.title, "id": str(doc.id), "chunks": doc.chunk_count})

        await refresh_kb_stats(db, kb.id)
        await db.commit()
        await db.refresh(kb)

        print(
            {
                "knowledge_base_id": str(kb.id),
                "slug": kb.slug,
                "doc_count": kb.doc_count,
                "chunk_count": kb.chunk_count,
                "vectorized_count": kb.vectorized_count,
                "imported": imported,
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
