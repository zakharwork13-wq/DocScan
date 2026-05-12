import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RuleResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    finding_type: str
    pattern: str
    validator: Optional[str]
    base_confidence: float
    positive_keywords: Optional[list[str]]
    negative_keywords: Optional[list[str]]
    is_active: bool
    is_builtin: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RuleListResponse(BaseModel):
    items: list[RuleResponse]
    total: int


class RuleCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    finding_type: str = Field(..., min_length=1, max_length=50)
    pattern: str = Field(..., min_length=1)
    validator: Optional[str] = Field(None, max_length=50)
    base_confidence: float = Field(0.5, ge=0.0, le=1.0)
    positive_keywords: Optional[list[str]] = None
    negative_keywords: Optional[list[str]] = None
    is_active: bool = True


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    pattern: Optional[str] = None
    validator: Optional[str] = None
    base_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    positive_keywords: Optional[list[str]] = None
    negative_keywords: Optional[list[str]] = None
    is_active: Optional[bool] = None


class RuleVersionResponse(BaseModel):
    id: int
    rule_id: uuid.UUID
    version: int
    snapshot: dict[str, Any]
    changed_by: Optional[uuid.UUID]
    changed_at: datetime

    model_config = {"from_attributes": True}


class RuleTestRequest(BaseModel):
    pattern: str
    text: str
    validator: Optional[str] = None


class RuleTestMatch(BaseModel):
    value: str
    start: int
    end: int
    valid: bool


class RuleTestResponse(BaseModel):
    matches: list[RuleTestMatch]
    error: Optional[str] = None
