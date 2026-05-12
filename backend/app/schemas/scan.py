import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScanFindingResponse(BaseModel):
    id: uuid.UUID
    finding_type: str
    masked_value: str
    position_start: Optional[int]
    position_end: Optional[int]
    page_number: Optional[int]
    confidence: float
    context_masked: Optional[str]

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    file_hash: str
    mime_type: str
    scan_mode: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    processing_duration_ms: Optional[int]
    document_category: Optional[str]
    findings_summary: Optional[dict]
    error_message: Optional[str]
    findings: list[ScanFindingResponse] = []

    model_config = {"from_attributes": True}


class ScanBriefResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    scan_mode: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    document_category: Optional[str]
    findings_summary: Optional[dict]

    model_config = {"from_attributes": True}


class ScanListResponse(BaseModel):
    items: list[ScanBriefResponse]
    total: int
    page: int
    page_size: int


class ScanStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    progress: Optional[int] = None


class ClientScanResultRequest(BaseModel):
    original_filename: str
    file_size_bytes: int
    file_hash: str
    mime_type: str
    document_category: str
    findings_summary: dict
