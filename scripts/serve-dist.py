"""Local static + demo API server for GEORank (no Docker required).

Serves dist/ with nginx-like HTML fallbacks, and mocks the public APIs
needed for the company directory homepage.
"""
from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

ROOT = Path(r"C:\Cursor local\GEORank\dist")
os.chdir(ROOT)

DEMO_COMPANIES = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "path_key": "georankhub",
        "name": "GEORankHub",
        "url": "https://www.georankhub.com/",
        "logo_url": None,
        "short_description": "GEOrank 官方演示与 GEO 公益研究平台，覆盖网站诊断、问答、方案与拓词。",
        "category": "GEO 平台",
        "tags": ["GEO", "开源", "诊断"],
        "geo_score": 92.5,
        "is_geo_certified": True,
        "tech_level": "SaaS",
        "funding_stage": "开源",
        "headquarters": "全球",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 128,
        "view_count": 5600,
        "description": "面向生成式引擎优化（GEO）的开源工作台与研究平台。",
        "employee_count": "开源社区",
        "founded_date": "2025",
        "geo_details": {"summary": "本地演示数据，后端 API 未启动时使用。"},
        "tech_stack": ["FastAPI", "Next.js", "PostgreSQL"],
        "team_members": [],
        "pipeline_error": None,
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "path_key": "brandorbit",
        "name": "BrandOrbit",
        "url": "https://brandorbit.test",
        "logo_url": None,
        "short_description": "面向市场与增长团队的 AI 搜索可见性管理平台（演示样本）。",
        "category": "营销科技",
        "tags": ["AI 搜索", "可见性", "内容"],
        "geo_score": 86.0,
        "is_geo_certified": False,
        "tech_level": "SaaS",
        "funding_stage": "种子轮",
        "headquarters": "上海",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 64,
        "view_count": 2100,
        "description": "帮助品牌更容易被 AI 搜索理解、引用和推荐。",
        "employee_count": "11-50",
        "founded_date": "2024",
        "geo_details": None,
        "tech_stack": ["Python", "React"],
        "team_members": [],
        "pipeline_error": None,
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "path_key": "signalcraft",
        "name": "SignalCraft",
        "url": "https://signalcraft.test",
        "logo_url": None,
        "short_description": "结构化内容与 Schema 自动化工具（演示样本）。",
        "category": "内容工具",
        "tags": ["JSON-LD", "llms.txt", "Schema"],
        "geo_score": 81.2,
        "is_geo_certified": True,
        "tech_level": "工具",
        "funding_stage": "天使轮",
        "headquarters": "深圳",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 41,
        "view_count": 980,
        "description": "把官网内容快速整理成 AI 可读的结构化资产。",
        "employee_count": "1-10",
        "founded_date": "2023",
        "geo_details": None,
        "tech_stack": ["TypeScript"],
        "team_members": [],
        "pipeline_error": None,
    },
    {
        "id": "44444444-4444-4444-8444-444444444444",
        "path_key": "answerlane",
        "name": "AnswerLane",
        "url": "https://answerlane.test",
        "logo_url": None,
        "short_description": "品牌问答与 AI 引用监测（演示样本）。",
        "category": "监测分析",
        "tags": ["问答", "引用监测", "GEO"],
        "geo_score": 78.4,
        "is_geo_certified": False,
        "tech_level": "SaaS",
        "funding_stage": "A 轮",
        "headquarters": "北京",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 55,
        "view_count": 1450,
        "description": "追踪品牌在 AI 答案中的出现与引用质量。",
        "employee_count": "51-200",
        "founded_date": "2022",
        "geo_details": None,
        "tech_stack": ["Go", "ClickHouse"],
        "team_members": [],
        "pipeline_error": None,
    },
    {
        "id": "55555555-5555-4555-8555-555555555555",
        "path_key": "citeforge",
        "name": "CiteForge",
        "url": "https://citeforge.test",
        "logo_url": None,
        "short_description": "面向 SEO/GEO 团队的内容事实库与引用工作流（演示样本）。",
        "category": "内容运营",
        "tags": ["知识库", "事实库", "工作流"],
        "geo_score": 74.0,
        "is_geo_certified": False,
        "tech_level": "平台",
        "funding_stage": "未融资",
        "headquarters": "杭州",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 22,
        "view_count": 620,
        "description": "把分散资料沉淀成可复用、可引用的品牌知识资产。",
        "employee_count": "1-10",
        "founded_date": "2025",
        "geo_details": None,
        "tech_stack": ["Next.js"],
        "team_members": [],
        "pipeline_error": None,
    },
    {
        "id": "66666666-6666-4666-8666-666666666666",
        "path_key": "promptatlas",
        "name": "PromptAtlas",
        "url": "https://promptatlas.test",
        "logo_url": None,
        "short_description": "场景词与问题词拓展助手（演示样本）。",
        "category": "拓词工具",
        "tags": ["拓词", "意图词", "选题"],
        "geo_score": 71.5,
        "is_geo_certified": False,
        "tech_level": "工具",
        "funding_stage": "开源",
        "headquarters": "远程",
        "pipeline_status": "completed",
        "publish_status": "published",
        "upvotes": 33,
        "view_count": 870,
        "description": "从业务词扩展问题词、场景词与推荐型关键词。",
        "employee_count": "开源社区",
        "founded_date": "2024",
        "geo_details": None,
        "tech_stack": ["Python"],
        "team_members": [],
        "pipeline_error": None,
    },
]

DEMO_TUTORIALS = [
    {
        "id": str(uuid4()),
        "title": "GEO 入门：什么是生成式引擎优化",
        "slug": "geo-intro",
        "path_key": "geo-intro",
        "content_type": "tutorial",
        "status": "published",
        "summary": "从传统 SEO 到 AI 答案引用，理解 GEO 的核心目标与指标。",
        "tags": ["入门", "GEO"],
        "updated_at": "2026-07-01T00:00:00Z",
    },
    {
        "id": str(uuid4()),
        "title": "如何为官网补齐 JSON-LD 与 llms.txt",
        "slug": "jsonld-llms-txt",
        "path_key": "jsonld-llms-txt",
        "content_type": "tutorial",
        "status": "published",
        "summary": "用结构化标记提升 AI 对品牌实体与产品能力的理解。",
        "tags": ["结构化", "Schema"],
        "updated_at": "2026-07-05T00:00:00Z",
    },
    {
        "id": str(uuid4()),
        "title": "30/60/90 天 GEO 行动方案模板",
        "slug": "geo-action-plan",
        "path_key": "geo-action-plan",
        "content_type": "tutorial",
        "status": "published",
        "summary": "把一次诊断结果拆成可执行的阶段性优化计划。",
        "tags": ["方案", "实战"],
        "updated_at": "2026-07-10T00:00:00Z",
    },
]

# Exact path -> static file under dist/
ROUTE_MAP = {
    "/": "index.html",
    "/companies": "index.html",
    "/index": "index.html",
    "/diagnostic": "diagnostic.html",
    "/solutions": "solutions.html",
    "/plans": "plans.html",
    "/keywords": "keywords.html",
    "/tools": "tools.html",
    "/experts": "experts.html",
    "/tutorial": "tutorial.html",
    "/profile": "profile.html",
    "/login": "login.html",
    "/register": "register.html",
    "/company": "company.html",
    "/company-submit": "company-submit.html",
    "/submit-company": "company-submit.html",
}


def brief(company: dict) -> dict:
    keys = [
        "id", "path_key", "name", "url", "logo_url", "short_description",
        "category", "tags", "geo_score", "is_geo_certified", "tech_level",
        "funding_stage", "headquarters", "pipeline_status", "publish_status",
        "upvotes", "view_count",
    ]
    return {k: company.get(k) for k in keys}


def find_company(identifier: str) -> dict | None:
    for company in DEMO_COMPANIES:
        if company["id"] == identifier or company.get("path_key") == identifier:
            return company
    return None


def sort_companies(items: list[dict], sort: str) -> list[dict]:
    if sort == "geo_score":
        return sorted(items, key=lambda c: (c.get("geo_score") or 0), reverse=True)
    if sort == "views":
        return sorted(items, key=lambda c: (c.get("view_count") or 0), reverse=True)
    if sort == "upvotes":
        return sorted(items, key=lambda c: (c.get("upvotes") or 0), reverse=True)
    # newest: keep demo order as created order (reverse index)
    return list(reversed(items)) if sort == "newest" else items


class Handler(SimpleHTTPRequestHandler):
    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_api(self, method: str) -> bool:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json({"status": "ok", "mode": "demo-static"})
            return True

        if path == "/api/settings/public":
            self._send_json({
                "site_name": "GEOrank",
                "site_description": "GEO 智搜优化引擎（本地演示模式）",
                "demo_mode": "true",
            })
            return True

        if path == "/api/settings/homepage":
            self._send_json({
                "mode": "default",
                "active": False,
                "active_release_id": None,
                "company_list_path": "/companies",
                "fallback_enabled": True,
            })
            return True

        if path == "/api/settings/frontend-modules":
            self._send_json({
                "default_module": "companies",
                "modules": [
                    {"key": "companies", "name": "公司", "path": "/companies", "enabled": True},
                    {"key": "diagnostic", "name": "诊断", "path": "/diagnostic", "enabled": True},
                    {"key": "solutions", "name": "问答", "path": "/solutions", "enabled": True},
                    {"key": "plans", "name": "方案", "path": "/plans", "enabled": True},
                    {"key": "keywords", "name": "拓词", "path": "/keywords", "enabled": True},
                    {"key": "tools", "name": "工具", "path": "/tools", "enabled": True},
                    {"key": "experts", "name": "专家", "path": "/experts", "enabled": True},
                    {"key": "tutorial", "name": "教程", "path": "/tutorial", "enabled": True},
                ],
            })
            return True

        if path == "/api/companies":
            page = max(int((qs.get("page") or ["1"])[0]), 1)
            size = min(max(int((qs.get("size") or ["20"])[0]), 1), 100)
            sort = (qs.get("sort") or ["newest"])[0]
            q = (qs.get("q") or [None])[0]
            category = (qs.get("category") or [None])[0]

            items = DEMO_COMPANIES[:]
            if category:
                items = [c for c in items if c.get("category") == category]
            if q:
                needle = q.lower()
                items = [
                    c for c in items
                    if needle in (c.get("name") or "").lower()
                    or needle in (c.get("short_description") or "").lower()
                ]
            items = sort_companies(items, sort)
            total = len(items)
            start = (page - 1) * size
            page_items = [brief(c) for c in items[start:start + size]]
            pages = (total + size - 1) // size if total else 1
            self._send_json({
                "items": page_items,
                "total": total,
                "page": page,
                "size": size,
                "pages": pages,
            })
            return True

        if path.startswith("/api/companies/"):
            rest = path[len("/api/companies/"):]
            parts = [p for p in rest.split("/") if p]
            if not parts:
                return False
            company = find_company(parts[0])
            if company is None:
                self._send_json({"detail": "公司不存在"}, 404)
                return True
            if len(parts) == 1:
                self._send_json(company)
                return True
            if parts[1] == "similar":
                others = [brief(c) for c in DEMO_COMPANIES if c["id"] != company["id"]][:3]
                self._send_json(others)
                return True
            if parts[1] == "pipeline-status":
                self._send_json({
                    "company_id": company["id"],
                    "status": company["pipeline_status"],
                    "publish_status": company["publish_status"],
                    "message": "演示模式：无真实流水线",
                })
                return True
            self._send_json({"detail": "演示模式未实现该接口"}, 501)
            return True

        if path == "/api/content":
            content_type = (qs.get("content_type") or [None])[0]
            size = min(max(int((qs.get("size") or ["20"])[0]), 1), 100)
            items = DEMO_TUTORIALS
            if content_type:
                items = [t for t in items if t.get("content_type") == content_type]
            self._send_json(items[:size])
            return True

        if path.startswith("/api/content/resolve/"):
            identifier = path.split("/api/content/resolve/", 1)[1]
            for item in DEMO_TUTORIALS:
                if item["slug"] == identifier or item["path_key"] == identifier or item["id"] == identifier:
                    detail = dict(item)
                    detail["body"] = f"# {item['title']}\n\n{item['summary']}\n\n（本地演示内容，完整教程需启动后端。）"
                    self._send_json(detail)
                    return True
            self._send_json({"detail": "内容不存在"}, 404)
            return True

        if path.startswith("/api/"):
            self._send_json({
                "detail": "本地演示模式：该接口需要完整 Docker 后端。当前仅提供公司目录等公开只读演示数据。",
            }, 503)
            return True

        return False

    def do_GET(self) -> None:
        if self._handle_api("GET"):
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self._handle_api("POST"):
            return
        self._send_json({"detail": "Method Not Allowed"}, 405)

    def send_head(self):
        parsed = urlparse(self.path)
        clean = parsed.path.split("?", 1)[0].split("#", 1)[0]
        if clean != "/" and clean.endswith("/"):
            clean = clean.rstrip("/")

        mapped = ROUTE_MAP.get(clean)
        if mapped:
            self.path = "/" + mapped
            return super().send_head()

        path = self.translate_path(clean)
        p = Path(path)
        if p.is_file():
            self.path = clean
            return super().send_head()
        if p.is_dir():
            index = p / "index.html"
            if index.is_file():
                rel = "/" + str(index.relative_to(ROOT)).replace("\\", "/")
                self.path = rel
                return super().send_head()
        html = Path(str(p) + ".html")
        if html.is_file():
            rel = "/" + str(html.relative_to(ROOT)).replace("\\", "/")
            self.path = rel
            return super().send_head()
        # company detail pretty path -> company.html
        if clean.startswith("/companies/"):
            self.path = "/company.html"
            return super().send_head()
        return super().send_head()

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    print("Serving GEORank dist + demo API on http://127.0.0.1:3009")
    print("NOTE: demo mode — company list uses local sample data until Docker/WSL backend is up.")
    ThreadingHTTPServer(("127.0.0.1", 3009), Handler).serve_forever()
