import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scan_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # client | server
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )  # queued | processing | completed | failed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    document_category: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # public | internal | confidential | strict
    findings_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="scans")  # type: ignore[name-defined]
    findings: Mapped[list["ScanFinding"]] = relationship(
        "ScanFinding", back_populates="scan", cascade="all, delete-orphan"
    )
    temp_files: Mapped[list["TempFile"]] = relationship("TempFile", back_populates="scan")


class ScanFinding(Base):
    __tablename__ = "scan_findings"

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    masked_value: Mapped[str] = mapped_column(String(255), nullable=False)
    position_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    context_masked: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_rules.id"), nullable=True
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")
    rule: Mapped[Optional["DetectionRule"]] = relationship("DetectionRule")  # type: ignore[name-defined]


class TempFile(Base):
    __tablename__ = "temp_files"

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="temp_files")
