"""已删除的问答/方案生成：旧 URL 永久重定向到 GEO Suite。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(include_in_schema=False)

SUITE_REDIRECT = "/suite"


@router.get("/solutions")
@router.get("/solutions/{identifier:path}")
@router.get("/solutions.html")
@router.get("/qa")
@router.get("/qa/{identifier:path}")
@router.get("/plans")
@router.get("/plans/{identifier:path}")
@router.get("/plans.html")
async def redirect_retired_solutions(_request: Request, identifier: str | None = None) -> RedirectResponse:
    del identifier
    return RedirectResponse(url=SUITE_REDIRECT, status_code=301)
