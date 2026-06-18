"""Общие fixtures для pytest."""

import os

# Минимальные настройки чтобы Settings загрузился без .env
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("FILE_ENCRYPTION_MASTER_KEY", "0" * 64)
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123")
