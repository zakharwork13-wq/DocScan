import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.user import Role, User, UserSession

settings = get_settings()
ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


# ─── Пароли ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False


# ─── JWT ──────────────────────────────────────────────────────────────────────

def _load_private_key() -> str:
    return Path(settings.jwt_private_key_path).read_text()


def _load_public_key() -> str:
    return Path(settings.jwt_public_key_path).read_text()


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, _load_private_key(), algorithm=settings.jwt_algorithm)


def create_refresh_token(session_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(session_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, _load_private_key(), algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _load_public_key(), algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ─── Пользователи ─────────────────────────────────────────────────────────────

async def get_user_by_login_or_email(db: AsyncSession, login_or_email: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(
            (User.login == login_or_email.lower()) | (User.email == login_or_email.lower())
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_role_by_code(db: AsyncSession, code: str) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.code == code))
    return result.scalar_one_or_none()


async def increment_failed_attempts(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.max_login_attempts:
        user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.lockout_duration_minutes
        )
    await db.commit()


async def reset_failed_attempts(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()


def is_user_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    return datetime.now(timezone.utc) < user.locked_until


# ─── Сессии ───────────────────────────────────────────────────────────────────

async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> tuple[UserSession, str]:
    now = datetime.now(timezone.utc)
    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(session_id)

    session = UserSession(
        id=session_id,
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now,
        last_active_at=now,
        expires_at=now + timedelta(days=settings.jwt_refresh_token_expire_days),
        is_revoked=False,
    )
    db.add(session)
    await db.commit()
    return session, refresh_token


async def get_session_by_token(db: AsyncSession, refresh_token: str) -> Optional[UserSession]:
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.is_revoked.is_(False),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(db: AsyncSession, session: UserSession) -> None:
    session.is_revoked = True
    await db.commit()
