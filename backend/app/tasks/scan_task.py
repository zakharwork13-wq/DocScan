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

from ..config import get_settings

settings = get_settings()
log = structlog.get_logger()


# Ленивая регистрация задачи в Celery: если celery не установлен — пропускаем,
# inline-режим всё равно работает напрямую через _process_scan_async().
try:
    from ..celery_app import celery_app  # noqa: F401

    @celery_app.task(name="scan_document", bind=True, max_retries=3)
    def process_scan(self, scan_id: str) -> dict:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(_process_scan_async(scan_id))
except ImportError:
    log.info("celery_not_installed", message="Celery недоступен — режим inline")

    def process_scan(scan_id: str) -> dict:  # type: ignore
        import asyncio
        return asyncio.run(_process_scan_async(scan_id))


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

            # Создаём обезличенную копию текста и сохраняем рядом
            try:
                redacted_text = _build_redacted_text(text, raw_findings)
                redacted_path = Path(temp_file.storage_path).parent / "redacted.txt"
                redacted_path.write_text(redacted_text, encoding="utf-8")
            except Exception as exc:
                log.warning("redaction_failed", scan_id=scan_id_str, error=str(exc))

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
        text = _extract_pdf(file_data)
        # Если PDF — скан без текстового слоя, пробуем OCR
        if not text.strip():
            text = _extract_pdf_ocr(file_data)
        return text

    if mime_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        return _extract_xlsx(file_data)

    # Изображения — через OCR
    if mime_type.startswith("image/"):
        return _extract_image_ocr(file_data)

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


def _find_tesseract() -> str | None:
    """Найти бинарник Tesseract на системе."""
    import os
    import shutil

    found = shutil.which("tesseract")
    if found:
        return found

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\soft\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_tessdata() -> str | None:
    """Найти папку tessdata с языковыми моделями. Сначала ищем в проекте."""
    import os
    from pathlib import Path

    # 1. В проекте: tools/tessdata (положили туда rus.traineddata и eng.traineddata)
    project_tessdata = Path(__file__).parent.parent.parent.parent / "tools" / "tessdata"
    if (project_tessdata / "rus.traineddata").exists():
        return str(project_tessdata)

    # 2. Рядом с tesseract.exe (стандартное место)
    tesseract = _find_tesseract()
    if tesseract:
        nearby = Path(tesseract).parent / "tessdata"
        if (nearby / "rus.traineddata").exists():
            return str(nearby)

    # 3. Переменная окружения
    env_path = os.environ.get("TESSDATA_PREFIX")
    if env_path and (Path(env_path) / "rus.traineddata").exists():
        return env_path

    return None


def _setup_tesseract() -> bool:
    """Настроить pytesseract: путь к бинарнику и tessdata. Вернёт True если готов."""
    import pytesseract

    tesseract_path = _find_tesseract()
    if not tesseract_path:
        log.warning("tesseract_not_found", message="Tesseract не установлен")
        return False
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tessdata = _find_tessdata()
    if not tessdata:
        log.warning(
            "tessdata_not_found",
            message="Языковые модели rus.traineddata не найдены",
        )
        return False

    # Передадим tessdata через env-переменную, чтобы Tesseract её использовал
    import os
    os.environ["TESSDATA_PREFIX"] = tessdata
    return True


def _ocr_image(pil_image) -> str:
    """Прогон одной картинки PIL через Tesseract."""
    import pytesseract

    tessdata = _find_tessdata()
    # --tessdata-dir передаём через список аргументов (pytesseract сам экранирует пробелы)
    if tessdata:
        config = f'--tessdata-dir {tessdata}'
    else:
        config = ""
    return pytesseract.image_to_string(pil_image, lang="rus+eng", config=config)


def _extract_image_ocr(data: bytes) -> str:
    """Распознать текст с изображения через Tesseract."""
    try:
        import io
        from PIL import Image

        if not _setup_tesseract():
            return ""

        image = Image.open(io.BytesIO(data))
        text = _ocr_image(image)
        log.info("image_ocr_done", chars=len(text))
        return text
    except Exception as e:
        log.error("ocr_failed", error=str(e))
        return ""


def _extract_pdf_ocr(data: bytes) -> str:
    """Извлечь текст из PDF-сканов через OCR — pypdfium2 + Tesseract.

    pypdfium2 — binding для PDFium (от Google), не требует Poppler.
    """
    try:
        import pypdfium2 as pdfium
        from PIL import Image  # noqa: F401

        if not _setup_tesseract():
            return ""

        pdf = pdfium.PdfDocument(data)
        text_parts: list[str] = []
        total_pages = len(pdf)
        for page_num in range(total_pages):
            page = pdf[page_num]
            pil_image = page.render(scale=2.0).to_pil()
            page_text = _ocr_image(pil_image)
            if page_text.strip():
                text_parts.append(f"--- Страница {page_num + 1} ---\n{page_text}")
            page.close()
        pdf.close()
        log.info("pdf_ocr_done", pages=total_pages, chars=sum(len(p) for p in text_parts))
        return "\n".join(text_parts)
    except Exception as e:
        log.error("pdf_ocr_failed", error=str(e))
        return ""


def _build_redacted_text(text: str, findings: list[dict]) -> str:
    """
    Заменить найденные значения масками в исходном тексте.

    Если несколько находок перекрываются (одна и та же строка матчится
    несколькими правилами), оставляем только одну с наибольшей уверенностью.
    Замены делаем с конца, чтобы позиции остальных находок не сдвигались.
    """
    valid = [
        f for f in findings
        if (
            f.get("position_start") is not None
            and f.get("position_end") is not None
            and f["position_start"] >= 0
            and f["position_end"] <= len(text)
            and f["position_start"] < f["position_end"]
        )
    ]

    # Сортируем: по началу, при равенстве — более длинная находка раньше
    valid.sort(key=lambda f: (f["position_start"], -f["position_end"]))

    # Жадно убираем перекрывающиеся
    non_overlapping: list[dict] = []
    for f in valid:
        last = non_overlapping[-1] if non_overlapping else None
        if last is None or f["position_start"] >= last["position_end"]:
            non_overlapping.append(f)
        elif f.get("confidence", 0) > last.get("confidence", 0):
            non_overlapping[-1] = f

    # Заменяем с конца
    result = text
    for f in reversed(non_overlapping):
        mask = f.get("masked_value", "***")
        result = result[:f["position_start"]] + mask + result[f["position_end"]:]
    return result
