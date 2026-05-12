from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_scans: int
    scans_today: int
    scans_week: int
    scans_month: int

    total_users: int
    active_users_week: int

    by_status: dict[str, int]
    by_category: dict[str, int]
    by_scan_mode: dict[str, int]


class TopFindingType(BaseModel):
    finding_type: str
    count: int


class TopUser(BaseModel):
    user_id: str
    login: str
    scans_count: int


class TimeSeriesPoint(BaseModel):
    date: str
    scans: int
    findings: int


class TimeSeriesResponse(BaseModel):
    points: list[TimeSeriesPoint]
    period: str  # day | week | month
