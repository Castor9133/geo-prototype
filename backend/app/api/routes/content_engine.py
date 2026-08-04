"""内容引擎 API（M1 native-python）"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession, OptionalUser
from app.models.content_engine import (
    ContentPrompt,
    ContentTask,
    DistributionChannel,
    KnowledgeBase,
    KnowledgeDocument,
)
from app.services import content_engine as ce
from app.services.content_engine_utils import repo_root

router = APIRouter()

CHANNEL_TEMPLATES = [
    {
        "key": "wechat-article",
        "name": "公众号文章",
        "channel_type": "wechat",
        "flow_theme_keys": ["geoflow-template-01-ink-editorial", "geoflow-template-16-newsletter-letter"],
        "shell": "wechat",
    },
    {
        "key": "zhihu-answer",
        "name": "知乎回答",
        "channel_type": "zhihu",
        "flow_theme_keys": ["geoflow-template-14-knowledge-paper", "geoflow-template-18-consulting-insight"],
        "shell": "zhihu",
    },
    {
        "key": "xiaohongshu-note",
        "name": "小红书笔记",
        "channel_type": "xiaohongshu",
        "flow_theme_keys": ["geoflow-template-03-salmon-insight", "geoflow-template-12-saas-gradient"],
        "shell": "xiaohongshu",
    },
    {
        "key": "site-faq",
        "name": "官网 FAQ",
        "channel_type": "faq",
        "flow_theme_keys": ["apple_support_clone", "geoflow-template-05-wire-clean"],
        "shell": "faq",
    },
    {
        "key": "douyin-script",
        "name": "抖音口播提纲",
        "channel_type": "douyin",
        "flow_theme_keys": ["geoflow-template-06-public-broadcast", "geoflow-template-07-breaking-red"],
        "shell": "douyin",
    },
]


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    source_label: str | None = None


class KBUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class DocCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    source_url: str | None = None


class PromptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    kind: str = "content"
    sort_order: int = 100


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    kind: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    knowledge_base_id: uuid.UUID | None = None
    prompt_id: uuid.UUID | None = None
    channel_id: uuid.UUID | None = None
    template_key: str | None = None
    input_query: str | None = None
    meta: dict[str, Any] | None = None


class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    channel_type: str = "generic"
    template_key: str | None = None
    webhook_url: str | None = None


class SearchBody(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=6, ge=1, le=20)
    include_l3: bool = False
    bajua: str | None = None
    site_id: str | None = None
    tiers: list[str] | None = None


def _kb_dict(kb: KnowledgeBase) -> dict[str, Any]:
    return {
        "id": str(kb.id),
        "name": kb.name,
        "slug": kb.slug,
        "description": kb.description,
        "source_label": kb.source_label,
        "doc_count": kb.doc_count,
        "chunk_count": kb.chunk_count,
        "vectorized_count": kb.vectorized_count,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
    }


def _prompt_dict(p: ContentPrompt, *, include_body: bool = False) -> dict[str, Any]:
    data = {
        "id": str(p.id),
        "title": p.title,
        "kind": p.kind,
        "sort_order": p.sort_order,
        "is_active": p.is_active,
    }
    if include_body:
        data["body"] = p.body
    return data


def _safe_upload_name(name: str) -> str:
    base = Path(name or "upload.txt").name
    cleaned = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._") or "upload.txt"
    return cleaned[:180]


@router.get("/backend-status")
async def backend_status(_: OptionalUser = None):
    return ce.public_content_backend_status()


@router.get("/public/demo-summary")
async def public_demo_summary(db: DbSession, _: OptionalUser = None):
    """Suite 知识库/分发步只读：DJI 演示包摘要 + 最近任务草稿预览。"""
    kb = await db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == "dji-mini-5-pro-demo"))
    status = ce.public_content_backend_status()
    recent_q = select(ContentTask).order_by(ContentTask.created_at.desc()).limit(8)
    if kb:
        recent_q = recent_q.where(ContentTask.knowledge_base_id == kb.id)
    recent = (await db.execute(recent_q)).scalars().all()
    recent_tasks = [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "template_key": t.template_key,
            "has_draft": bool(t.draft_body),
            "draft_preview": (t.draft_body or "")[:280],
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in recent
    ]
    if not kb:
        return {
            **status,
            "demo_ready": False,
            "message": "尚未导入 DJI 演示包；请打开 /knowledge 或管理员后台点击导入",
            "public_path": "/knowledge",
            "admin_path": "/admin/content-engine",
            "recent_tasks": recent_tasks,
        }
    return {
        **status,
        "demo_ready": True,
        "knowledge_base": _kb_dict(kb),
        "public_path": f"/knowledge?kb={kb.id}",
        "admin_path": f"/admin/content-engine?kb={kb.id}",
        "recent_tasks": recent_tasks,
    }


@router.get("/channel-templates")
async def list_channel_templates(_: OptionalUser = None):
    """中国生态五渠道静态壳清单（自 GEOFlow 主题 key 对照，无编译管线）。"""
    return {"items": CHANNEL_TEMPLATES}


@router.get("/knowledge-bases")
async def list_knowledge_bases(db: DbSession, _: AdminUser):
    rows = (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))).scalars().all()
    return {"items": [_kb_dict(r) for r in rows]}


@router.post("/knowledge-bases")
async def create_kb(payload: KBCreate, db: DbSession, _: AdminUser):
    kb = await ce.create_knowledge_base(
        db,
        name=payload.name,
        description=payload.description,
        source_label=payload.source_label,
    )
    await db.commit()
    await db.refresh(kb)
    return _kb_dict(kb)


@router.patch("/knowledge-bases/{kb_id}")
async def update_kb(kb_id: uuid.UUID, payload: KBUpdate, db: DbSession, _: AdminUser):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    if payload.name is not None:
        kb.name = payload.name.strip()
    if payload.description is not None:
        kb.description = payload.description
    kb.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(kb)
    return _kb_dict(kb)


@router.delete("/knowledge-bases/{kb_id}")
async def delete_kb(kb_id: uuid.UUID, db: DbSession, _: AdminUser):
    ok = await ce.delete_knowledge_base(db, kb_id=kb_id)
    if not ok:
        raise HTTPException(404, "知识库不存在")
    await db.commit()
    return {"ok": True}


@router.get("/knowledge-bases/{kb_id}")
async def get_kb(kb_id: uuid.UUID, db: DbSession, _: AdminUser):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    docs = (
        await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
    ).scalars().all()
    return {
        **_kb_dict(kb),
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "chunk_count": d.chunk_count,
                "status": d.status,
                "source_path": d.source_path,
                "body": d.body or "",
                "tier": getattr(d, "tier", None) or "L2",
                "tags": getattr(d, "tags", None) or {},
                "review_state": getattr(d, "review_state", None) or "approved",
                "rag_eligible": bool(
                    (getattr(d, "review_state", "approved") == "approved")
                    and (
                        (getattr(d, "tier", "L2") or "L2").upper() == "L2"
                        or (
                            (getattr(d, "tier", "") or "").upper() == "L1"
                            and getattr(d, "local_confirmed_at", None)
                        )
                    )
                ),
            }
            for d in docs
        ],
    }


@router.post("/knowledge-bases/{kb_id}/documents")
async def add_document(kb_id: uuid.UUID, payload: DocCreate, db: DbSession, _: AdminUser):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    doc = await ce.add_document_and_chunk(
        db,
        kb=kb,
        title=payload.title,
        body=payload.body,
        source_url=payload.source_url,
        embed=True,
    )
    await db.commit()
    return {"id": str(doc.id), "title": doc.title, "chunk_count": doc.chunk_count}


@router.post("/knowledge-bases/{kb_id}/upload")
async def upload_document(
    kb_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    file: UploadFile = File(...),
    title: str | None = Form(None),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    filename = _safe_upload_name(file.filename or "upload.txt")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".md", ".txt", ".markdown"}:
        raise HTTPException(400, "仅支持 .md / .txt 上传")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    if len(raw) > 2_000_000:
        raise HTTPException(400, "文件过大（上限约 2MB）")
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "文件须为 UTF-8 文本") from exc

    upload_dir = repo_root() / "runtime" / "content-uploads" / str(kb_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4().hex[:10]}_{filename}"
    dest.write_bytes(raw)
    rel = str(dest.relative_to(repo_root())).replace("\\", "/")

    doc = await ce.add_document_and_chunk(
        db,
        kb=kb,
        title=(title or Path(filename).stem)[:300],
        body=body,
        source_path=rel,
        embed=True,
    )
    await db.commit()
    return {"id": str(doc.id), "title": doc.title, "chunk_count": doc.chunk_count, "source_path": rel}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: uuid.UUID, db: DbSession, _: AdminUser):
    kb_id = await ce.delete_document(db, doc_id=doc_id)
    if not kb_id:
        raise HTTPException(404, "文档不存在")
    await db.commit()
    return {"ok": True, "knowledge_base_id": str(kb_id)}


@router.post("/knowledge-bases/{kb_id}/search")
async def search_kb(kb_id: uuid.UUID, payload: SearchBody, db: DbSession, _: AdminUser):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知识库不存在")
    hits = await ce.search_chunks(
        db,
        kb_id=kb_id,
        query=payload.query,
        limit=payload.limit,
        include_l3=payload.include_l3,
        bajua=payload.bajua,
        site_id=payload.site_id,
        tiers=payload.tiers,
    )
    return {"items": hits}


@router.post("/knowledge-bases/import-dji-demo")
async def import_dji(db: DbSession, _: AdminUser):
    try:
        result = await ce.import_dji_demo_package(db)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@router.get("/prompts")
async def list_prompts(db: DbSession, _: AdminUser):
    await ce.ensure_default_prompts(db)
    await db.commit()
    rows = (
        await db.execute(
            select(ContentPrompt).where(ContentPrompt.is_active.is_(True)).order_by(ContentPrompt.sort_order)
        )
    ).scalars().all()
    return {"items": [_prompt_dict(p) for p in rows]}


@router.post("/prompt-library/restore")
async def restore_default_prompts(db: DbSession, _: AdminUser):
    """恢复内置提示词正文，并停用标题不在内置清单中的自定义项。"""
    rows = await ce.ensure_default_prompts(db, prune_custom=True)
    await db.commit()
    return {
        "restored": len(rows),
        "titles": [r.title for r in rows],
        "items": [_prompt_dict(p) for p in rows],
    }


@router.post("/prompts")
async def create_prompt(payload: PromptCreate, db: DbSession, _: AdminUser):
    row = ContentPrompt(
        title=payload.title.strip(),
        body=payload.body,
        kind=payload.kind or "content",
        sort_order=payload.sort_order,
        locale="zh-CN",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _prompt_dict(row, include_body=True)


@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: uuid.UUID, db: DbSession, _: AdminUser):
    p = await db.get(ContentPrompt, prompt_id)
    if not p:
        raise HTTPException(404, "提示词不存在")
    return _prompt_dict(p, include_body=True)


@router.patch("/prompts/{prompt_id}")
async def update_prompt(prompt_id: uuid.UUID, payload: PromptUpdate, db: DbSession, _: AdminUser):
    p = await db.get(ContentPrompt, prompt_id)
    if not p:
        raise HTTPException(404, "提示词不存在")
    if payload.title is not None:
        p.title = payload.title.strip()
    if payload.body is not None:
        p.body = payload.body
    if payload.kind is not None:
        p.kind = payload.kind
    if payload.sort_order is not None:
        p.sort_order = payload.sort_order
    if payload.is_active is not None:
        p.is_active = payload.is_active
    await db.commit()
    await db.refresh(p)
    return _prompt_dict(p, include_body=True)


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: uuid.UUID, db: DbSession, _: AdminUser):
    p = await db.get(ContentPrompt, prompt_id)
    if not p:
        raise HTTPException(404, "提示词不存在")
    p.is_active = False
    await db.commit()
    return {"ok": True}


@router.get("/tasks")
async def list_tasks(db: DbSession, _: AdminUser):
    rows = (await db.execute(select(ContentTask).order_by(ContentTask.created_at.desc()).limit(50))).scalars().all()
    return {
        "items": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "workflow_status": getattr(t, "workflow_status", None) or "claimed",
                "promote_suggestion": getattr(t, "promote_suggestion", None),
                "knowledge_base_id": str(t.knowledge_base_id) if t.knowledge_base_id else None,
                "template_key": t.template_key,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "has_draft": bool(t.draft_body or getattr(t, "template_draft_body", None)),
                "distributed": bool((t.meta or {}).get("distributed_at")),
            }
            for t in rows
        ]
    }


@router.post("/tasks")
async def create_task(payload: TaskCreate, db: DbSession, _: AdminUser):
    task = ContentTask(
        title=payload.title,
        knowledge_base_id=payload.knowledge_base_id,
        prompt_id=payload.prompt_id,
        channel_id=payload.channel_id,
        template_key=payload.template_key,
        input_query=payload.input_query or payload.title,
        status="pending",
        meta=dict(payload.meta or {}),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await ce.run_content_task(db, task.id)
    await db.commit()
    await db.refresh(task)

    return {
        "id": str(task.id),
        "status": task.status,
        "draft_preview": (task.draft_body or "")[:400],
        "template_key": task.template_key,
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: uuid.UUID, db: DbSession, _: AdminUser):
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "workflow_status": getattr(task, "workflow_status", None) or "claimed",
        "input_query": task.input_query,
        "draft_body": task.draft_body,
        "template_draft_body": getattr(task, "template_draft_body", None),
        "channel_draft_body": getattr(task, "channel_draft_body", None),
        "channel_key": getattr(task, "channel_key", None),
        "promote_suggestion": getattr(task, "promote_suggestion", None),
        "geo_run_id": str(task.geo_run_id) if getattr(task, "geo_run_id", None) else None,
        "error_message": task.error_message,
        "template_key": task.template_key,
        "knowledge_base_id": str(task.knowledge_base_id) if task.knowledge_base_id else None,
        "prompt_id": str(task.prompt_id) if task.prompt_id else None,
        "channel_id": str(task.channel_id) if task.channel_id else None,
        "meta": task.meta or {},
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


@router.post("/tasks/{task_id}/mark-distributed")
async def mark_distributed(task_id: uuid.UUID, db: DbSession, _: AdminUser):
    task = await db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    now = datetime.utcnow().isoformat()
    task.meta = {
        **(task.meta or {}),
        "distributed_at": now,
        "ready_at": now,
        "preview_only": True,
        "publish_status": "ready_not_published",
    }
    if task.status == "completed":
        task.status = "distributed"
    await db.commit()
    return {
        "id": str(task.id),
        "status": task.status,
        "meta": task.meta,
        "message": "已标记渠道壳就绪（未真实发布）",
    }


@router.get("/channels")
async def list_channels(db: DbSession, _: AdminUser):
    await ce.ensure_default_channels(db)
    await db.commit()
    rows = (
        await db.execute(select(DistributionChannel).where(DistributionChannel.is_active.is_(True)))
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "name": c.name,
                "channel_type": c.channel_type,
                "template_key": c.template_key,
            }
            for c in rows
        ]
    }


@router.post("/channels")
async def create_channel(payload: ChannelCreate, db: DbSession, _: AdminUser):
    ch = DistributionChannel(
        name=payload.name,
        channel_type=payload.channel_type,
        template_key=payload.template_key,
        webhook_url=payload.webhook_url,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return {
        "id": str(ch.id),
        "name": ch.name,
        "channel_type": ch.channel_type,
        "template_key": ch.template_key,
    }
