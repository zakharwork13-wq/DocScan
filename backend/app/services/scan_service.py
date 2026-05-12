import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.scan import Scan, ScanFinding, TempFile

settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/msword",                                                         # doc
    "application/pdf",                                                            # pdf
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         # xlsx
    "application/vnd.ms-excel",                                                  # xls
    "text/plain",                                                                 # txt
    "text/rtf",                                                                   # rtf
    "application/rtf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─── Создание записи сканирования ─────────────────────────────────────────────

async def create_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    file_size: int,
    file_hash: str,
    mime_type: str,
    scan_mode: str,
) -> Scan:
    scan = Scan(
        user_id=user_id,
        original_filename=filename,
        file_size_bytes=file_size,
        file_hash=file_hash,
        mime_type=mime_type,
        scan_mode=scan_mode,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


# ─── Сохранение временного файла ──────────────────────────────────────────────

async def save_temp_file(
    db: AsyncSession,
    scan_id: uuid.UUID,
    file_data: bytes,
) -> TempFile:
    from datetime import timedelta
    from ..services.crypto_service import encrypt_file, encrypt_key

    storage_path = Path(settings.storage_local_path) / str(scan_id)
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / "upload.bin"

    encrypted_data, file_key = encrypt_file(file_data)
    file_path.write_bytes(encrypted_data)

    encrypted_key = encrypt_key(file_key)
    now = datetime.now(timezone.utc)

    temp = TempFile(
        scan_id=scan_id,
        storage_path=str(file_path),
        encrypted_key=encrypted_key,
        uploaded_at=now,
        expires_at=now + timedelta(seconds=settings.temp_file_ttl_seconds),
        is_processed=False,
    )
    db.add(temp)
    await db.commit()
    return temp


# ─── Получение сканирований ───────────────────────────────────────────────────

async def get_scan_by_id(db: AsyncSession, scan_id: uuid.UUID) -> Optional[Scan]:
    result = await db.execute(select(Scan).where(Scan.id == scan_id, Scan.is_deleted.is_(False)))
    return result.scalar_one_or_none()


async def get_scans_list(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    page: int,
    page_size: int,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> tuple[list[Scan], int]:
    query = select(Scan).where(Scan.is_deleted.is_(False))

    if user_id is not None:
        query = query.where(Scan.user_id == user_id)
    if status:
        query = query.where(Scan.status == status)
    if category:
        query = query.where(Scan.document_category == category)

    query = query.order_by(Scan.created_at.desc())

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all()), total


# ─── Мягкое удаление ──────────────────────────────────────────────────────────

async def soft_delete_scan(db: AsyncSession, scan: Scan) -> None:
    scan.is_deleted = True
    await db.commit()


# ─── Сохранение результата клиентского сканирования ──────────────────────────

async def create_client_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    file_size: int,
    file_hash: str,
    mime_type: str,
    document_category: str,
    findings_summary: dict,
) -> Scan:
    now = datetime.now(timezone.utc)
    scan = Scan(
        user_id=user_id,
        original_filename=filename,
        file_size_bytes=file_size,
        file_hash=file_hash,
        mime_type=mime_type,
        scan_mode="client",
        status="completed",
        created_at=now,
        started_at=now,
        finished_at=now,
        processing_duration_ms=0,
        document_category=document_category,
        findings_summary=findings_summary,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan
