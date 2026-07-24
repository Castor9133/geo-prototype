"""
外部系统集成 API — GEO Suite / GEOFlow handoff / SSO / callback
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import AdminUser, CurrentUser, DbSession, OptionalUser
from app.services.geoflow_integration import (
    _extract_keywords_from_text,
    _titles_from_keywords,
    append_geoflow_event,
    append_handoff_log,
    build_handoff_brief_from_conversation,
    build_preview_handoff_result,
    execute_geoflow_handoff,
    fetch_geoflow_task_status,
    get_geoflow_api_token,
    get_geoflow_integration_config,
    issue_geoflow_sso_ticket,
    list_geoflow_events,
    list_handoff_log,
    public_geoflow_status,
    verify_callback_signature,
)
from app.services.runtime_settings import invalidate_runtime_settings_cache

router = APIRouter()


class GeoflowHandoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="manual", max_length=40)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    company_id: Optional[str] = Field(default=None, max_length=64)
    task_name: Optional[str] = Field(default=None, max_length=160)
    brief: Optional[str] = Field(default=None, max_length=20000)
    keywords: list[str] = Field(default_factory=list, max_length=40)
    force_preview: bool = False


class GeoflowSsoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_path: Optional[str] = Field(default="/geo_admin/dashboard", max_length=240)


@router.get("/geoflow/status")
async def geoflow_status():
    """公开状态：是否可展示 CTA、预览/实况模式。"""
    config = await get_geoflow_integration_config()
    token = await get_geoflow_api_token()
    return public_geoflow_status(config, has_token=bool(token))


@router.get("/geoflow/review")
async def geoflow_review(_: OptionalUser):
    """Suite 回看：最近 handoff + 发布回调事件。"""
    config = await get_geoflow_integration_config()
    token = await get_geoflow_api_token()
    return {
        "status": public_geoflow_status(config, has_token=bool(token)),
        "handoffs": await list_handoff_log(limit=10),
        "events": await list_geoflow_events(limit=20),
    }


@router.post("/geoflow/handoff")
async def geoflow_handoff(
    payload: GeoflowHandoffRequest,
    db: DbSession,
    _: OptionalUser,
):
    """
    将 GEORank 资产移交到 GEOFlow。

    - 未配置 Token：返回 preview 载荷（半成品演示可用）
    - 已配置：创建知识库 + 标题库 + 任务
    """
    source = (payload.source or "manual").strip().lower()
    if source not in {"manual", "solutions", "keywords", "plans", "diagnostic"}:
        raise HTTPException(status_code=400, detail="不支持的 handoff 来源")

    config = await get_geoflow_integration_config()
    token = await get_geoflow_api_token()

    task_name = (payload.task_name or "").strip()
    brief = (payload.brief or "").strip()
    keywords = [
        item.strip()
        for item in (payload.keywords or [])
        if isinstance(item, str) and item.strip()
    ][:20]
    company_id = (payload.company_id or "").strip() or None

    if payload.conversation_id:
        conv_title, conv_brief, conv_keywords = await build_handoff_brief_from_conversation(
            db,
            payload.conversation_id,
        )
        task_name = task_name or conv_title
        brief = brief or conv_brief
        if not keywords:
            keywords = conv_keywords

    if not keywords and brief:
        keywords = _extract_keywords_from_text(brief, limit=12)

    if not task_name:
        if keywords:
            task_name = f"GEORank · {keywords[0]}"
        else:
            task_name = "GEORank 内容任务"

    if not brief:
        if keywords:
            brief = (
                "# GEORank 拓词移交\n\n"
                + "\n".join(f"- {item}" for item in keywords)
                + "\n\n请据此生成知识约束、实体一致、可审计的 GEO 内容；"
                + "目标是答案引擎可读与可抽取，勿把页面就绪信号表述为 AI 答案引用率。"
            )
        else:
            raise HTTPException(status_code=400, detail="请提供 brief、keywords 或 conversation_id")

    titles = _titles_from_keywords(keywords, brief)
    live_ready = bool(config.get("enabled") and config.get("base_url") and token) and not payload.force_preview

    if not live_ready:
        result = build_preview_handoff_result(
            task_name=task_name,
            brief=brief,
            keywords=keywords,
            titles=titles,
            config=config,
        )
        result["source"] = source
        result["company_id"] = company_id or config.get("default_company_id")
        return result

    result: dict[str, Any] = await execute_geoflow_handoff(
        task_name=task_name,
        brief=brief,
        keywords=keywords,
        config=config,
        token=token,
        company_id=company_id,
    )
    result["source"] = source
    await append_handoff_log(
        db,
        {
            **{k: result.get(k) for k in (
                "mode", "status", "message", "task_id", "task_name",
                "company_id", "geoflow_task_url", "geoflow_admin_url", "source",
            )},
            "at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.commit()
    await invalidate_runtime_settings_cache()
    return result


@router.post("/geoflow/sso-ticket")
async def geoflow_sso_ticket(payload: GeoflowSsoRequest, user: CurrentUser):
    """为已登录用户签发 GEOFlow SSO 一次性 ticket。"""
    if str(getattr(user.role, "value", user.role) or "") not in {"admin", "enterprise"}:
        # 普通用户也可换票进入只读演示；更严可改为 AdminUser
        pass
    config = await get_geoflow_integration_config()
    return issue_geoflow_sso_ticket(user=user, config=config, next_path=payload.next_path)


@router.get("/geoflow/tasks/{task_id}")
async def geoflow_task_status(task_id: str, _: OptionalUser):
    """代理查询 GEOFlow 任务状态（需已配置 Token）。"""
    config = await get_geoflow_integration_config()
    token = await get_geoflow_api_token()
    if not (config.get("enabled") and config.get("base_url") and token):
        raise HTTPException(status_code=400, detail="GEOFlow 未进入 live 模式，无法查询任务")
    return await fetch_geoflow_task_status(task_id=task_id, config=config, token=token)


@router.post("/geoflow/callback")
async def geoflow_callback(request: Request, db: DbSession):
    """接收 GEOFlow 发布等事件（HMAC 签名）。"""
    raw = await request.body()
    signature = request.headers.get("X-GeoSuite-Signature") or request.headers.get("x-geosuite-signature")
    if not verify_callback_signature(raw, signature):
        raise HTTPException(status_code=401, detail="回调签名无效")

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="回调 JSON 无效") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="回调体必须是对象")

    event = {
        "event": str(payload.get("event") or "unknown")[:80],
        "task_id": payload.get("task_id"),
        "article_id": payload.get("article_id"),
        "public_url": str(payload.get("public_url") or "")[:500],
        "external_company_id": str(payload.get("external_company_id") or "")[:64] or None,
        "occurred_at": str(payload.get("occurred_at") or datetime.now(timezone.utc).isoformat())[:64],
        "received_at": datetime.now(timezone.utc).isoformat(),
        "raw": {k: payload.get(k) for k in ("title", "slug", "status") if k in payload},
    }
    events = await append_geoflow_event(db, event)
    await db.commit()
    await invalidate_runtime_settings_cache()
    return {"ok": True, "stored": len(events), "event": event}


@router.get("/geoflow/events")
async def geoflow_events(_: AdminUser):
    return {"items": await list_geoflow_events(limit=50)}
