import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.user import Role
from ....schemas.stats import OverviewStats, TimeSeriesResponse, TopFindingType, TopUser
from ....services import stats_service
from .auth import _get_current_user

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _require_admin_or_analyst(db: AsyncSession, user_id: uuid.UUID) -> None:
    from ....models.user import User
    result = await db.execute(
        select(Role).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    role = result.scalar_one_or_none()
    if role is None or role.code not in ("admin", "analyst"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")


@router.get("/overview", response_model=OverviewStats)
async def get_overview(request: Request, db: DbDep) -> OverviewStats:
    current_user = await _get_current_user(request, db)
    await _require_admin_or_analyst(db, current_user.id)
    return await stats_service.get_overview(db)


@router.get("/top-finding-types", response_model=list[TopFindingType])
async def get_top_finding_types(
    request: Request, db: DbDep, limit: int = Query(10, ge=1, le=50)
) -> list[TopFindingType]:
    current_user = await _get_current_user(request, db)
    await _require_admin_or_analyst(db, current_user.id)
    return await stats_service.get_top_finding_types(db, limit)


@router.get("/top-users", response_model=list[TopUser])
async def get_top_users(
    request: Request, db: DbDep, limit: int = Query(10, ge=1, le=50)
) -> list[TopUser]:
    current_user = await _get_current_user(request, db)
    await _require_admin_or_analyst(db, current_user.id)
    return await stats_service.get_top_users(db, limit)


@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    request: Request, db: DbDep, days: int = Query(30, ge=1, le=365)
) -> TimeSeriesResponse:
    current_user = await _get_current_user(request, db)
    await _require_admin_or_analyst(db, current_user.id)
    points = await stats_service.get_time_series(db, days)
    return TimeSeriesResponse(points=points, period="day")
