from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", extra="ignore")

    # Приложение
    app_env: Literal["development", "production"] = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    # База данных
    database_url: str
    postgres_db: str = "docscan"
    postgres_user: str = "docscan"
    postgres_password: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis
    redis_url: str
    redis_password: str

    # JWT
    jwt_private_key_path: str = "/app/certs/private.pem"
    jwt_public_key_path: str = "/app/certs/public.pem"
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Шифрование файлов
    file_encryption_master_key: str

    # Хранилище
    storage_backend: Literal["local", "minio"] = "local"
    storage_local_path: str = "/app/storage"
    temp_file_ttl_seconds: int = 3600

    # Лимиты
    max_file_size_mb: int = 50
    rate_limit_per_minute: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Первый администратор
    admin_login: str = "admin"
    admin_email: str = "admin@example.com"
    admin_password: str
    admin_full_name: str = "Администратор системы"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
