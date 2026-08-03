"""Lightweight adapters — URLs only; interaction lives in run_probe.py."""
from __future__ import annotations

from platforms import PLATFORM_URLS

__all__ = ["PLATFORM_URLS", "adapter_for"]


def adapter_for(platform: str) -> dict:
    key = (platform or "").strip().lower()
    return {
        "platform": key,
        "start_url": PLATFORM_URLS.get(key),
        "label": {"doubao": "豆包", "yuanbao": "元宝", "deepseek": "DeepSeek"}.get(key, key),
    }
