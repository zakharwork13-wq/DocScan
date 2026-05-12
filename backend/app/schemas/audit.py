import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[uuid.UUID]
    action: str
    object_type: Optional[str]
    object_id: Optional[uuid.UUID]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    details: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
