#!/usr/bin/env python3
"""策略流程冒烟（可选连本机 API）。默认只跑离线 unittest。

用法:
  python scripts/smoke_geo_strategy_flow.py
  python scripts/smoke_geo_strategy_flow.py --api http://127.0.0.1:8010 --token <JWT>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def run_offline_tests() -> int:
    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "tests.test_geo_strategy_flow",
        "tests.test_geo_strategy_validate",
        "tests.test_content_engine",
        "tests.test_navigation_settings",
        "-v",
    ]
    print(">> offline:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(BACKEND))


def run_service_e2e() -> int:
    """服务层全流程（fixture after 样本；不跑白号浏览器）。"""
    script = ROOT / "scripts" / "smoke_geo_strategy_e2e.py"
    if not script.is_file():
        print(">> skip e2e: missing", script)
        return 0
    print(">> service e2e:", script)
    return subprocess.call([sys.executable, str(script)], cwd=str(ROOT))


def api_json(base: str, path: str, token: str | None, method: str = "GET", body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_api_smoke(base: str, token: str) -> int:
    print(">> API smoke against", base)
    print("   NOTE: 跳过白号观测采样；baseline/after 仅测挂接与闸门")
    try:
        me = api_json(base, "/api/content-engine/geo/me", token)
        print("geo/me roles:", me.get("effective_roles"), "geo_role=", me.get("geo_role"))
        items = api_json(base, "/api/geo-strategies/?limit=5", token)
        print("strategies count:", len(items.get("items") or []))
        print("OK api reachable")
        return 0
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read()[:300])
        return 1
    except Exception as exc:
        print("API smoke skipped/failed:", exc)
        return 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="", help="如 http://127.0.0.1:8010")
    p.add_argument("--token", default="", help="JWT")
    p.add_argument("--e2e", action="store_true", help="再跑服务层全流程 E2E（需本机 Postgres）")
    p.add_argument("--skip-unit", action="store_true", help="跳过 unittest")
    args = p.parse_args()
    code = 0 if args.skip_unit else run_offline_tests()
    if args.e2e:
        code = code or run_service_e2e()
    if args.api and args.token:
        api_code = run_api_smoke(args.api, args.token)
        return code or api_code
    if args.api and not args.token:
        http_script = ROOT / "scripts" / "smoke_geo_strategy_api_http.py"
        if http_script.is_file():
            print(">> HTTP gate smoke (smoke users):", args.api)
            # 脚本内写死默认 8010；用环境变量不够时直接调用
            return code or subprocess.call([sys.executable, str(http_script)], cwd=str(ROOT))
    print(">> no --api/--token: skip live API smoke（可用 --e2e）")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
