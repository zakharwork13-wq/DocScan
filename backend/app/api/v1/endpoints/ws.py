"""
WebSocket-эндпоинт для real-time уведомлений.

Протокол:
  - Клиент подключается с access-токеном в query: /api/v1/ws?token=<jwt>
  - Сервер шлёт JSON-сообщения с полем "type":
      scan.status_changed   { "scan_id", "status", "progress?" }
      scan.completed        { "scan_id", "findings_count", "category" }
      scan.failed           { "scan_id", "error" }
  - Клиент может слать "ping" — сервер ответит "pong".
"""

import uuid

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ....database import AsyncSessionLocal
from ....services import auth_service
from ....services.notification_service import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)) -> None:
    # Аутентификация по JWT из query
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Проверка что пользователь активен
    async with AsyncSessionLocal() as db:
        user = await auth_service.get_user_by_id(db, user_id)
        if user is None or not user.is_active or user.is_blocked:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect(user_id, websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            # Поддержка простого ping/pong для keepalive
            if msg.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
    except Exception:
        await manager.disconnect(user_id, websocket)
