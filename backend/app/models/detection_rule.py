import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk


class DetectionRule(Base, TimestampMixin):
    __tablename__ = "detection_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # regex | dictionary | morphology | yara
    rule_content: Mapped[str] = mapped_column(Text, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    versions: Mapped[list["RuleVersion"]] = relationship(
        "RuleVersion", back_populates="rule", cascade="all, delete-orphan"
    )
    keywords: Mapped[list["RuleKeyword"]] = relationship(
        "RuleKeyword", back_populates="rule", cascade="all, delete-orphan"
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_rules.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_content: Mapped[str] = mapped_column(Text, nullable=False)
    change_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    rule: Mapped["DetectionRule"] = relationship("DetectionRule", back_populates="versions")


class RuleKeyword(Base):
    __tablename__ = "rule_keywords"

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_rules.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    keyword_type: Mapped[str] = mapped_column(String(10), nullable=False)  # positive | negative
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rule: Mapped["DetectionRule"] = relationship("DetectionRule", back_populates="keywords")
