"""内容引擎业务：切片、向量、检索、生成、演示包导入。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content_engine import (
    ContentPrompt,
    ContentTask,
    DistributionChannel,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.services.ai_client import chat_completion, get_embedding
from app.services.content_engine_utils import (
    CHINA_PROMPTS,
    cosine,
    local_hash_embedding,
    repo_root,
    slugify,
    soften_markdown_prose,
    split_chunks,
)
from app.services.geo_observe_script import build_generation_focus_block, get_ai_focus_config

# 兼容旧导入名
_slugify = slugify
_repo_root = repo_root


def content_backend_mode() -> str:
    mode = (settings.CONTENT_BACKEND_MODE or "native-python").strip().lower()
    if mode not in {"native-python", "legacy-flow"}:
        return "native-python"
    return mode


def public_content_backend_status() -> dict[str, Any]:
    mode = content_backend_mode()
    return {
        "mode": mode,
        "native": mode == "native-python",
        "legacy_flow": mode == "legacy-flow",
        "public_path": "/knowledge",
        "admin_path": "/admin/content-engine",
        "materials_path": "/knowledge",
        "note": (
            "知识库/任务/分发走 GEORank 原生 Python"
            if mode == "native-python"
            else "Suite 仍可 handoff 到 GEOFlow（F2 对照）"
        ),
    }


async def embed_text(text: str) -> list[float]:
    try:
        if settings.effective_embedding_key:
            return await get_embedding(text)
    except Exception:
        pass
    return local_hash_embedding(text)


async def refresh_kb_stats(db: AsyncSession, kb_id: uuid.UUID) -> None:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return
    docs = await db.scalar(
        select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    )
    chunks = await db.scalar(
        select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id)
    )
    vect = await db.scalar(
        select(func.count())
        .select_from(KnowledgeChunk)
        .where(KnowledgeChunk.knowledge_base_id == kb_id, KnowledgeChunk.embedding.is_not(None))
    )
    kb.doc_count = int(docs or 0)
    kb.chunk_count = int(chunks or 0)
    kb.vectorized_count = int(vect or 0)
    kb.updated_at = datetime.utcnow()


async def create_knowledge_base(
    db: AsyncSession,
    *,
    name: str,
    description: str = "",
    source_label: str | None = None,
    slug: str | None = None,
) -> KnowledgeBase:
    slug_val = slug or _slugify(name)
    existing = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == slug_val))
    if existing:
        suffix = uuid.uuid4().hex[:6]
        slug_val = f"{slug_val}-{suffix}"
    kb = KnowledgeBase(
        name=name.strip(),
        slug=slug_val,
        description=description or None,
        source_label=source_label,
        meta={},
    )
    db.add(kb)
    await db.flush()
    return kb


async def add_document_and_chunk(
    db: AsyncSession,
    *,
    kb: KnowledgeBase,
    title: str,
    body: str,
    source_path: str | None = None,
    source_url: str | None = None,
    embed: bool = True,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        title=title.strip()[:300],
        body=body,
        source_path=source_path,
        source_url=source_url,
        status="processing",
    )
    db.add(doc)
    await db.flush()
    pieces = split_chunks(body)
    for idx, piece in enumerate(pieces):
        emb = await embed_text(piece) if embed else None
        db.add(
            KnowledgeChunk(
                knowledge_base_id=kb.id,
                document_id=doc.id,
                chunk_index=idx,
                content=piece,
                embedding=emb,
                token_estimate=max(1, len(piece) // 2),
            )
        )
    doc.chunk_count = len(pieces)
    doc.status = "ready"
    await refresh_kb_stats(db, kb.id)
    return doc


async def delete_document(db: AsyncSession, *, doc_id: uuid.UUID) -> uuid.UUID | None:
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        return None
    kb_id = doc.knowledge_base_id
    chunks = (
        await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id))
    ).scalars().all()
    for chunk in chunks:
        await db.delete(chunk)
    await db.delete(doc)
    await refresh_kb_stats(db, kb_id)
    return kb_id


async def delete_knowledge_base(db: AsyncSession, *, kb_id: uuid.UUID) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return False
    docs = (
        await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id))
    ).scalars().all()
    for doc in docs:
        await delete_document(db, doc_id=doc.id)
    await db.delete(kb)
    return True


async def ensure_default_channels(db: AsyncSession) -> list[DistributionChannel]:
    """五渠道演示壳：公众号 / 知乎 / 小红书 / 官网 FAQ / 抖音口播。"""
    defaults = [
        {"name": "公众号文章", "channel_type": "wechat", "template_key": "wechat-article"},
        {"name": "知乎回答", "channel_type": "zhihu", "template_key": "zhihu-answer"},
        {"name": "小红书笔记", "channel_type": "xiaohongshu", "template_key": "xiaohongshu-note"},
        {"name": "官网 FAQ", "channel_type": "faq", "template_key": "site-faq"},
        {"name": "抖音口播提纲", "channel_type": "douyin", "template_key": "douyin-script"},
    ]
    created: list[DistributionChannel] = []
    for item in defaults:
        existing = await db.scalar(
            select(DistributionChannel).where(DistributionChannel.template_key == item["template_key"])
        )
        if existing:
            created.append(existing)
            continue
        row = DistributionChannel(
            name=item["name"],
            channel_type=item["channel_type"],
            template_key=item["template_key"],
            meta={"shell": True},
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return created


async def search_chunks(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    query: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    q_emb = await embed_text(query)
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id).limit(500)
    )
    rows = list(result.scalars().all())
    scored = sorted(
        ((cosine(q_emb, c.embedding), c) for c in rows),
        key=lambda x: x[0],
        reverse=True,
    )
    out = []
    for score, chunk in scored[:limit]:
        out.append(
            {
                "id": str(chunk.id),
                "score": round(float(score), 4),
                "content": chunk.content,
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
            }
        )
    return out


async def ensure_default_prompts(
    db: AsyncSession,
    *,
    prune_custom: bool = False,
) -> list[ContentPrompt]:
    existing = list((await db.execute(select(ContentPrompt))).scalars().all())
    by_title = {row.title: row for row in existing}
    builtin_titles = {item["title"] for item in CHINA_PROMPTS}
    result: list[ContentPrompt] = []
    for item in CHINA_PROMPTS:
        row = by_title.get(item["title"])
        if row is None:
            row = ContentPrompt(
                title=item["title"],
                body=item["body"],
                sort_order=item["sort_order"],
                kind="content",
                locale="zh-CN",
            )
            db.add(row)
            result.append(row)
            continue
        # 同步内置提示词正文，避免演示库长期停留在旧版「过 Markdown」指令
        row.body = item["body"]
        row.sort_order = item["sort_order"]
        row.is_active = True
        result.append(row)
    # 旧版内置标题（及 prune_custom 时的自定义项）停用，保证下拉只见细版 5 套
    for row in existing:
        if row.title not in builtin_titles:
            if prune_custom or row.kind == "content":
                row.is_active = False
    await db.flush()
    return result or existing


def _task_entity(task: ContentTask) -> str:
    meta = task.meta if isinstance(task.meta, dict) else {}
    entity = str(meta.get("entity") or "").strip()
    if entity:
        return entity
    title = (task.title or "").strip()
    if "·" in title:
        return title.split("·", 1)[0].strip() or title
    return title or "产品"


async def run_content_task(db: AsyncSession, task_id: uuid.UUID) -> ContentTask:
    task = await db.get(ContentTask, task_id)
    if not task:
        raise ValueError("task not found")
    task.status = "running"
    await db.flush()
    try:
        knowledge_block = ""
        if task.knowledge_base_id:
            hits = await search_chunks(
                db,
                kb_id=task.knowledge_base_id,
                query=task.input_query or task.title,
                limit=6,
            )
            knowledge_block = "\n\n".join(h["content"] for h in hits) or "（暂无检索命中）"
        prompt_body = (
            "请根据知识写一篇答案优先的中文 GEO 正文。"
            "输出纯中文成稿，不要使用 Markdown 符号（井号、加粗、分隔线、反引号）。"
        )
        if task.prompt_id:
            prompt = await db.get(ContentPrompt, task.prompt_id)
            if prompt:
                prompt_body = prompt.body
        filled = (
            prompt_body.replace("{{title}}", task.title)
            .replace("{{keyword}}", task.input_query or task.title)
            .replace("{{entity}}", _task_entity(task))
            .replace("{{Knowledge}}", knowledge_block)
        )
        meta = task.meta if isinstance(task.meta, dict) else {}
        focus_block = ""
        if meta.get("ai_focus_inject"):
            platforms = meta.get("target_platforms") or meta.get("ai_platforms") or []
            if isinstance(platforms, str):
                platforms = [platforms]
            try:
                focus_script = await get_ai_focus_config()
                focus_block = build_generation_focus_block(
                    focus_script,
                    [str(p) for p in platforms if p],
                )
            except Exception:
                focus_block = ""
            if focus_block:
                filled = f"{focus_block}\n\n{filled}"
        messages = [
            {
                "role": "system",
                "content": (
                    "你是严谨的中文 GEO 内容作者，参数必须来自知识，禁止编造。"
                    "输出像已排版的公众号/官网正文：纯中文、少符号。"
                    "禁止 Markdown 语法（不要用 #、**、---、反引号、[]()）。"
                    "用「一、二、三」或空行分段；FAQ 用「问：」「答：」。"
                    "若用户消息含「目标 AI 生成侧重」，在不编造的前提下优先满足该侧重。"
                ),
            },
            {"role": "user", "content": filled},
        ]
        llm_error: str | None = None
        try:
            draft = await chat_completion(messages, temperature=0.3, max_tokens=2500)
        except Exception as llm_exc:  # noqa: BLE001
            llm_error = f"{type(llm_exc).__name__}: {llm_exc}"[:800]
            focus_note = f"{focus_block}\n\n" if focus_block else ""
            draft = (
                f"{task.title}\n\n"
                f"（本地降级草稿：LLM 未配置或调用失败）\n"
                f"原因：{llm_error}\n\n"
                f"{focus_note}"
                f"答案摘要\n基于知识库检索整理如下要点。\n\n{knowledge_block[:1200]}\n"
            )
        task.draft_body = soften_markdown_prose(draft)
        task.status = "completed"
        task.finished_at = datetime.utcnow()
        task.error_message = llm_error
        task.meta = {
            **(task.meta or {}),
            "knowledge_chars": len(knowledge_block),
            "ai_focus_applied": bool(focus_block),
            "llm_ok": llm_error is None,
            "llm_fallback_reason": llm_error,
        }
    except Exception as exc:  # noqa: BLE001
        task.status = "failed"
        task.error_message = str(exc)[:1000]
        task.finished_at = datetime.utcnow()
    await db.flush()
    return task


async def import_dji_demo_package(db: AsyncSession) -> dict[str, Any]:
    """从 docs/pilot-demo/cn-product-demo-v2 导入 DJI 演示包。"""
    root = repo_root() / "docs" / "pilot-demo" / "cn-product-demo-v2"
    fact_dir = root / "fact-cards"
    files = sorted(fact_dir.glob("*.md")) if fact_dir.is_dir() else []
    if not files:
        merged = root / "fact-cards.md"
        bodies = [merged.read_text(encoding="utf-8")] if merged.is_file() else []
        titles = ["DJI Mini 5 Pro 事实卡合集"] if bodies else []
    else:
        bodies = [p.read_text(encoding="utf-8") for p in files]
        titles = [p.stem for p in files]

    if not bodies:
        raise FileNotFoundError(f"未找到演示包事实卡：{fact_dir}")

    slug = "dji-mini-5-pro-demo"
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == slug))
    if not kb:
        kb = await create_knowledge_base(
            db,
            name="中文产品演示包·DJI Mini 5 Pro",
            description="官方公开资料整理的演示知识库（介绍/参数/场景/FAQ）",
            source_label="cn-product-demo-v2",
            slug=slug,
        )
    else:
        # 清空旧文档切片后重导
        old_docs = (
            await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb.id))
        ).scalars().all()
        for d in old_docs:
            chunks = (
                await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == d.id))
            ).scalars().all()
            for c in chunks:
                await db.delete(c)
            await db.delete(d)
        await db.flush()

    imported = 0
    for title, body in zip(titles, bodies):
        await add_document_and_chunk(
            db,
            kb=kb,
            title=title,
            body=body,
            source_path=f"docs/pilot-demo/cn-product-demo-v2/{title}",
            source_url="https://www.dji.com/cn/mini-5-pro",
            embed=True,
        )
        imported += 1

    await ensure_default_prompts(db)
    await ensure_default_channels(db)
    await db.commit()
    await db.refresh(kb)
    return {
        "knowledge_base_id": str(kb.id),
        "slug": kb.slug,
        "documents_imported": imported,
        "chunk_count": kb.chunk_count,
        "vectorized_count": kb.vectorized_count,
    }
