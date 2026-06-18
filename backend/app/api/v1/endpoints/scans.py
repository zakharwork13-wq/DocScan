import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.scan import Scan, ScanFinding
from ....models.user import Role
from ....schemas.scan import (
    ClientScanResultRequest,
    ScanBriefResponse,
    ScanListResponse,
    ScanResponse,
    ScanStatusResponse,
)
from ....services import scan_service
from ....services.scan_service import ALLOWED_MIME_TYPES
from ....config import get_settings
from .auth import _get_current_user

router = APIRouter()
settings = get_settings()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_role_code(db: AsyncSession, user_id: uuid.UUID) -> str:
    from ....models.user import User
    result = await db.execute(
        select(Role).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    role = result.scalar_one_or_none()
    return role.code if role else "user"


def _to_scan_response(scan: Scan, findings: list[ScanFinding]) -> ScanResponse:
    from ....schemas.scan import ScanFindingResponse
    return ScanResponse(
        id=scan.id,
        user_id=scan.user_id,
        original_filename=scan.original_filename,
        file_size_bytes=scan.file_size_bytes,
        file_hash=scan.file_hash,
        mime_type=scan.mime_type,
        scan_mode=scan.scan_mode,
        status=scan.status,
        created_at=scan.created_at,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        processing_duration_ms=scan.processing_duration_ms,
        document_category=scan.document_category,
        findings_summary=scan.findings_summary,
        error_message=scan.error_message,
        findings=[
            ScanFindingResponse(
                id=f.id,
                finding_type=f.finding_type,
                masked_value=f.masked_value,
                position_start=f.position_start,
                position_end=f.position_end,
                page_number=f.page_number,
                confidence=f.confidence,
                context_masked=f.context_masked,
            )
            for f in findings
        ],
    )


# ─── POST /scans/upload ───────────────────────────────────────────────────────

@router.post("/upload", response_model=ScanStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_scan(
    request: Request,
    db: DbDep,
    file: UploadFile,
) -> ScanStatusResponse:
    current_user = await _get_current_user(request, db)

    if file.size and file.size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл превышает максимальный размер {settings.max_file_size_mb} МБ",
        )

    file_data = await file.read()

    if len(file_data) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл превышает максимальный размер {settings.max_file_size_mb} МБ",
        )

    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Тип файла не поддерживается: {mime_type}",
        )

    file_hash = scan_service.compute_sha256(file_data)

    scan = await scan_service.create_scan(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "unknown",
        file_size=len(file_data),
        file_hash=file_hash,
        mime_type=mime_type,
        scan_mode="server",
    )

    await scan_service.save_temp_file(db, scan.id, file_data)

    # Запускаем задачу через Celery (если Redis доступен) или inline
    from ....services.task_runner import run_scan_task
    await run_scan_task(str(scan.id))

    return ScanStatusResponse(id=scan.id, status=scan.status)


# ─── POST /scans/client-result ────────────────────────────────────────────────

@router.post("/client-result", response_model=ScanStatusResponse, status_code=status.HTTP_201_CREATED)
async def submit_client_result(
    body: ClientScanResultRequest,
    request: Request,
    db: DbDep,
) -> ScanStatusResponse:
    current_user = await _get_current_user(request, db)

    scan = await scan_service.create_client_scan(
        db=db,
        user_id=current_user.id,
        filename=body.original_filename,
        file_size=body.file_size_bytes,
        file_hash=body.file_hash,
        mime_type=body.mime_type,
        document_category=body.document_category,
        findings_summary=body.findings_summary,
    )

    return ScanStatusResponse(id=scan.id, status=scan.status)


# ─── GET /scans/{scan_id}/status ──────────────────────────────────────────────

@router.get("/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: uuid.UUID, request: Request, db: DbDep) -> ScanStatusResponse:
    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    scan = await scan_service.get_scan_by_id(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сканирование не найдено")

    if role_code not in ("admin", "analyst") and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    return ScanStatusResponse(id=scan.id, status=scan.status)


# ─── GET /scans/{scan_id} ─────────────────────────────────────────────────────

@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: uuid.UUID, request: Request, db: DbDep) -> ScanResponse:
    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    scan = await scan_service.get_scan_by_id(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сканирование не найдено")

    if role_code not in ("admin", "analyst") and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    findings_result = await db.execute(
        select(ScanFinding).where(ScanFinding.scan_id == scan_id)
    )
    findings = list(findings_result.scalars().all())

    return _to_scan_response(scan, findings)


# ─── GET /scans ───────────────────────────────────────────────────────────────

@router.get("", response_model=ScanListResponse)
async def list_scans(
    request: Request,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_status: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
) -> ScanListResponse:
    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    # Обычный пользователь видит только свои сканирования
    filter_user_id = None if role_code in ("admin", "analyst") else current_user.id

    scans, total = await scan_service.get_scans_list(
        db=db,
        user_id=filter_user_id,
        page=page,
        page_size=page_size,
        status=scan_status,
        category=category,
    )

    items = [
        ScanBriefResponse(
            id=s.id,
            original_filename=s.original_filename,
            file_size_bytes=s.file_size_bytes,
            scan_mode=s.scan_mode,
            status=s.status,
            created_at=s.created_at,
            finished_at=s.finished_at,
            document_category=s.document_category,
            findings_summary=s.findings_summary,
        )
        for s in scans
    ]

    return ScanListResponse(items=items, total=total, page=page, page_size=page_size)


# ─── DELETE /scans/{scan_id} ──────────────────────────────────────────────────

@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(scan_id: uuid.UUID, request: Request, db: DbDep) -> None:
    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    scan = await scan_service.get_scan_by_id(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сканирование не найдено")

    if role_code != "admin" and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    await scan_service.soft_delete_scan(db, scan)


# ─── GET /scans/{scan_id}/report ──────────────────────────────────────────────

@router.get("/{scan_id}/report")
async def download_scan_report(scan_id: uuid.UUID, request: Request, db: DbDep):
    """Скачать PDF-отчёт о сканировании."""
    from fastapi.responses import Response

    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    scan = await scan_service.get_scan_by_id(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сканирование не найдено")

    if role_code not in ("admin", "analyst") and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if scan.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отчёт доступен только для завершённых сканирований",
        )

    findings_result = await db.execute(
        select(ScanFinding).where(ScanFinding.scan_id == scan_id)
    )
    findings = list(findings_result.scalars().all())

    from ....services.report_service import generate_scan_report
    pdf_bytes = generate_scan_report(scan, findings)

    filename = f"docscan_report_{scan.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── GET /scans/{scan_id}/redacted ────────────────────────────────────────────

@router.get("/{scan_id}/redacted")
async def download_redacted(scan_id: uuid.UUID, request: Request, db: DbDep):
    """Скачать обезличенную копию документа (только серверное сканирование)."""
    from pathlib import Path

    from fastapi.responses import Response

    current_user = await _get_current_user(request, db)
    role_code = await _get_role_code(db, current_user.id)

    scan = await scan_service.get_scan_by_id(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сканирование не найдено")

    if role_code not in ("admin", "analyst") and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if scan.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Обезличивание доступно только для завершённых сканирований",
        )

    if scan.scan_mode != "server":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для клиентских сканирований обезличенная копия доступна сразу при загрузке",
        )

    redacted_path = Path(settings.storage_local_path) / str(scan_id) / "redacted.txt"
    if not redacted_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Обезличенная копия недоступна (возможно, файл удалён по сроку TTL)",
        )

    content = redacted_path.read_text(encoding="utf-8")

    from urllib.parse import quote

    base = scan.original_filename
    dot = base.rfind(".")
    name = base[:dot] if dot > 0 else base
    filename = f"{name}_обезличено.txt"
    # RFC 5987: percent-encode для UTF-8 имён в заголовке
    filename_encoded = quote(filename, safe="")
    # ASCII fallback на случай если клиент не поймёт filename*
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "redacted.txt"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{filename_encoded}"
            ),
        },
    )
