"""加载 GEO 观测/检查共用演示剧本（无白号采样）."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.geo_run import DEFAULT_OBSERVE_SCRIPT

# backend/app/services -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CANDIDATES = [
    _REPO_ROOT / "dist" / "pilot-demo",
    _REPO_ROOT / "docs" / "pilot-demo",
]


@lru_cache(maxsize=8)
def load_observe_script(key: str | None = None) -> dict[str, Any]:
    script_key = (key or DEFAULT_OBSERVE_SCRIPT).strip() or DEFAULT_OBSERVE_SCRIPT
    filename = f"{script_key}.json"
    for folder in _CANDIDATES:
        path = folder / filename
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"observe script not found: {filename}")


def script_summary(script: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": script.get("key"),
        "version": script.get("version"),
        "disclaimer": script.get("disclaimer"),
        "entity": script.get("entity"),
        "competitor": script.get("competitor"),
        "platforms": script.get("platforms") or [],
        "layers": script.get("layers") or [],
        "question_count": len(script.get("questions") or []),
        "summary": script.get("summary") or {},
        "scoring_rubric": script.get("scoring_rubric") or {},
    }


def load_ai_focus(key: str | None = None) -> dict[str, Any]:
    """兼容旧调用：优先同步读文件；新路径请用 get_ai_focus_config()。"""
    return load_observe_script(key or "geo-ai-focus-dji")


async def get_ai_focus_config() -> dict[str, Any]:
    """目标 AI 侧重：后台 keyword_expansion settings（与拓词同源）。"""
    from app.services.runtime_settings import get_keyword_expansion_config

    config = await get_keyword_expansion_config()
    items = []
    for row in config.get("platforms") or []:
        items.append(
            {
                "platform": row["platform"],
                "generation_focus": row.get("generation_focus") or "",
                "avoid": list(row.get("avoid") or []),
                "source_prefs": [],
                "title_patterns": [],
            }
        )
    return {
        "key": "keyword_ai_focus",
        "version": "settings",
        "disclaimer": config.get("disclaimer")
        or "目标 AI 侧重来自后台配置 · 非平台实测",
        "entity": "",
        "platforms": [row["platform"] for row in items],
        "items": items,
    }


def ai_focus_for_platforms(
    script: dict[str, Any],
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    items = list(script.get("items") or [])
    if not platforms:
        return items
    wanted = {str(p).strip() for p in platforms if str(p).strip()}
    return [row for row in items if str(row.get("platform") or "") in wanted]


def build_generation_focus_block(
    script: dict[str, Any],
    platforms: list[str] | None = None,
) -> str:
    rows = ai_focus_for_platforms(script, platforms)
    if not rows:
        return ""
    lines = ["【目标 AI 生成侧重 · 演示策略表 · 非实测】"]
    for row in rows:
        name = row.get("platform") or "平台"
        focus = (row.get("generation_focus") or "").strip()
        avoid = "、".join(row.get("avoid") or [])
        lines.append(f"- {name}：{focus}")
        if avoid:
            lines.append(f"  避免：{avoid}")
    return "\n".join(lines)
