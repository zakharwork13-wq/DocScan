"""
Универсальный запускатель задач: пробует Celery+Redis,
при недоступности — запускает задачу inline в фоновой задаче FastAPI.

Это позволяет работать в development без Redis,
а в production использовать полноценную очередь.
"""

import asyncio
import socket
from typing import Optional

import structlog

from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()

_redis_available: Optional[bool] = None


def is_redis_available() -> bool:
    """Проверяет доступность Redis (кешируется на время процесса)."""
    global _redis_available
    if _redis_available is not None:
        return _redis_available

    try:
        from urllib.parse import urlparse
        parsed = urlparse(settings.redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        with socket.create_connection((host, port), timeout=1):
            _redis_available = True
            log.info("redis_available", host=host, port=port)
    except (OSError, socket.timeout):
        _redis_available = False
        log.warning("redis_unavailable", message="Задачи будут выполняться inline")

    return _redis_available


async def run_scan_task(scan_id: str) -> None:
    """Запускает задачу сканирования через Celery или inline."""
    if is_redis_available():
        # Через Celery
        try:
            from ..tasks.scan_task import process_scan
            process_scan.delay(scan_id)
            log.info("task_dispatched_celery", scan_id=scan_id)
            return
        except Exception as e:
            log.error("celery_dispatch_failed", error=str(e))
            # Падаем в fallback

    # Inline-режим: запускаем асинхронно в фоне
    log.info("task_dispatched_inline", scan_id=scan_id)
    asyncio.create_task(_run_inline(scan_id))


async def _run_inline(scan_id: str) -> None:
    """Запускает задачу сканирования прямо в asyncio event loop."""
    try:
        from ..tasks.scan_task import _process_scan_async
        await _process_scan_async(scan_id)
    except Exception as e:
        log.error("inline_task_failed", scan_id=scan_id, error=str(e))
