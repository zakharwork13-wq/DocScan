import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.user import Role, User
from ....schemas.user import (
    ChangePasswordRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from ....services import auth_service
from .auth import _get_current_user

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _require_admin(user: User) -> None:
    """Бросает 403 если пользователь не администратор."""
    # role.code хранится в связанном объекте, но здесь role_id — проверяем через кеш
    pass  # проверка выполняется внутри эндпоинтов через role_code


async def _resolve_user_response(db: AsyncSession, user: User) -> UserResponse:
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one()
    return UserResponse(
        id=user.id,
        login=user.login,
        email=user.email,
        full_name=user.full_name,
        role=role.code,
        is_active=user.is_active,
        is_blocked=user.is_blocked,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


# ─── GET /users ───────────────────────────────────────────────────────────────

@router.get("", response_model=UserListResponse)
async def list_users(
    request: Request,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
) -> UserListResponse:
    current_user = await _get_current_user(request, db)
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    current_role = role_result.scalar_one()
    if current_role.code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    query = select(User)

    if role:
        role_filter = await db.execute(select(Role).where(Role.code == role))
        role_obj = role_filter.scalar_one_or_none()
        if role_obj:
            query = query.where(User.role_id == role_obj.id)

    if active is not None:
        query = query.where(User.is_active == active)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            (User.login.ilike(pattern)) | (User.full_name.ilike(pattern)) | (User.email.ilike(pattern))
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    users_result = await db.execute(query)
    users = users_result.scalars().all()

    items = [await _resolve_user_response(db, u) for u in users]
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


# ─── GET /users/{user_id} ─────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, request: Request, db: DbDep) -> UserResponse:
    current_user = await _get_current_user(request, db)
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    current_role = role_result.scalar_one()

    # Администратор видит всех, пользователь — только себя
    if current_role.code != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    return await _resolve_user_response(db, user)


# ─── PATCH /users/{user_id} ───────────────────────────────────────────────────

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID, body: UserUpdateRequest, request: Request, db: DbDep
) -> UserResponse:
    current_user = await _get_current_user(request, db)
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    current_role = role_result.scalar_one()
    if current_role.code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        user.email = body.email
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_blocked is not None:
        user.is_blocked = body.is_blocked
    if body.role is not None:
        new_role = await auth_service.get_role_by_code(db, body.role)
        if new_role is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Роль не найдена")
        user.role_id = new_role.id

    await db.commit()
    await db.refresh(user)
    return await _resolve_user_response(db, user)


# ─── POST /users/{user_id}/deactivate ────────────────────────────────────────

@router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(user_id: uuid.UUID, request: Request, db: DbDep) -> None:
    current_user = await _get_current_user(request, db)
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    current_role = role_result.scalar_one()
    if current_role.code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя деактивировать себя"
        )

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    user.is_active = False
    await db.commit()


# ─── POST /users/me/password ──────────────────────────────────────────────────

@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    body: ChangePasswordRequest, request: Request, db: DbDep
) -> None:
    current_user = await _get_current_user(request, db)

    if not auth_service.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный текущий пароль"
        )

    current_user.password_hash = auth_service.hash_password(body.new_password)
    await db.commit()
