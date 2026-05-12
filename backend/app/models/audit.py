import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    object_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    object_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result: Mapped[str] = mapped_column(String(10), nullable=False)  # success | failure
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    prev_record_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User")  # type: ignore[name-defined]
