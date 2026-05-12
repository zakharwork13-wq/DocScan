"""
Сервис уведомлений через WebSocket.
Менеджер активных подключений: один пользователь может иметь несколько вкладок.
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import WebSocket


class NotificationManager:
    def __init__(self) -> None:
        # user_id -> set[WebSocket]
        self._connections: dict[uuid.UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if sockets is not None:
                sockets.discard(websocket)
                if not sockets:
                    self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: uuid.UUID, payload: dict[str, Any]) -> None:
        """Отправить событие всем активным сессиям пользователя."""
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))

        if not sockets:
            return

        msg = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(user_id, ws)

    async def broadcast_admins(self, payload: dict[str, Any]) -> None:
        """Зарезервировано: рассылка администраторам (нужен реестр ролей в коннекшенах)."""
        # Упрощённо: пока рассылаем всем подключённым
        async with self._lock:
            all_sockets = [ws for sockets in self._connections.values() for ws in sockets]

        msg = json.dumps(payload, default=str)
        for ws in all_sockets:
            try:
                await ws.send_text(msg)
            except Exception:
                pass


# Глобальный менеджер уведомлений
manager = NotificationManager()
