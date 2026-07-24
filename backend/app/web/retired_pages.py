"""已删除的前台模块：专家频道旧 URL 永久重定向到 GEO Suite。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(include_in_schema=False)

SUITE_REDIRECT = "/suite"


@router.get("/experts")
@router.get("/experts/{identifier:path}")
async def redirect_retired_experts(_request: Request, identifier: str | None = None) -> RedirectResponse:
    del identifier
    return RedirectResponse(url=SUITE_REDIRECT, status_code=301)
