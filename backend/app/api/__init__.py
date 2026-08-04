"""
API 路由汇总

Suite 默认面：auth / diagnostics / keywords / content-engine / trust-obs /
settings / admin / usage / integrations（GEOFlow 仅 legacy 可选）。

已下线产品 API（companies / experts / solutions / content wiki）不再挂载；
模块文件保留供 Admin 内部引用与历史测试，页面层由 web/* 301 → /suite。
"""
from fastapi import APIRouter

from app.api.routes import (
    auth,
    diagnostics,
    admin,
    settings,
    keywords,
    usage,
    integrations,
    trust_obs,
    content_engine,
    geo_runs,
    real_obs,
    geo_kb_api,
    geo_strategy_api,
)

router = APIRouter()

router.include_router(auth.router,        prefix="/auth",        tags=["认证"])
router.include_router(diagnostics.router,  prefix="/diagnostics", tags=["诊断"])
router.include_router(keywords.router,     prefix="/keywords",    tags=["拓词"])
router.include_router(usage.router,        prefix="/usage",       tags=["AI 用量"])
router.include_router(integrations.router, prefix="/integrations", tags=["集成"])
router.include_router(trust_obs.router,   prefix="/admin/trust-obs", tags=["可信观测"])
router.include_router(content_engine.router, prefix="/content-engine", tags=["内容引擎"])
router.include_router(geo_kb_api.router,   prefix="/content-engine", tags=["GEO知识库工作流"])
router.include_router(geo_runs.router,     prefix="/geo-runs",    tags=["GEO 回合"])
router.include_router(real_obs.router,     prefix="/geo-runs",    tags=["真实点名观测"])
router.include_router(geo_strategy_api.router, prefix="/geo-strategies", tags=["GEO策略"])
router.include_router(admin.router,        prefix="/admin",       tags=["后台管理"])
router.include_router(settings.router,     prefix="/settings",    tags=["站点配置"])
