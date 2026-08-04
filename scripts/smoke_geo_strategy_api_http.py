#!/usr/bin/env python3
"""HTTP 层策略闸门冒烟：登录 → seed → 六元组 → 诊断/baseline → 审批。

跳过白号采样；完整闭环见 smoke_geo_strategy_e2e.py（服务层 + fixture 样本）。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8010"
EDITOR = ("smoke-editor@georank.local", "SmokeTest!234")
REVIEWER = ("smoke-reviewer@georank.local", "SmokeTest!234")


def req(method: str, path: str, token: str | None = None, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(API.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc


def login(account: str, password: str) -> str:
    out = req("POST", "/api/auth/login", body={"account": account, "password": password})
    tok = out.get("access_token")
    if not tok:
        raise RuntimeError(f"login failed for {account}: {out}")
    return tok


def main() -> int:
    print(">> HTTP smoke", API)
    try:
        ed = login(*EDITOR)
        rv = login(*REVIEWER)
    except Exception as exc:
        print("LOGIN_FAIL", exc)
        print("提示: 先跑 python scripts/smoke_geo_strategy_e2e.py 写入 smoke 用户")
        return 2

    me = req("GET", "/api/content-engine/geo/me", ed)
    print("editor geo_role=", me.get("geo_role"), "roles=", me.get("effective_roles"))

    seed = req(
        "POST",
        "/api/geo-strategies/seed",
        ed,
        {
            "platform": "doubao",
            "question_class": "HTTP冒烟·第一现场是什么",
            "gap_note": "HTTP 闸门冒烟缺口说明",
            "title": "HTTP冒烟策略草稿",
        },
    )
    sid = seed["id"]
    print("seeded", sid, "status", seed.get("status"))

    patched = req(
        "PATCH",
        f"/api/geo-strategies/{sid}",
        ed,
        {
            "content_orientation": "深文+FAQ",
            "query_variants": [
                "第一现场是什么栏目",
                "第一现场报道什么",
                "哪里看第一现场",
            ],
            "channel_matrix": {"site_required": True, "media_types": ["wechat"]},
            "success_signal": {"mode": "mention_top10", "top_n": 10},
            "knowledge_document_ids": ["00000000-0000-0000-0000-000000000001"],
            "knowledge_tag_pack": {
                "site_id": "diyixianchang",
                "theme": "栏目认知",
                "task_bajua": "栏目认知",
            },
        },
    )
    print("patched queries", len(patched.get("query_variants") or []))

    # 无 geo_run / 诊断时 baseline 应失败（闸门正确）
    try:
        req("POST", f"/api/geo-strategies/{sid}/register-baseline", ed)
        print("UNEXPECTED baseline ok without geo_run")
        return 1
    except RuntimeError as exc:
        if "400" not in str(exc):
            print("UNEXPECTED", exc)
            return 1
        print("baseline gate ok (needs geo_run):", str(exc)[:120])

    # 无诊断/baseline 时 submit 可过六元组校验，但 approve 必须挡
    submitted = req("POST", f"/api/geo-strategies/{sid}/submit", ed)
    print("submitted", submitted.get("status"))
    try:
        req("POST", f"/api/geo-strategies/{sid}/approve", rv)
        print("UNEXPECTED approve without diag/baseline")
        return 1
    except RuntimeError as exc:
        if "400" not in str(exc) and "诊断" not in str(exc) and "baseline" not in str(exc):
            # 仍算闸门生效只要是 400
            if "HTTP 400" not in str(exc):
                print("UNEXPECTED", exc)
                return 1
        print("approve gate ok:", str(exc)[:160])

    items = req("GET", "/api/geo-strategies/?limit=3", ed)
    print("list count", len(items.get("items") or []))
    cl = req("GET", f"/api/geo-strategies/{sid}/handoff-checklist", ed)
    print(
        "checklist ready_for_approve",
        cl.get("ready_for_approve"),
        "obs_deferred",
        cl.get("obs_white_hat_deferred"),
    )
    print("HTTP_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
