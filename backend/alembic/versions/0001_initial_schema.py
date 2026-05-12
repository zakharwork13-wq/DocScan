# -*- coding: utf-8 -*-
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------
    # roles
    # -------------------------
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # -------------------------
    # users
    # -------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("login", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_login", "users", ["login"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # -------------------------
    # user_sessions
    # -------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    # -------------------------
    # detection_rules
    # -------------------------
    op.create_table(
        "detection_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("rule_content", sa.Text(), nullable=False),
        sa.Column("finding_type", sa.String(50), nullable=False),
        sa.Column("base_confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_detection_rules_code", "detection_rules", ["code"])
    op.create_index("ix_detection_rules_is_enabled", "detection_rules", ["is_enabled"])

    # -------------------------
    # rule_versions
    # -------------------------
    op.create_table(
        "rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("rule_content", sa.Text(), nullable=False),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["detection_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------
    # rule_keywords
    # -------------------------
    op.create_table(
        "rule_keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("keyword_type", sa.String(10), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("case_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["rule_id"], ["detection_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------
    # scans
    # -------------------------
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("scan_mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("document_category", sa.String(20), nullable=True),
        sa.Column("findings_summary", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_status", "scans", ["status"])
    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_index("ix_scans_file_hash", "scans", ["file_hash"])

    # -------------------------
    # scan_findings
    # -------------------------
    op.create_table(
        "scan_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(50), nullable=False),
        sa.Column("masked_value", sa.String(255), nullable=False),
        sa.Column("position_start", sa.Integer(), nullable=True),
        sa.Column("position_end", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("context_masked", sa.String(500), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["detection_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_findings_scan_id", "scan_findings", ["scan_id"])
    op.create_index("ix_scan_findings_finding_type", "scan_findings", ["finding_type"])

    # -------------------------
    # temp_files
    # -------------------------
    op.create_table(
        "temp_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_temp_files_expires_at", "temp_files", ["expires_at"])

    # -------------------------
    # audit_log
    # -------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("object_id", sa.String(255), nullable=True),
        sa.Column("object_type", sa.String(50), nullable=True),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("extra_data", postgresql.JSON(), nullable=True),
        sa.Column("prev_record_hash", sa.String(64), nullable=True),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])

    # Запрет UPDATE и DELETE для audit_log через правила PostgreSQL
    op.execute("""
        CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
    """)
    op.execute("""
        CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;
    """)

    # -------------------------
    # settings
    # -------------------------
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )

    # -------------------------
    # Начальные данные: роли
    # -------------------------
    op.execute("""
        INSERT INTO roles (id, code, name, description) VALUES
        (gen_random_uuid(), 'admin',   'Администратор', 'Полный доступ к системе'),
        (gen_random_uuid(), 'analyst', 'Аналитик',      'Просмотр всех сканирований и статистики'),
        (gen_random_uuid(), 'user',    'Пользователь',  'Сканирование своих документов');
    """)

    # -------------------------
    # Начальные данные: системные настройки
    # -------------------------
    op.execute("""
        INSERT INTO settings (key, value, value_type, description, category) VALUES
        ('max_file_size_mb',       '50',   'integer', 'Максимальный размер загружаемого файла (МБ)',          'storage'),
        ('temp_file_ttl_seconds',  '3600', 'integer', 'Время жизни временных файлов (секунды)',               'storage'),
        ('session_lifetime_hours', '168',  'integer', 'Время жизни сессии (часы)',                            'auth'),
        ('rate_limit_per_minute',  '60',   'integer', 'Лимит запросов в минуту на пользователя',              'security'),
        ('max_login_attempts',     '5',    'integer', 'Максимум неудачных попыток входа до блокировки',       'security'),
        ('lockout_duration_minutes','15',  'integer', 'Длительность блокировки после превышения попыток (мин)','security');
    """)


def downgrade() -> None:
    op.execute("DROP RULE IF EXISTS audit_log_no_delete ON audit_log;")
    op.execute("DROP RULE IF EXISTS audit_log_no_update ON audit_log;")
    op.drop_table("settings")
    op.drop_table("audit_log")
    op.drop_table("temp_files")
    op.drop_table("scan_findings")
    op.drop_table("scans")
    op.drop_table("rule_keywords")
    op.drop_table("rule_versions")
    op.drop_table("detection_rules")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("roles")
