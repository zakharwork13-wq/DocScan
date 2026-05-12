"""
Скрипт первоначальной инициализации DocScan.

Выполняет:
  1. Генерацию RSA-ключей для JWT (если не существуют).
  2. Применение миграций Alembic.
  3. Создание учётной записи администратора.

Запуск:
  python -m scripts.init
"""

import asyncio
import os
import sys
from pathlib import Path

# Убеждаемся, что app доступен как пакет
sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select, text

from app.config import get_settings
from app.database import AsyncSessionLocal, engine
from app.models import Base, Role, User
from app.services.auth_service import hash_password

settings = get_settings()


# ─── RSA ключи ────────────────────────────────────────────────────────────────

def generate_rsa_keys() -> None:
    private_path = Path(settings.jwt_private_key_path)
    public_path = Path(settings.jwt_public_key_path)

    if private_path.exists() and public_path.exists():
        print("[keys] RSA-ключи уже существуют, пропускаем.")
        return

    private_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)

    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    print(f"[keys] RSA-ключи сгенерированы: {private_path}, {public_path}")


# ─── Миграции ─────────────────────────────────────────────────────────────────

def run_migrations() -> None:
    print("[migrations] Применяем миграции...")

    backend_dir = str(Path(__file__).parent.parent)

    # Убираем backend/ из sys.path чтобы локальная папка alembic/ не перекрывала пакет
    clean_path = [p for p in sys.path if p not in ("", ".", backend_dir)]
    original_path = sys.path.copy()
    sys.path = clean_path

    try:
        from alembic.config import Config
        from alembic import command as alembic_command
        from dotenv import load_dotenv
        load_dotenv(Path(backend_dir) / ".env", encoding="utf-8-sig")

        # Строим синхронный URL из переменных окружения (pg8000 — чистый Python, без проблем с кодировкой)
        db_url = (
            f"postgresql+pg8000://"
            f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
            f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
            f":{os.environ.get('POSTGRES_PORT', '5432')}"
            f"/{os.environ['POSTGRES_DB']}"
        )

        cfg = Config()
        cfg.set_main_option("script_location", str(Path(backend_dir) / "alembic"))
        cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_command.upgrade(cfg, "head")
        print("[migrations] Готово.")
    except Exception as e:
        import traceback
        print(f"[migrations] ОШИБКА: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        sys.path = original_path


# ─── Администратор ────────────────────────────────────────────────────────────

async def create_admin() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(User).where(User.login == settings.admin_login)
        )
        if existing.scalar_one_or_none() is not None:
            print(f"[admin] Пользователь '{settings.admin_login}' уже существует, пропускаем.")
            return

        role_result = await db.execute(select(Role).where(Role.code == "admin"))
        role = role_result.scalar_one_or_none()
        if role is None:
            print("[admin] ОШИБКА: роль 'admin' не найдена. Сначала примените миграции.")
            sys.exit(1)

        from datetime import datetime, timezone

        admin = User(
            login=settings.admin_login,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            full_name=settings.admin_full_name,
            role_id=role.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        await db.commit()
        print(f"[admin] Администратор '{settings.admin_login}' создан.")


# ─── Entrypoint ───────────────────────────────────────────────────────────────

async def main() -> None:
    print("=== DocScan: инициализация ===\n")
    generate_rsa_keys()
    run_migrations()
    await create_admin()
    print("\n=== Инициализация завершена ===")


if __name__ == "__main__":
    asyncio.run(main())
