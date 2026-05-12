import csv
import io
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.user import Role
from ....schemas.audit import AuditLogListResponse, AuditLogResponse
from ....services import audit_service
from .auth import _get_current_user

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _require_admin(db: AsyncSession, user_id: uuid.UUID) -> None:
    from ....models.user import User
    result = await db.execute(
        select(Role).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    role = result.scalar_one_or_none()
    if role is None or role.code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только администратор")


# ─── GET /audit ───────────────────────────────────────────────────────────────

@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    request: Request,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    object_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
) -> AuditLogListResponse:
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    logs, total = await audit_service.get_audit_logs(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        object_type=object_type,
        date_from=date_from,
        date_to=date_to,
    )

    items = [AuditLogResponse.model_validate(log) for log in logs]
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


# ─── GET /audit/export ────────────────────────────────────────────────────────

@router.get("/export")
async def export_audit_logs(
    request: Request,
    db: DbDep,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
) -> StreamingResponse:
    """Экспорт журнала аудита в CSV."""
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    # Без пагинации: для экспорта — всё что подходит под фильтры
    logs, _ = await audit_service.get_audit_logs(
        db=db, page=1, page_size=100000,
        date_from=date_from, date_to=date_to,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([
        "id", "created_at", "user_id", "action", "object_type", "object_id",
        "ip_address", "user_agent", "request_id", "details"
    ])
    for log in logs:
        writer.writerow([
            log.id,
            log.created_at.isoformat() if log.created_at else "",
            str(log.user_id) if log.user_id else "",
            log.action or "",
            log.object_type or "",
            str(log.object_id) if log.object_id else "",
            log.ip_address or "",
            log.user_agent or "",
            log.request_id or "",
            str(log.details) if log.details else "",
        ])

    buffer.seek(0)
    filename = f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
