"""已删除的公司目录：旧 URL 永久重定向到 GEO Suite。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(include_in_schema=False)

SUITE_REDIRECT = "/suite"


@router.get("/company")
@router.get("/company/{identifier:path}")
@router.get("/companies")
@router.get("/companies/{identifier:path}")
@router.get("/c/{identifier:path}")
@router.get("/submit-company")
@router.get("/company-submit")
async def redirect_retired_companies(_request: Request, identifier: str | None = None) -> RedirectResponse:
    del identifier
    return RedirectResponse(url=SUITE_REDIRECT, status_code=301)
