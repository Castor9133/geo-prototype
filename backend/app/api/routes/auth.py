"""
认证 API — 注册 / 登录 / 获取当前用户
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt
import bcrypt
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import DbSession, CurrentUser
from app.models.user import User, UserRole
from app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserProfileUpdateRequest,
)
from app.services.phone_security import (
    assign_user_phone,
    normalize_phone_digits,
    phone_lookup_hash,
    reveal_user_phone,
)

router = APIRouter()


# ---------- 工具函数 ----------

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _normalize_phone(phone: str | None) -> str:
    """兼容 admin 等模块导入；校验失败抛 HTTP 422。"""
    try:
        return normalize_phone_digits(phone)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        username=user.username,
        phone=reveal_user_phone(user),
        role=user.role.value if hasattr(user.role, "value") else user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


async def _username_exists(db: DbSession, username: str) -> bool:
    result = await db.execute(select(User.id).where(User.username == username))
    return result.scalar_one_or_none() is not None


async def _build_phone_identity(db: DbSession, phone: str) -> tuple[str, str]:
    base_username = f"u_{phone}"
    username = base_username
    suffix = 1
    while await _username_exists(db, username):
        username = f"{base_username}_{suffix}"
        suffix += 1
    email = f"phone_{phone}@phone.local"
    return username, email


def _create_access_token(
    user_id: str,
    *,
    token_version: int = 0,
    persistent: bool = False,
) -> str:
    expire = datetime.now(timezone.utc) + (
        timedelta(days=settings.JWT_PERSIST_DAYS)
        if persistent
        else timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload = {"sub": user_id, "ver": int(token_version), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ---------- 路由 ----------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession):
    """用户注册 — 创建账号并返回 JWT"""
    phone = _normalize_phone(data.phone) if data.phone else None
    username = data.username
    email = str(data.email) if data.email else None

    if phone:
        phone_hash = phone_lookup_hash(phone)
        result = await db.execute(select(User).where(User.phone_hash == phone_hash))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册")
        if not username or not email:
            username, email = await _build_phone_identity(db, phone)

    if not username or not email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="注册信息不完整")

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用")

    user = User(
        email=email,
        username=username,
        hashed_password=_hash_password(data.password),
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
    )
    assign_user_phone(user, phone)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _create_access_token(
        str(user.id),
        token_version=user.token_version,
        persistent=data.remember_me,
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: DbSession):
    """用户登录 — 支持手机号 / 用户名 / 邮箱（全局限速 200次/分钟/IP 兜底）"""
    identifier = data.phone or data.account or data.username or ""
    filters = []
    if data.phone:
        normalized_phone = _normalize_phone(data.phone)
        filters.append(User.phone_hash == phone_lookup_hash(normalized_phone))
    else:
        filters.extend([User.username == identifier, User.email == identifier])

    result = await db.execute(select(User).where(or_(*filters)))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    # 遗留明文手机号：登录成功后升级为密文 + hash
    plain = reveal_user_phone(user)
    if plain and (not user.phone_hash or not (user.phone or "").startswith("ph1.")):
        assign_user_phone(user, plain)
        await db.commit()

    token = _create_access_token(
        str(user.id),
        token_version=user.token_version,
        persistent=data.remember_me,
    )
    return TokenResponse(access_token=token)


@router.post("/demo-admin-session", response_model=TokenResponse)
async def demo_admin_session(db: DbSession):
    """本地演示：在 GEORANK_ALLOW_ANONYMOUS_AI 开启时签发管理员 JWT，供 /settings 免弹登录。

    不放宽 AdminUser 依赖；生产环境配置校验会禁止该开关。
    """
    if not bool(getattr(settings, "GEORANK_ALLOW_ANONYMOUS_AI", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="演示管理员会话未开启",
        )
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        .order_by(User.created_at.asc())
        .limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(
            select(User).where(User.username == "admin", User.is_active.is_(True)).limit(1)
        )
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未找到演示管理员，请先执行 seed",
        )
    if user.role != UserRole.ADMIN and str(getattr(user.role, "value", user.role)) != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="演示账号不是管理员")
    token = _create_access_token(
        str(user.id),
        token_version=user.token_version,
        persistent=True,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser):
    """获取当前登录用户信息"""
    return _user_out(current_user)


@router.put("/me", response_model=UserOut)
async def update_me(data: UserProfileUpdateRequest, current_user: CurrentUser, db: DbSession):
    """修改当前登录用户资料"""
    updates = data.model_dump(exclude_unset=True)

    if "username" in updates and updates["username"] is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="用户名不能为空")
    if "email" in updates and updates["email"] is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="邮箱不能为空")

    next_username = updates["username"].strip() if "username" in updates and updates["username"] else None
    if "username" in updates and not next_username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="用户名不能为空")
    if next_username and next_username != current_user.username:
        result = await db.execute(
            select(User.id).where(User.username == next_username, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用")
        current_user.username = next_username

    next_email = str(updates["email"]).strip() if "email" in updates and updates["email"] else None
    if "email" in updates and not next_email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="邮箱不能为空")
    if next_email and next_email != current_user.email:
        result = await db.execute(
            select(User.id).where(User.email == next_email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")
        current_user.email = next_email

    if "phone" in updates:
        raw_phone = updates["phone"]
        next_phone = _normalize_phone(raw_phone) if raw_phone and str(raw_phone).strip() else None
        current_plain = reveal_user_phone(current_user)
        if next_phone != current_plain:
            if next_phone:
                phone_hash = phone_lookup_hash(next_phone)
                result = await db.execute(
                    select(User.id).where(User.phone_hash == phone_hash, User.id != current_user.id)
                )
                if result.scalar_one_or_none():
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册")
            assign_user_phone(current_user, next_phone)

    await db.commit()
    await db.refresh(current_user)
    return _user_out(current_user)


@router.put("/password")
async def change_password(data: PasswordChangeRequest, current_user: CurrentUser, db: DbSession):
    """修改当前登录用户密码"""
    locked_user = await db.scalar(
        select(User)
        .where(User.id == current_user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locked_user or not _verify_password(data.current_password, locked_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    if _verify_password(data.new_password, locked_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")

    locked_user.hashed_password = _hash_password(data.new_password)
    locked_user.token_version += 1
    await db.commit()
    return {"message": "密码已更新"}
