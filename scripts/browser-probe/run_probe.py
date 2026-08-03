"""半自动浏览器点名采样（豆包 / 元宝 / DeepSeek）。

约定账号网页端抽样；结果回传本仓 real-obs API。
登录态存本地 storage，勿提交 Git。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = Path.home() / ".georank-browser-probe"
URL_RE = re.compile(r"https?://[^\s\)\]\>\"'<>]+", re.I)

PLATFORM_URLS = {
    "doubao": "https://www.doubao.com/chat/",
    "yuanbao": "https://yuanbao.tencent.com/",
    "deepseek": "https://chat.deepseek.com/",
}


def _http_json(method: str, url: str, body: dict | None = None, timeout: int = 60) -> dict:
    data = None
    headers = {"Accept": "application/json", "User-Agent": "georank-browser-probe/1.0"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def extract_urls(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url in URL_RE.findall(text or ""):
        clean = url.rstrip(".,;）)」』\"'")
        if clean in seen:
            continue
        seen.add(clean)
        host = clean.split("/")[2].lower() if "://" in clean else ""
        if host.startswith("www."):
            host = host[4:]
        out.append({"url": clean, "domain": host, "title": None, "source": "body_extract"})
    return out


def fetch_job(api_base: str, run_id: str, snapshot_id: str) -> dict[str, Any]:
    url = urljoin(api_base.rstrip("/") + "/", f"api/geo-runs/{run_id}/real-obs/snapshots/{snapshot_id}")
    payload = _http_json("GET", url)
    job = payload.get("job") or {}
    if not job.get("units"):
        raise SystemExit("快照任务无采样单元")
    _http_json("POST", urljoin(api_base.rstrip("/") + "/", f"api/geo-runs/{run_id}/real-obs/snapshots/{snapshot_id}/start"))
    return job


def post_sample(api_base: str, run_id: str, snapshot_id: str, sample: dict[str, Any]) -> dict:
    url = urljoin(
        api_base.rstrip("/") + "/",
        f"api/geo-runs/{run_id}/real-obs/snapshots/{snapshot_id}/samples",
    )
    return _http_json("POST", url, sample)


def wait_enter(msg: str) -> None:
    print(msg)
    try:
        input()
    except EOFError:
        pass


def run_manual_unit(unit: dict[str, Any], entity: str) -> dict[str, Any]:
    platform = unit["platform"]
    qtext = unit["question_text"]
    print("\n" + "=" * 60)
    print(f"平台: {platform}  问法: {unit['question_id']}")
    print(f"建议打开: {PLATFORM_URLS.get(platform, '')}")
    print(f"请粘贴/输入问题到网页端：\n{qtext}")
    print(f"（本品关键词提示: {entity}）")
    wait_enter("登录/验证码处理完毕并看到完整答案后，按 Enter，然后粘贴答案全文（空行结束）…")
    print("答案全文（空行结束）：")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    answer = "\n".join(lines).strip()
    if not answer:
        return {
            "question_id": unit["question_id"],
            "platform": platform,
            "attempt": unit.get("attempt") or 1,
            "ok": False,
            "error_message": "空答案",
            "answer_text": None,
            "citations": [],
            "raw_meta": {"mode": "manual-paste"},
        }
    cites = extract_urls(answer)
    return {
        "question_id": unit["question_id"],
        "platform": platform,
        "attempt": unit.get("attempt") or 1,
        "ok": True,
        "answer_text": answer,
        "citations": cites,
        "raw_meta": {"mode": "manual-paste"},
    }


def run_playwright_unit(
    unit: dict[str, Any],
    *,
    state_dir: Path,
    headed: bool,
    entity: str,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("需要 playwright：pip install playwright && playwright install chromium") from exc

    platform = unit["platform"]
    url = PLATFORM_URLS.get(platform)
    if not url:
        return {
            "question_id": unit["question_id"],
            "platform": platform,
            "attempt": 1,
            "ok": False,
            "error_message": f"未知平台 {platform}",
            "citations": [],
        }

    state_dir.mkdir(parents=True, exist_ok=True)
    storage = state_dir / f"{platform}.json"
    qtext = unit["question_text"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context_kwargs: dict[str, Any] = {"viewport": {"width": 1280, "height": 900}}
        if storage.exists():
            context_kwargs["storage_state"] = str(storage)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        print(f"\n[{platform}] 已打开 {url}")
        print(f"问法: {qtext}")
        print(f"本品提示: {entity}")
        wait_enter(
            "请在浏览器中完成登录/验证码，将问题发给模型并等待完整回答；"
            "完成后回到终端按 Enter（将保存登录态并抓取页面可见文本）…"
        )
        try:
            context.storage_state(path=str(storage))
        except Exception as exc:  # noqa: BLE001
            print(f"警告: 保存 storage 失败: {exc}")

        body_text = ""
        try:
            body_text = page.inner_text("body", timeout=15000)
        except Exception:  # noqa: BLE001
            body_text = page.content()

        # 取页面后段作为答案近似（半自动，人工可再改标）
        answer = body_text[-8000:].strip() if body_text else ""
        hrefs: list[dict[str, Any]] = []
        try:
            for a in page.query_selector_all("a[href^='http']"):
                href = a.get_attribute("href") or ""
                title = (a.inner_text() or "").strip()[:120] or None
                if href:
                    host = href.split("/")[2].lower() if "://" in href else ""
                    if host.startswith("www."):
                        host = host[4:]
                    hrefs.append(
                        {"url": href, "domain": host, "title": title, "source": "structured"}
                    )
        except Exception:  # noqa: BLE001
            pass
        cites = hrefs[:40] + [c for c in extract_urls(answer) if c["url"] not in {h["url"] for h in hrefs}]
        browser.close()

    if not answer:
        return {
            "question_id": unit["question_id"],
            "platform": platform,
            "attempt": unit.get("attempt") or 1,
            "ok": False,
            "error_message": "未能抽取页面文本",
            "citations": cites,
            "raw_meta": {"mode": "playwright"},
        }
    return {
        "question_id": unit["question_id"],
        "platform": platform,
        "attempt": unit.get("attempt") or 1,
        "ok": True,
        "answer_text": answer,
        "citations": cites,
        "raw_meta": {"mode": "playwright", "storage": str(storage)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GEOrank 半自动浏览器点名采样")
    parser.add_argument("--api", default="http://127.0.0.1:8010", help="API 根，如 http://127.0.0.1:8010")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--mode", choices=("playwright", "manual"), default="playwright")
    parser.add_argument("--platform", action="append", help="只跑指定平台，可重复；默认任务内全部")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument("--headed", action="store_true", default=True)
    parser.add_argument("--headless", action="store_true", help="无头（不推荐，验证码难过）")
    parser.add_argument("--dry-job", action="store_true", help="只打印任务 JSON，不采样")
    args = parser.parse_args(argv)

    headed = not args.headless
    job = fetch_job(args.api, args.run_id, args.snapshot_id)
    if args.dry_job:
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    platforms = set(args.platform or [])
    units = [
        u
        for u in job.get("units") or []
        if not platforms or u.get("platform") in platforms
    ]
    entity = job.get("entity") or ""
    print(job.get("method_note") or "")
    print(f"任务单元数: {len(units)}  snapshot={args.snapshot_id}")

    ok_n = 0
    fail_n = 0
    for unit in units:
        try:
            if args.mode == "manual":
                sample = run_manual_unit(unit, entity)
            else:
                sample = run_playwright_unit(
                    unit,
                    state_dir=Path(args.state_dir),
                    headed=headed,
                    entity=entity,
                )
            resp = post_sample(args.api, args.run_id, args.snapshot_id, sample)
            flag = "OK" if sample.get("ok") else "FAIL"
            adopted = (resp.get("sample") or {}).get("strong_adopted")
            print(f"[{flag}] {unit['platform']} {unit['question_id']} strong_adopted={adopted}")
            if sample.get("ok"):
                ok_n += 1
            else:
                fail_n += 1
        except Exception as exc:  # noqa: BLE001
            fail_n += 1
            print(f"[ERR] {unit.get('platform')} {unit.get('question_id')}: {exc}")
            try:
                post_sample(
                    args.api,
                    args.run_id,
                    args.snapshot_id,
                    {
                        "question_id": unit["question_id"],
                        "platform": unit["platform"],
                        "attempt": unit.get("attempt") or 1,
                        "ok": False,
                        "error_message": str(exc)[:500],
                        "citations": [],
                    },
                )
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.3)

    print(f"完成: ok={ok_n} fail={fail_n}")
    return 0 if fail_n == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
