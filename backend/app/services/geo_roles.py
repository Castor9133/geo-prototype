"""GEO 内容角色：editor / reviewer / risk / admin"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.deps import CurrentUser
from app.models.user import User, UserRole

GEO_ROLES = frozenset({"editor", "reviewer", "risk", "admin"})


def effective_geo_roles(user: User | None) -> set[str]:
    if not user:
        return set()
    roles: set[str] = set()
    if user.role == UserRole.ADMIN:
        roles.add("admin")
    gr = (getattr(user, "geo_role", None) or "").strip().lower()
    if gr in GEO_ROLES:
        roles.add(gr)
    return roles


def has_geo_role(user: User | None, *needed: str) -> bool:
    """技术/兼容路径：平台 admin 视为具备全部 GEO 能力。"""
    have = effective_geo_roles(user)
    if "admin" in have:
        return True
    return any(n in have for n in needed)


def has_business_geo_role(user: User | None, *needed: str) -> bool:
    """业务审批路径：admin 不自动顶替 editor/reviewer（PRD：admin 仅技术支持+强制终确）。"""
    have = effective_geo_roles(user)
    return any(n in have for n in needed)


def is_platform_admin(user: User | None) -> bool:
    return bool(user and user.role == UserRole.ADMIN)


def require_geo_roles(*needed: str):
    async def _dep(user: CurrentUser) -> User:
        if not has_geo_role(user, *needed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色之一: {', '.join(needed)}（或 admin）",
            )
        return user

    return _dep


def require_business_geo_roles(*needed: str):
    async def _dep(user: CurrentUser) -> User:
        if not has_business_geo_role(user, *needed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要业务角色之一: {', '.join(needed)}（admin 不自动顶替）",
            )
        return user

    return _dep
