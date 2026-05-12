"""
Сервис аудита действий пользователей.
Журнал immutable: записи не редактируются и не удаляются (защита триггером БД).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    object_type: Optional[str] = None,
    object_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> AuditLog:
    """
    Записать событие в журнал аудита.
    Если в текущей транзакции уже есть незакоммиченные изменения — передать commit=False.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        details=details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return log


async def get_audit_logs(
    db: AsyncSession,
    page: int,
    page_size: int,
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    object_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total
