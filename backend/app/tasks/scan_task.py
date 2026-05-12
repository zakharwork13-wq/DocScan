"""
Celery-задача серверного сканирования документа.

Этапы:
  1. Загрузка зашифрованного файла из временного хранилища.
  2. Расшифровка.
  3. Определение формата и парсинг текста.
  4. Применение правил детекции (regex + валидаторы).
  5. Морфологический анализ (ФИО, адреса) — этап 3 роадмапа.
  6. Сохранение результата в БД.
  7. Очистка временного файла.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog

from ..celery_app import celery_app
from ..config import get_settings

settings = get_settings()
log = structlog.get_logger()


@celery_app.task(name="scan_document", bind=True, max_retries=3)
def process_scan(self, scan_id: str) -> dict:
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_process_scan_async(scan_id))


async def _process_scan_async(scan_id_str: str) -> dict:
    from sqlalchemy import select
    from ..database import AsyncSessionLocal
    from ..models.scan import Scan, ScanFinding, TempFile

    scan_id = uuid.UUID(scan_id_str)
    log.info("scan_started", scan_id=scan_id_str)

    async with AsyncSessionLocal() as db:
        # Загружаем запись сканирования
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        if scan is None:
            log.error("scan_not_found", scan_id=scan_id_str)
            return {"error": "scan not found"}

        scan.status = "processing"
        scan.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # Загружаем временный файл
            temp_result = await db.execute(
                select(TempFile).where(TempFile.scan_id == scan_id)
            )
            temp_file = temp_result.scalar_one_or_none()
            if temp_file is None:
                raise RuntimeError("Временный файл не найден")

            # Расшифровываем файл
            from ..services.crypto_service import decrypt_file, decrypt_key
            file_key = decrypt_key(temp_file.encrypted_key)
            encrypted_data = Path(temp_file.storage_path).read_bytes()
            file_data = decrypt_file(encrypted_data, file_key)

            # Извлекаем текст
            text = _extract_text(file_data, scan.mime_type)

            # Применяем правила детекции
            from ..detection.engine import DetectionEngine
            engine = DetectionEngine()
            raw_findings = engine.scan(text)

            # Классифицируем документ
            category = engine.classify(raw_findings)

            # Формируем сводку
            summary: dict[str, int] = {}
            for f in raw_findings:
                summary[f["finding_type"]] = summary.get(f["finding_type"], 0) + 1

            # Сохраняем находки в БД
            for f in raw_findings:
                finding = ScanFinding(
                    scan_id=scan_id,
                    finding_type=f["finding_type"],
                    masked_value=f["masked_value"],
                    position_start=f.get("position_start"),
                    position_end=f.get("position_end"),
                    confidence=f["confidence"],
                    context_masked=f.get("context_masked"),
                )
                db.add(finding)

            now = datetime.now(timezone.utc)
            scan.status = "completed"
            scan.finished_at = now
            scan.processing_duration_ms = int(
                (now - scan.started_at).total_seconds() * 1000
            )
            scan.document_category = category
            scan.findings_summary = summary
            await db.commit()

            # Помечаем временный файл как обработанный
            temp_file.is_processed = True
            await db.commit()

            # WebSocket уведомление о завершении
            try:
                from ..services.notification_service import manager
                await manager.send_to_user(scan.user_id, {
                    "type": "scan.completed",
                    "scan_id": str(scan.id),
                    "findings_count": len(raw_findings),
                    "category": category,
                })
            except Exception as ws_exc:
                log.warning("ws_notify_failed", error=str(ws_exc))

            log.info("scan_completed", scan_id=scan_id_str, findings=len(raw_findings))
            return {"status": "completed", "findings": len(raw_findings)}

        except Exception as exc:
            log.error("scan_failed", scan_id=scan_id_str, error=str(exc))
            scan.status = "failed"
            scan.error_message = str(exc)
            scan.finished_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                from ..services.notification_service import manager
                await manager.send_to_user(scan.user_id, {
                    "type": "scan.failed",
                    "scan_id": str(scan.id),
                    "error": str(exc),
                })
            except Exception:
                pass
            raise


def _extract_text(file_data: bytes, mime_type: str) -> str:
    """Извлекает текст из файла по mime-типу."""
    if mime_type == "text/plain":
        for enc in ("utf-8", "windows-1251", "latin-1"):
            try:
                return file_data.decode(enc)
            except UnicodeDecodeError:
                continue
        return file_data.decode("utf-8", errors="replace")

    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(file_data)

    if mime_type == "application/pdf":
        return _extract_pdf(file_data)

    if mime_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        return _extract_xlsx(file_data)

    return ""


def _extract_docx(data: bytes) -> str:
    import io
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_pdf(data: bytes) -> str:
    import io
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _extract_xlsx(data: bytes) -> str:
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            parts.append(" ".join(str(c) for c in row if c is not None))
    return "\n".join(parts)
