"""
GEOFlow 薄集成：配置、公开状态、handoff 代理。

GEORank 负责诊断 / 问答 / 拓词；GEOFlow 负责内容生成与分发。
本模块只做契约转发，不合并两套业务栈。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.runtime_settings import (
    _pick_bool,
    _pick_int,
    _pick_string,
    _safe_http_url,
    invalidate_runtime_settings_cache,
)
from app.services.settings_security import MASKED_VALUE

if TYPE_CHECKING:
    from app.models.user import User

GEOFLOW_INTEGRATION_SETTING_KEY = "geoflow_integration"
GEOFLOW_API_TOKEN_SETTING_KEY = "geoflow_api_token"

DEFAULT_GEOFLOW_INTEGRATION = {
    "enabled": False,
    "base_url": "http://host.docker.internal:18080",
    "public_base_url": "http://localhost:18080",
    "timeout_seconds": 30,
    "public_cta_label": "发送到 GEOFlow",
    "prompt_id": None,
    "ai_model_id": None,
    "auto_start": False,
    "draft_limit": 3,
    "article_limit": 3,
    "need_review": True,
    "publish_scope": "local_and_distribution",
    # Phase2：默认绑定的 GEORank company_id（handoff 可覆盖）
    "default_company_id": None,
}

GEOFLOW_EVENTS_SETTING_KEY = "geoflow_callback_events"
GEOFLOW_HANDOFF_LOG_SETTING_KEY = "geoflow_handoff_log"
SSO_TICKET_TTL_SECONDS = 60


def get_default_geoflow_integration_config() -> dict[str, Any]:
    return dict(DEFAULT_GEOFLOW_INTEGRATION)


def _is_masked_secret(value: str | None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return set(value) <= {"•", " "}


def _build_geoflow_integration_config(values: dict[str, Any]) -> dict[str, Any]:
    defaults = get_default_geoflow_integration_config()
    raw = values.get(GEOFLOW_INTEGRATION_SETTING_KEY)
    if not isinstance(raw, dict):
        raw = {}

    env_enabled = _pick_bool(getattr(settings, "GEOFLOW_ENABLED", None), defaults["enabled"])
    env_base = _pick_string(getattr(settings, "GEOFLOW_BASE_URL", ""), defaults["base_url"])
    env_public = _pick_string(
        getattr(settings, "GEOFLOW_PUBLIC_BASE_URL", ""),
        defaults["public_base_url"],
    )

    prompt_id = raw.get("prompt_id", defaults["prompt_id"])
    ai_model_id = raw.get("ai_model_id", defaults["ai_model_id"])
    try:
        prompt_id = int(prompt_id) if prompt_id not in (None, "") else None
    except (TypeError, ValueError):
        prompt_id = None
    try:
        ai_model_id = int(ai_model_id) if ai_model_id not in (None, "") else None
    except (TypeError, ValueError):
        ai_model_id = None

    publish_scope = _pick_string(raw.get("publish_scope"), defaults["publish_scope"])
    if publish_scope not in {
        "local_and_distribution",
        "distribution_only",
        "local_only",
    }:
        publish_scope = defaults["publish_scope"]

    return {
        "enabled": _pick_bool(raw.get("enabled"), env_enabled),
        "base_url": _safe_http_url(
            raw.get("base_url") or env_base,
            defaults["base_url"],
            max_length=240,
        ),
        "public_base_url": _safe_http_url(
            raw.get("public_base_url") or env_public,
            defaults["public_base_url"],
            max_length=240,
        ),
        "timeout_seconds": min(
            120,
            max(5, _pick_int(raw.get("timeout_seconds"), defaults["timeout_seconds"], default=30)),
        ),
        "public_cta_label": _pick_string(
            raw.get("public_cta_label"),
            defaults["public_cta_label"],
        )[:80]
        or defaults["public_cta_label"],
        "prompt_id": prompt_id,
        "ai_model_id": ai_model_id,
        "auto_start": _pick_bool(raw.get("auto_start"), defaults["auto_start"]),
        "draft_limit": min(
            50,
            max(1, _pick_int(raw.get("draft_limit"), defaults["draft_limit"], default=3)),
        ),
        "article_limit": min(
            50,
            max(1, _pick_int(raw.get("article_limit"), defaults["article_limit"], default=3)),
        ),
        "need_review": _pick_bool(raw.get("need_review"), defaults["need_review"]),
        "publish_scope": publish_scope,
        "default_company_id": _pick_string(raw.get("default_company_id"), "")[:64] or None,
    }


def normalize_geoflow_integration_payload(
    payload: dict[str, Any],
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = current if isinstance(current, dict) else get_default_geoflow_integration_config()
    return _build_geoflow_integration_config(
        {GEOFLOW_INTEGRATION_SETTING_KEY: {**base, **(payload or {})}}
    )


async def get_geoflow_integration_config(force_refresh: bool = False) -> dict[str, Any]:
    from app.services.runtime_settings import _load_runtime_settings

    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    return _build_geoflow_integration_config(values)


def public_geoflow_status(config: dict[str, Any], *, has_token: bool) -> dict[str, Any]:
    ready = bool(config.get("enabled") and config.get("base_url") and has_token)
    public_base = config.get("public_base_url") or ""
    if "127.0.0.1" in public_base:
        public_base = public_base.replace("127.0.0.1", "localhost")
    return {
        "enabled": bool(config.get("enabled")),
        "configured": ready,
        "public_base_url": public_base,
        "public_cta_label": config.get("public_cta_label")
        or DEFAULT_GEOFLOW_INTEGRATION["public_cta_label"],
        "suite_path": "/suite?step=review",
        "mode": "live" if ready else "preview",
        "sso_available": bool(_suite_hmac_secret(prefer_callback=False)),
        "default_company_id": config.get("default_company_id"),
    }


def admin_geoflow_payload(config: dict[str, Any], *, has_token: bool) -> dict[str, Any]:
    return {
        **config,
        "api_token": MASKED_VALUE if has_token else "",
        "has_api_token": has_token,
        "status": public_geoflow_status(config, has_token=has_token),
    }


async def get_geoflow_api_token(force_refresh: bool = False) -> str:
    from app.services.runtime_settings import _load_runtime_settings

    if force_refresh:
        await invalidate_runtime_settings_cache()
    values = await _load_runtime_settings()
    token = _pick_string(values.get(GEOFLOW_API_TOKEN_SETTING_KEY))
    if token:
        return token
    return _pick_string(getattr(settings, "GEOFLOW_API_TOKEN", ""))


async def store_geoflow_integration_setting(
    db: AsyncSession,
    admin: "User",
    config: dict[str, Any],
    *,
    api_token: str | None = None,
) -> None:
    from app.models.settings import Setting

    result = await db.execute(select(Setting).where(Setting.key == GEOFLOW_INTEGRATION_SETTING_KEY))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = config
        setting.category = "integrations"
        setting.is_public = False
        setting.updated_by = admin.id
    else:
        db.add(
            Setting(
                key=GEOFLOW_INTEGRATION_SETTING_KEY,
                value=config,
                category="integrations",
                is_public=False,
                updated_by=admin.id,
            )
        )

    if api_token is not None and not _is_masked_secret(api_token):
        token_value = api_token.strip()
        token_result = await db.execute(
            select(Setting).where(Setting.key == GEOFLOW_API_TOKEN_SETTING_KEY)
        )
        token_setting = token_result.scalar_one_or_none()
        if token_setting:
            token_setting.value = token_value
            token_setting.category = "api_keys"
            token_setting.is_public = False
            token_setting.updated_by = admin.id
        else:
            db.add(
                Setting(
                    key=GEOFLOW_API_TOKEN_SETTING_KEY,
                    value=token_value,
                    category="api_keys",
                    is_public=False,
                    updated_by=admin.id,
                )
            )


def _extract_keywords_from_text(text: str, *, limit: int = 12) -> list[str]:
    parts = re.split(r"[\n,，、;；|]+", text or "")
    keywords: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = re.sub(r"\s+", " ", part).strip(" -\t•*#")
        if len(item) < 2 or len(item) > 80:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(item)
        if len(keywords) >= limit:
            break
    return keywords


def _titles_from_keywords(keywords: list[str], brief: str) -> list[dict[str, str]]:
    titles: list[dict[str, str]] = []
    for keyword in keywords[:12]:
        titles.append(
            {
                "title": f"{keyword}：GEO 可见性实践指南",
                "keyword": keyword,
            }
        )
    if not titles and brief.strip():
        titles.append(
            {
                "title": (brief.strip().splitlines()[0][:80] or "GEO 内容任务"),
                "keyword": "GEO",
            }
        )
    return titles


async def build_handoff_brief_from_conversation(
    db: AsyncSession,
    conversation_id: str,
) -> tuple[str, str, list[str]]:
    from app.models.conversation import Conversation, Message, MessageRole

    cid = UUID(conversation_id)
    result = await db.execute(select(Conversation).where(Conversation.id == cid))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="问答会话不存在")

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == cid).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    if not messages:
        raise HTTPException(status_code=400, detail="会话尚无内容，无法发送到 GEOFlow")

    lines = [f"# GEORank 问答移交：{conversation.title or '未命名对话'}", ""]
    keywords: list[str] = []
    for message in messages[-12:]:
        role = "用户" if message.role == MessageRole.USER else "助手"
        content = (message.content or "").strip()
        if not content:
            continue
        lines.append(f"## {role}")
        lines.append(content)
        lines.append("")
        keywords.extend(_extract_keywords_from_text(content, limit=4))

    deduped: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    title = conversation.title or "GEORank 问答内容任务"
    return title, "\n".join(lines).strip(), deduped[:12]


def build_preview_handoff_result(
    *,
    task_name: str,
    brief: str,
    keywords: list[str],
    titles: list[dict[str, str]],
    config: dict[str, Any],
) -> dict[str, Any]:
    admin_url = urljoin(
        (config.get("public_base_url") or "http://localhost:18080").rstrip("/") + "/",
        "geo_admin/tasks",
    )
    return {
        "mode": "preview",
        "status": "preview",
        "message": "GEOFlow 尚未配置完整凭证。已生成可移交载荷预览，配置 Token 后可一键创建真实任务。",
        "task_name": task_name,
        "brief_preview": brief[:1200],
        "keywords": keywords,
        "titles": titles,
        "geoflow_admin_url": admin_url,
        "suite_path": "/suite?step=review",
        "next_steps": [
            "在后台「系统设置 → GEO Suite」填写 GEOFlow base_url 与 API Token",
            "确认 GEOFlow 中已有可用的 content 提示词与 chat 模型",
            "再次点击「发送到 GEOFlow」创建任务，或打开 /suite?step=review 回看预览载荷",
        ],
    }


async def _geoflow_request(
    config: dict[str, Any],
    token: str,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = (config.get("base_url") or "").rstrip("/")
    url = f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    timeout = float(config.get("timeout_seconds") or 30)
    # 使用普通客户端：Suite 本地联调依赖 localhost / host.docker.internal，
    # 不能走 LLM Provider 的公网 pinning 策略。
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        response = await client.request(method, url, headers=headers, json=json_body)
    if response.status_code >= 400:
        detail = response.text[:500]
        raise HTTPException(
            status_code=502,
            detail=f"GEOFlow 接口失败 ({response.status_code}): {detail}",
        )
    if not response.content:
        return {}
    data = response.json()
    if isinstance(data, dict):
        return data
    return {"data": data}


async def resolve_catalog_defaults(
    config: dict[str, Any],
    token: str,
) -> tuple[int, int]:
    prompt_id = config.get("prompt_id")
    ai_model_id = config.get("ai_model_id")
    if prompt_id and ai_model_id:
        return int(prompt_id), int(ai_model_id)

    catalog = await _geoflow_request(config, token, "GET", "/api/v1/catalog")
    prompts = catalog.get("prompts") or (catalog.get("data") or {}).get("prompts") or []
    models = (
        catalog.get("ai_models")
        or catalog.get("models")
        or (catalog.get("data") or {}).get("ai_models")
        or []
    )

    if not prompt_id:
        for item in prompts:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or item.get("prompt_type") or "") in {"content", "article", ""}:
                if item.get("id") is not None:
                    prompt_id = int(item["id"])
                    break
        if prompt_id is None and prompts and isinstance(prompts[0], dict) and prompts[0].get("id") is not None:
            prompt_id = int(prompts[0]["id"])

    if not ai_model_id:
        for item in models:
            if not isinstance(item, dict):
                continue
            status_value = str(item.get("status") or "active").lower()
            kind = str(item.get("type") or item.get("capability") or "chat").lower()
            if status_value in {"active", "enabled", "1", "true"} and "embed" not in kind:
                if item.get("id") is not None:
                    ai_model_id = int(item["id"])
                    break
        if ai_model_id is None and models and isinstance(models[0], dict) and models[0].get("id") is not None:
            ai_model_id = int(models[0]["id"])

    if not prompt_id or not ai_model_id:
        raise HTTPException(
            status_code=400,
            detail="GEOFlow 缺少可用的提示词或 AI 模型，请先在 GEOFlow 后台配置，或在 GEO Suite 设置中指定 prompt_id / ai_model_id",
        )
    return int(prompt_id), int(ai_model_id)


def _unwrap_resource_id(payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        return None
    if payload.get("id") is not None:
        return payload["id"]
    data = payload.get("data")
    if isinstance(data, dict):
        if data.get("id") is not None:
            return data["id"]
        item = data.get("item")
        if isinstance(item, dict) and item.get("id") is not None:
            return item["id"]
        task = data.get("task")
        if isinstance(task, dict) and task.get("id") is not None:
            return task["id"]
    item = payload.get("item")
    if isinstance(item, dict) and item.get("id") is not None:
        return item["id"]
    return None


def _suite_hmac_secret(*, prefer_callback: bool = False) -> str:
    callback = _pick_string(getattr(settings, "GEOSUITE_CALLBACK_SECRET", ""))
    sso = _pick_string(getattr(settings, "GEOSUITE_SSO_SECRET", ""))
    if prefer_callback:
        return callback or sso
    return sso or callback


def issue_geoflow_sso_ticket(
    *,
    user: "User",
    config: dict[str, Any],
    next_path: str | None = None,
) -> dict[str, Any]:
    import base64
    import hashlib
    import hmac
    import json
    import time
    from uuid import uuid4

    secret = _suite_hmac_secret(prefer_callback=False)
    if not secret:
        raise HTTPException(
            status_code=400,
            detail="未配置 GEOSUITE_SSO_SECRET，无法签发 GEOFlow SSO ticket",
        )

    public_base = (config.get("public_base_url") or "http://localhost:18080").rstrip("/")
    # 强制演示口径：禁止 127.0.0.1，避免 419
    if "127.0.0.1" in public_base:
        public_base = public_base.replace("127.0.0.1", "localhost")

    now = int(time.time())
    payload = {
        "iss": "georank",
        "aud": "geoflow",
        "iat": now,
        "exp": now + SSO_TICKET_TTL_SECONDS,
        "nonce": uuid4().hex,
        "rank_user_id": str(user.id),
        "email": (user.email or "").strip().lower(),
        "username": (user.username or "").strip(),
        "role": str(getattr(user.role, "value", user.role) or "user"),
        "next": (next_path or "/geo_admin/dashboard").strip() or "/geo_admin/dashboard",
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    ticket = f"{body}.{sig}"
    consume_url = f"{public_base}/geo_admin/sso/consume?ticket={ticket}"
    return {
        "ticket": ticket,
        "expires_in": SSO_TICKET_TTL_SECONDS,
        "consume_url": consume_url,
        "public_base_url": public_base,
    }


def verify_callback_signature(raw_body: bytes, signature_header: str | None) -> bool:
    import hashlib
    import hmac

    secret = _suite_hmac_secret(prefer_callback=True)
    if not secret or not signature_header:
        return False
    provided = signature_header.strip()
    if provided.lower().startswith("sha256="):
        provided = provided.split("=", 1)[1].strip()
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


async def append_geoflow_event(db: AsyncSession, event: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
    from app.models.settings import Setting

    result = await db.execute(select(Setting).where(Setting.key == GEOFLOW_EVENTS_SETTING_KEY))
    setting = result.scalar_one_or_none()
    events: list[dict[str, Any]] = []
    if setting and isinstance(setting.value, list):
        events = [item for item in setting.value if isinstance(item, dict)]
    events.insert(0, event)
    events = events[:limit]
    if setting:
        setting.value = events
        setting.category = "integrations"
        setting.is_public = False
    else:
        db.add(
            Setting(
                key=GEOFLOW_EVENTS_SETTING_KEY,
                value=events,
                category="integrations",
                is_public=False,
            )
        )
    return events


async def append_handoff_log(db: AsyncSession, record: dict[str, Any], *, limit: int = 30) -> None:
    from app.models.settings import Setting

    result = await db.execute(select(Setting).where(Setting.key == GEOFLOW_HANDOFF_LOG_SETTING_KEY))
    setting = result.scalar_one_or_none()
    rows: list[dict[str, Any]] = []
    if setting and isinstance(setting.value, list):
        rows = [item for item in setting.value if isinstance(item, dict)]
    rows.insert(0, record)
    rows = rows[:limit]
    if setting:
        setting.value = rows
        setting.category = "integrations"
        setting.is_public = False
    else:
        db.add(
            Setting(
                key=GEOFLOW_HANDOFF_LOG_SETTING_KEY,
                value=rows,
                category="integrations",
                is_public=False,
            )
        )


async def list_geoflow_events(*, limit: int = 20) -> list[dict[str, Any]]:
    from app.services.runtime_settings import _load_runtime_settings

    values = await _load_runtime_settings()
    raw = values.get(GEOFLOW_EVENTS_SETTING_KEY)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)][:limit]


async def list_handoff_log(*, limit: int = 10) -> list[dict[str, Any]]:
    from app.services.runtime_settings import _load_runtime_settings

    values = await _load_runtime_settings()
    raw = values.get(GEOFLOW_HANDOFF_LOG_SETTING_KEY)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)][:limit]


async def fetch_geoflow_task_status(
    *,
    task_id: int | str,
    config: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    payload = await _geoflow_request(config, token, "GET", f"/api/v1/tasks/{task_id}")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    task = data.get("task") if isinstance(data, dict) and isinstance(data.get("task"), dict) else data
    if not isinstance(task, dict):
        raise HTTPException(status_code=502, detail="GEOFlow 任务状态响应无效")
    public_base = (config.get("public_base_url") or "").rstrip("/")
    tid = task.get("id") or task_id
    return {
        "task_id": tid,
        "name": task.get("name") or task.get("title") or "",
        "status": task.get("status") or task.get("state") or "unknown",
        "geoflow_task_url": f"{public_base}/geo_admin/tasks/{tid}/edit",
        "raw": {
            "id": tid,
            "status": task.get("status"),
            "updated_at": task.get("updated_at"),
        },
    }


async def execute_geoflow_handoff(
    *,
    task_name: str,
    brief: str,
    keywords: list[str],
    config: dict[str, Any],
    token: str,
    company_id: str | None = None,
) -> dict[str, Any]:
    titles = _titles_from_keywords(keywords, brief)
    if not titles:
        raise HTTPException(status_code=400, detail="至少需要一个标题或关键词才能创建 GEOFlow 任务")

    prompt_id, ai_model_id = await resolve_catalog_defaults(config, token)
    bound_company = (company_id or config.get("default_company_id") or "").strip() or None
    kb_content = brief
    if bound_company:
        kb_content = (
            f"---\ngeorank_company_id: {bound_company}\n---\n\n{brief}"
        )

    kb = await _geoflow_request(
        config,
        token,
        "POST",
        "/api/v1/materials/knowledge-bases",
        json_body={
            "name": f"GEORank · {task_name}"[:120],
            "description": (
                f"由 GEORank 移交；company_id={bound_company}"
                if bound_company
                else "由 GEORank 问答/拓词移交生成"
            ),
            "content": kb_content,
            "file_type": "markdown",
        },
    )
    knowledge_base_id = _unwrap_resource_id(kb)
    if knowledge_base_id is None:
        raise HTTPException(status_code=502, detail="GEOFlow 未返回知识库 ID")

    title_lib = await _geoflow_request(
        config,
        token,
        "POST",
        "/api/v1/materials/title-libraries",
        json_body={
            "name": f"GEORank · {task_name}"[:120],
            "description": "由 GEORank 自动创建的标题库",
        },
    )
    title_library_id = _unwrap_resource_id(title_lib)
    if title_library_id is None:
        raise HTTPException(status_code=502, detail="GEOFlow 未返回标题库 ID")

    for item in titles:
        await _geoflow_request(
            config,
            token,
            "POST",
            f"/api/v1/materials/title-libraries/{title_library_id}/items",
            json_body=item,
        )

    task_payload: dict[str, Any] = {
        "name": task_name[:120],
        "title_library_id": int(title_library_id),
        "prompt_id": prompt_id,
        "ai_model_id": ai_model_id,
        "status": "paused" if not config.get("auto_start") else "active",
        "category_mode": "smart",
        "draft_limit": config.get("draft_limit") or 3,
        "article_limit": config.get("article_limit") or 3,
        "knowledge_base_ids": [int(knowledge_base_id)],
        "need_review": 1 if config.get("need_review", True) else 0,
        "publish_scope": config.get("publish_scope") or "local_and_distribution",
    }
    task = await _geoflow_request(
        config,
        token,
        "POST",
        "/api/v1/tasks",
        json_body=task_payload,
    )
    task_id = _unwrap_resource_id(task)
    if task_id is None:
        raise HTTPException(status_code=502, detail="GEOFlow 未返回任务 ID")

    started = False
    if config.get("auto_start"):
        await _geoflow_request(
            config,
            token,
            "POST",
            f"/api/v1/tasks/{task_id}/start",
            json_body={"enqueue_now": True},
        )
        started = True

    public_base = (config.get("public_base_url") or config.get("base_url") or "").rstrip("/")
    if "127.0.0.1" in public_base:
        public_base = public_base.replace("127.0.0.1", "localhost")
    task_url = f"{public_base}/geo_admin/tasks/{task_id}/edit"
    return {
        "mode": "live",
        "status": "created",
        "message": "已在 GEOFlow 创建内容任务" + ("并入队生成" if started else "（暂停，可在 GEOFlow 启动）"),
        "task_id": task_id,
        "task_name": task_name,
        "company_id": bound_company,
        "knowledge_base_id": knowledge_base_id,
        "title_library_id": title_library_id,
        "keywords": keywords,
        "titles": titles,
        "started": started,
        "geoflow_admin_url": task_url,
        "geoflow_task_url": task_url,
        "suite_path": "/suite?step=review",
    }

