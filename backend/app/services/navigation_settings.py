"""前台菜单栏配置的默认值与输入规范化。"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit


NAVIGATION_MENU_SETTING_KEY = "navigation_menu"
MAX_NAVIGATION_ITEMS = 12
SUITE_NAVIGATION_ITEM: dict[str, Any] = {
    "id": "suite",
    "label": "GEO Suite",
    "url": "/suite",
    "target": "_self",
    "enabled": True,
}
KNOWLEDGE_NAVIGATION_ITEM: dict[str, Any] = {
    "id": "knowledge",
    "label": "知识库",
    "url": "/knowledge",
    "target": "_self",
    "enabled": True,
}
DISTRIBUTE_NAVIGATION_ITEM: dict[str, Any] = {
    "id": "distribute",
    "label": "分发",
    "url": "/knowledge?tab=tasks",
    "target": "_self",
    "enabled": True,
}
REMOVED_NAVIGATION_IDS = frozenset({"companies", "experts", "tutorial", "github", "solutions", "plans"})
# Soft-hidden from public nav (recoverable via admin menu editor / module switch).
HIDDEN_NAVIGATION_IDS = frozenset({"tools"})
DEFAULT_NAVIGATION_MENU = {
    "items": [
        deepcopy(SUITE_NAVIGATION_ITEM),
        {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_self", "enabled": True},
        deepcopy(KNOWLEDGE_NAVIGATION_ITEM),
        {"id": "keywords", "label": "拓词", "url": "/keywords", "target": "_self", "enabled": True},
        deepcopy(DISTRIBUTE_NAVIGATION_ITEM),
        {"id": "measure", "label": "观测", "url": "/suite?step=measure", "target": "_self", "enabled": True},
        {"id": "config", "label": "配置", "url": "/settings", "target": "_self", "enabled": True},
    ]
}


class NavigationMenuValidationError(ValueError):
    """菜单栏配置不满足公开渲染约束。"""


def get_default_navigation_menu() -> dict[str, list[dict[str, Any]]]:
    return deepcopy(DEFAULT_NAVIGATION_MENU)


def _has_suite_navigation_item(items: list[Any]) -> bool:
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip().lower()
        item_url = str(item.get("url") or "").strip().rstrip("/").lower()
        if item_id == "suite" or item_url == "/suite":
            return True
    return False


def _is_legacy_suite_knowledge_url(url: str) -> bool:
    """旧入口：Suite 知识步；现统一进前台顶栏知识页。"""
    raw = str(url or "").strip().lower()
    if not raw:
        return False
    path = raw.split("?", 1)[0].rstrip("/")
    return path == "/suite" and "step=knowledge" in raw


def _is_admin_content_engine_knowledge_url(url: str) -> bool:
    """旧前台知识库链：误进 Admin 左栏的 /admin/content-engine。"""
    raw = str(url or "").strip().lower()
    if not raw:
        return False
    path = raw.split("?", 1)[0].rstrip("/")
    if path not in {"/admin/content-engine", "/admin/content-engine.html"}:
        return False
    # 带 tab=tasks / channels 的是分发，不按知识库改写
    return "tab=tasks" not in raw and "tab=channels" not in raw


def _is_admin_content_engine_distribute_url(url: str) -> bool:
    raw = str(url or "").strip().lower()
    if not raw:
        return False
    path = raw.split("?", 1)[0].rstrip("/")
    if path not in {"/admin/content-engine", "/admin/content-engine.html"}:
        return False
    return "tab=tasks" in raw or "tab=channels" in raw


def _rewrite_frontend_pillar_navigation_urls(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把已存的前台六大能力链改写到顶栏页，并强制同窗口 _self。"""
    rewritten: list[dict[str, Any]] = []
    for item in items:
        next_item = deepcopy(item)
        item_id = str(next_item.get("id") or "").strip().lower()
        item_url = str(next_item.get("url") or "").strip()
        if item_id == "knowledge" or _is_legacy_suite_knowledge_url(item_url) or _is_admin_content_engine_knowledge_url(item_url):
            next_item["id"] = "knowledge"
            next_item["label"] = str(next_item.get("label") or "知识库").strip() or "知识库"
            next_item["url"] = KNOWLEDGE_NAVIGATION_ITEM["url"]
            next_item["target"] = "_self"
            next_item["enabled"] = next_item.get("enabled") is not False
        elif item_id == "distribute" or _is_admin_content_engine_distribute_url(item_url):
            next_item["id"] = "distribute"
            next_item["label"] = str(next_item.get("label") or "分发").strip() or "分发"
            next_item["url"] = DISTRIBUTE_NAVIGATION_ITEM["url"]
            next_item["target"] = "_self"
            next_item["enabled"] = next_item.get("enabled") is not False
        elif item_id in {"suite", "diagnostic", "keywords", "measure", "config"}:
            # 站内六大能力默认同窗口；外链保留原 target
            url_l = item_url.lower()
            if url_l.startswith("/") and not url_l.startswith("//"):
                next_item["target"] = "_self"
        rewritten.append(next_item)
    return rewritten


def _has_knowledge_navigation_item(items: list[Any]) -> bool:
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip().lower()
        item_url = str(item.get("url") or "").strip().lower()
        if item_id == "knowledge":
            return True
        if "step=knowledge" in item_url:
            return True
        path = item_url.split("?", 1)[0].rstrip("/")
        if path in {"/knowledge", "/knowledge.html"}:
            return True
        if "content-engine" in item_url and "tab=tasks" not in item_url and "tab=channels" not in item_url:
            return True
        if "/geo_admin/knowledge-bases" in item_url or item_url.endswith("/knowledge-bases"):
            return True
    return False


def _insert_knowledge_navigation_item(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insert the six-pillar knowledge entry after diagnostic (or after suite)."""
    if _has_knowledge_navigation_item(items):
        return items
    knowledge = deepcopy(KNOWLEDGE_NAVIGATION_ITEM)
    insert_at = 1
    for index, item in enumerate(items):
        item_id = str(item.get("id") or "").strip().lower()
        item_url = str(item.get("url") or "").strip().rstrip("/").lower()
        if item_id == "diagnostic" or item_url == "/diagnostic":
            insert_at = index + 1
            break
        if item_id == "suite" or item_url == "/suite":
            insert_at = index + 1
    merged = [*items[:insert_at], knowledge, *items[insert_at:]]
    if len(merged) > MAX_NAVIGATION_ITEMS:
        # Prefer keeping suite + knowledge; drop trailing items first.
        merged = merged[:MAX_NAVIGATION_ITEMS]
    return merged


def _has_distribute_navigation_item(items: list[Any]) -> bool:
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip().lower()
        item_url = str(item.get("url") or "").strip().lower()
        if item_id == "distribute":
            return True
        if "tab=tasks" in item_url or "tab=channels" in item_url:
            return True
    return False


def _insert_distribute_navigation_item(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insert distribute entry after keywords (or after knowledge)."""
    if _has_distribute_navigation_item(items):
        return items
    distribute = deepcopy(DISTRIBUTE_NAVIGATION_ITEM)
    insert_at = len(items)
    for index, item in enumerate(items):
        item_id = str(item.get("id") or "").strip().lower()
        item_url = str(item.get("url") or "").strip().lower()
        if item_id == "keywords" or item_url.endswith("/keywords"):
            insert_at = index + 1
            break
        if (
            item_id == "knowledge"
            or "step=knowledge" in item_url
            or item_url.split("?", 1)[0].rstrip("/") in {"/knowledge", "/knowledge.html"}
            or ("content-engine" in item_url and "tab=tasks" not in item_url and "tab=channels" not in item_url)
        ):
            insert_at = index + 1
    merged = [*items[:insert_at], distribute, *items[insert_at:]]
    if len(merged) > MAX_NAVIGATION_ITEMS:
        merged = merged[:MAX_NAVIGATION_ITEMS]
    return merged


def ensure_suite_in_navigation_menu(payload: Any) -> dict[str, list[dict[str, Any]]]:
    """Ensure GEO Suite + knowledge + distribute appear; strip deleted public entries."""
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list) or not payload["items"]:
        return get_default_navigation_menu()

    items = [
        deepcopy(item)
        for item in payload["items"]
        if isinstance(item, dict)
        and str(item.get("id") or "").strip().lower() not in REMOVED_NAVIGATION_IDS
        and str(item.get("id") or "").strip().lower() not in HIDDEN_NAVIGATION_IDS
        and not _is_removed_navigation_url(item.get("url"))
        and not _is_hidden_navigation_url(item.get("url"))
    ]
    if not items:
        return get_default_navigation_menu()
    if not _has_suite_navigation_item(items):
        items = [deepcopy(SUITE_NAVIGATION_ITEM), *items]
    items = _rewrite_frontend_pillar_navigation_urls(items)
    items = _insert_knowledge_navigation_item(items)
    items = _insert_distribute_navigation_item(items)
    if len(items) > MAX_NAVIGATION_ITEMS:
        items = [items[0], *items[1:MAX_NAVIGATION_ITEMS]]
    return {"items": items}


def _is_removed_navigation_url(value: Any) -> bool:
    url = str(value or "").strip().rstrip("/").lower()
    if not url:
        return False
    if url in {"/companies", "/company", "/submit-company", "/company-submit", "/experts", "/tutorial", "/solutions", "/plans", "/qa"}:
        return True
    if url.startswith("/companies/") or url.startswith("/company/") or url.startswith("/c/"):
        return True
    if url.startswith("/experts/") or url.startswith("/tutorial/"):
        return True
    if url.startswith("/solutions/") or url.startswith("/plans/") or url.startswith("/qa/"):
        return True
    return "github.com/yaojingang/georank" in url


def _is_hidden_navigation_url(value: Any) -> bool:
    """Soft-hide tools (and aliases) from public nav until re-enabled in admin."""
    url = str(value or "").strip().rstrip("/").lower()
    if not url:
        return False
    path = url.split("?", 1)[0]
    return path == "/tools" or path.startswith("/tools/")


def _normalize_navigation_url(value: Any, index: int) -> str:
    url = str(value or "").strip()
    if not url:
        raise NavigationMenuValidationError(f"第 {index} 个菜单项缺少 URL")
    if len(url) > 2048:
        raise NavigationMenuValidationError(f"第 {index} 个菜单项 URL 不能超过 2048 个字符")
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise NavigationMenuValidationError(f"第 {index} 个菜单项 URL 包含不可见字符")
    if url.startswith("/") and not url.startswith("//"):
        return url
    if url.startswith("#") and len(url) > 1:
        return url
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise NavigationMenuValidationError(f"第 {index} 个菜单项 URL 无效") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise NavigationMenuValidationError(
            f"第 {index} 个菜单项 URL 仅支持站内路径、锚点或 HTTP/HTTPS 地址"
        )
    return url


def normalize_navigation_menu_payload(payload: Any) -> dict[str, list[dict[str, Any]]]:
    if payload is None:
        return get_default_navigation_menu()
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise NavigationMenuValidationError("菜单栏配置必须包含 items 数组")

    raw_items = payload["items"]
    if not raw_items:
        raise NavigationMenuValidationError("菜单栏至少需要保留一个菜单项")
    if len(raw_items) > MAX_NAVIGATION_ITEMS:
        raise NavigationMenuValidationError(f"菜单栏最多支持 {MAX_NAVIGATION_ITEMS} 个菜单项")

    normalized_items: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for position, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            raise NavigationMenuValidationError(f"第 {position} 个菜单项格式无效")
        label = str(raw_item.get("label") or "").strip()
        if not label:
            raise NavigationMenuValidationError(f"第 {position} 个菜单项缺少文案")
        if len(label) > 40:
            raise NavigationMenuValidationError(f"第 {position} 个菜单项文案不能超过 40 个字符")

        raw_id = str(raw_item.get("id") or f"menu-{position}").strip()
        item_id = raw_id if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", raw_id) else f"menu-{position}"
        if item_id in used_ids:
            item_id = f"{item_id}-{position}"
        used_ids.add(item_id)

        url = _normalize_navigation_url(raw_item.get("url"), position)
        # 站内路径默认同窗口；外链默认新窗口（可显式传 _self）
        is_internal = url.startswith("/") and not url.startswith("//")
        raw_target = str(raw_item.get("target") or ("_self" if is_internal else "_blank")).strip().lower()
        target = "_self" if raw_target in {"_self", "same_tab"} else "_blank"
        if is_internal and raw_item.get("target") is None:
            target = "_self"
        normalized_items.append(
            {
                "id": item_id,
                "label": label,
                "url": url,
                "target": target,
                "enabled": raw_item.get("enabled") is not False,
            }
        )

    if not any(item["enabled"] for item in normalized_items):
        raise NavigationMenuValidationError("菜单栏至少需要保留一个菜单项显示")
    return {"items": normalized_items}
