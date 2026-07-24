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
REMOVED_NAVIGATION_IDS = frozenset({"companies", "experts", "tutorial", "github"})
DEFAULT_NAVIGATION_MENU = {
    "items": [
        deepcopy(SUITE_NAVIGATION_ITEM),
        {"id": "diagnostic", "label": "诊断", "url": "/diagnostic", "target": "_blank", "enabled": True},
        {"id": "solutions", "label": "问答", "url": "/solutions", "target": "_blank", "enabled": True},
        {"id": "plans", "label": "方案", "url": "/plans", "target": "_blank", "enabled": True},
        {"id": "keywords", "label": "拓词", "url": "/keywords", "target": "_blank", "enabled": True},
        {"id": "tools", "label": "工具", "url": "/tools", "target": "_blank", "enabled": True},
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


def ensure_suite_in_navigation_menu(payload: Any) -> dict[str, list[dict[str, Any]]]:
    """Ensure GEO Suite appears; strip deleted public entries (companies/experts/tutorial/github)."""
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list) or not payload["items"]:
        return get_default_navigation_menu()

    items = [
        deepcopy(item)
        for item in payload["items"]
        if isinstance(item, dict)
        and str(item.get("id") or "").strip().lower() not in REMOVED_NAVIGATION_IDS
        and not _is_removed_navigation_url(item.get("url"))
    ]
    if not items:
        return get_default_navigation_menu()
    if _has_suite_navigation_item(items):
        return {"items": items}

    merged = [deepcopy(SUITE_NAVIGATION_ITEM), *items]
    if len(merged) > MAX_NAVIGATION_ITEMS:
        merged = [merged[0], *merged[1:MAX_NAVIGATION_ITEMS]]
    return {"items": merged}


def _is_removed_navigation_url(value: Any) -> bool:
    url = str(value or "").strip().rstrip("/").lower()
    if not url:
        return False
    if url in {"/companies", "/company", "/submit-company", "/company-submit", "/experts", "/tutorial"}:
        return True
    if url.startswith("/companies/") or url.startswith("/company/") or url.startswith("/c/"):
        return True
    if url.startswith("/experts/") or url.startswith("/tutorial/"):
        return True
    return "github.com/yaojingang/georank" in url


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

        target_value = str(raw_item.get("target") or "_blank").strip().lower()
        target = "_self" if target_value in {"_self", "same_tab"} else "_blank"
        normalized_items.append(
            {
                "id": item_id,
                "label": label,
                "url": _normalize_navigation_url(raw_item.get("url"), position),
                "target": target,
                "enabled": raw_item.get("enabled") is not False,
            }
        )

    if not any(item["enabled"] for item in normalized_items):
        raise NavigationMenuValidationError("菜单栏至少需要保留一个菜单项显示")
    return {"items": normalized_items}
