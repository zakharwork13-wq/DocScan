"""
Сервис агрегированной статистики для дашбордов.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.scan import Scan
from ..models.user import User
from ..schemas.stats import OverviewStats, TimeSeriesPoint, TopFindingType, TopUser


async def get_overview(db: AsyncSession) -> OverviewStats:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    base = select(func.count()).select_from(Scan).where(Scan.is_deleted.is_(False))

    total_scans = (await db.execute(base)).scalar_one()
    scans_today = (await db.execute(base.where(Scan.created_at >= today_start))).scalar_one()
    scans_week = (await db.execute(base.where(Scan.created_at >= week_start))).scalar_one()
    scans_month = (await db.execute(base.where(Scan.created_at >= month_start))).scalar_one()

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active_users_week = (await db.execute(
        select(func.count()).select_from(User).where(User.last_login_at >= week_start)
    )).scalar_one()

    # Распределение по статусам
    status_rows = await db.execute(
        select(Scan.status, func.count())
        .where(Scan.is_deleted.is_(False))
        .group_by(Scan.status)
    )
    by_status = {row[0]: row[1] for row in status_rows.all()}

    # Распределение по категориям
    cat_rows = await db.execute(
        select(Scan.document_category, func.count())
        .where(Scan.is_deleted.is_(False), Scan.document_category.is_not(None))
        .group_by(Scan.document_category)
    )
    by_category = {row[0]: row[1] for row in cat_rows.all()}

    # Распределение по режиму сканирования
    mode_rows = await db.execute(
        select(Scan.scan_mode, func.count())
        .where(Scan.is_deleted.is_(False))
        .group_by(Scan.scan_mode)
    )
    by_scan_mode = {row[0]: row[1] for row in mode_rows.all()}

    return OverviewStats(
        total_scans=total_scans,
        scans_today=scans_today,
        scans_week=scans_week,
        scans_month=scans_month,
        total_users=total_users,
        active_users_week=active_users_week,
        by_status=by_status,
        by_category=by_category,
        by_scan_mode=by_scan_mode,
    )


async def get_top_finding_types(db: AsyncSession, limit: int = 10) -> list[TopFindingType]:
    """Топ типов находок за всё время."""
    sql = text("""
        SELECT finding_type, COUNT(*) as cnt
        FROM scan_findings f
        JOIN scans s ON s.id = f.scan_id
        WHERE s.is_deleted = false
        GROUP BY finding_type
        ORDER BY cnt DESC
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"lim": limit})).all()
    return [TopFindingType(finding_type=r[0], count=r[1]) for r in rows]


async def get_top_users(db: AsyncSession, limit: int = 10) -> list[TopUser]:
    """Топ пользователей по числу сканирований."""
    sql = text("""
        SELECT u.id, u.login, COUNT(s.id) as cnt
        FROM users u
        LEFT JOIN scans s ON s.user_id = u.id AND s.is_deleted = false
        GROUP BY u.id, u.login
        ORDER BY cnt DESC
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"lim": limit})).all()
    return [TopUser(user_id=str(r[0]), login=r[1], scans_count=r[2]) for r in rows]


async def get_time_series(db: AsyncSession, days: int = 30) -> list[TimeSeriesPoint]:
    """График: количество сканирований и находок по дням."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    sql = text("""
        SELECT
            DATE(s.created_at) AS day,
            COUNT(DISTINCT s.id) AS scans,
            COUNT(f.id) AS findings
        FROM scans s
        LEFT JOIN scan_findings f ON f.scan_id = s.id
        WHERE s.is_deleted = false AND s.created_at >= :since
        GROUP BY DATE(s.created_at)
        ORDER BY day
    """)
    rows = (await db.execute(sql, {"since": since})).all()
    return [TimeSeriesPoint(date=str(r[0]), scans=r[1], findings=r[2]) for r in rows]
