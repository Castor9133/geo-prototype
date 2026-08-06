#!/usr/bin/env python3
"""GEOrank 本地页面截图脚本

使用 Playwright 对本地运行的 GEO 工作台页面进行截图。

用法：
    # 确保本地服务已启动（端口 3009）
    # 然后运行：
    backend\.venv\Scripts\python.exe scripts\take_screenshots.py
    
    # 如果 Playwright 浏览器未安装，先运行：
    backend\.venv\Scripts\python.exe -m playwright install chromium
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "temp_screenshots"
BASE_URL = "http://127.0.0.1:3009"

PAGES = [
    ("/suite", "suite_page.png"),
    ("/", "home_page.png"),
    ("/strategies", "strategies_page.png"),
    ("/knowledge", "knowledge_page.png"),
    ("/diagnostic", "diagnostic_page.png"),
    ("/keywords", "keywords_page.png"),
    ("/distribute", "distribute_page.png"),
    ("/observe", "observe_page.png"),
]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("错误: 需要安装 playwright")
        print("请运行: backend\\.venv\\Scripts\\python.exe -m pip install playwright")
        print("然后: backend\\.venv\\Scripts\\python.exe -m playwright install chromium")
        return 1

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"截图将保存到: {SCREENSHOT_DIR}")
    print(f"目标地址: {BASE_URL}")
    print()

    with sync_playwright() as p:
        print("启动浏览器...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        page = context.new_page()

        success_count = 0
        fail_count = 0

        for path, filename in PAGES:
            url = f"{BASE_URL}{path}"
            output_path = SCREENSHOT_DIR / filename
            
            try:
                print(f"正在访问: {url}")
                page.goto(url, wait_until="networkidle", timeout=15000)
                # 额外等待动态内容加载
                time.sleep(1.5)
                
                # 截取整页
                page.screenshot(path=str(output_path), full_page=True)
                print(f"  ✓ 已保存: {filename}")
                success_count += 1
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                fail_count += 1

        browser.close()

    print()
    print(f"完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    print(f"截图目录: {SCREENSHOT_DIR}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
