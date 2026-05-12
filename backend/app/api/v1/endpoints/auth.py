import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.user import User
from ....schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from ....services import auth_service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_current_user(request: Request, db: AsyncSession) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен недействителен")

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь недоступен")
    return user


CurrentUser = Annotated[User, Depends(lambda req=Depends(), db=Depends(get_db): _get_current_user(req, db))]


# ─── POST /auth/register ──────────────────────────────────────────────────────

@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbDep, request: Request) -> UserInfo:
    from sqlalchemy import select
    from ....models.user import User as UserModel

    existing = await auth_service.get_user_by_login_or_email(db, body.login)
    if existing is None:
        existing = await auth_service.get_user_by_login_or_email(db, body.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже существует")

    role = await auth_service.get_role_by_code(db, body.role)
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Роль не найдена")

    from datetime import datetime, timezone
    user = UserModel(
        login=body.login,
        email=body.email,
        password_hash=auth_service.hash_password(body.password),
        full_name=body.full_name,
        role_id=role.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserInfo(
        id=user.id,
        login=user.login,
        email=user.email,
        full_name=user.full_name,
        role=role.code,
    )


# ─── POST /auth/login ─────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbDep, request: Request) -> TokenResponse:
    user = await auth_service.get_user_by_login_or_email(db, body.login)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    if auth_service.is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Учётная запись временно заблокирована из-за неудачных попыток входа",
        )

    if not user.is_active or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись недоступна")

    if not auth_service.verify_password(body.password, user.password_hash):
        await auth_service.increment_failed_attempts(db, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    await auth_service.reset_failed_attempts(db, user)

    role = await auth_service.get_role_by_code(db, "")
    from sqlalchemy import select
    from ....models.user import Role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role_obj = role_result.scalar_one()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    _, refresh_token = await auth_service.create_session(db, user.id, ip, ua)
    access_token = auth_service.create_access_token(user.id, role_obj.code)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: RefreshRequest, db: DbDep) -> AccessTokenResponse:
    try:
        payload = auth_service.decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен")

    session = await auth_service.get_session_by_token(db, body.refresh_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена или истекла")

    user = await auth_service.get_user_by_id(db, session.user_id)
    if user is None or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь недоступен")

    from sqlalchemy import select
    from ....models.user import Role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role_obj = role_result.scalar_one()

    access_token = auth_service.create_access_token(user.id, role_obj.code)
    return AccessTokenResponse(access_token=access_token)


# ─── POST /auth/logout ────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: DbDep) -> None:
    session = await auth_service.get_session_by_token(db, body.refresh_token)
    if session:
        await auth_service.revoke_session(db, session)


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserInfo)
async def me(request: Request, db: DbDep) -> UserInfo:
    user = await _get_current_user(request, db)

    from sqlalchemy import select
    from ....models.user import Role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role_obj = role_result.scalar_one()

    return UserInfo(
        id=user.id,
        login=user.login,
        email=user.email,
        full_name=user.full_name,
        role=role_obj.code,
    )
