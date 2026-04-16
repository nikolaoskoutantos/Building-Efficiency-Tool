from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from db import SessionLocal
from services.websocket_tasks import TaskExecutionContext, TaskNotRegisteredError, resolve_task_handler
from utils.auth_dependencies import decode_jwt_token, resolve_registered_user_id
from utils.policies import has_permission
from utils.ws_protocol import (
    AlertMessage,
    AuthMessage,
    ErrorMessage,
    PingMessage,
    PongMessage,
    ProgressMessage,
    ResultMessage,
    model_dump,
    parse_auth_message,
    parse_runtime_client_message,
)


router = APIRouter()

AUTH_CLOSE_CODE = 4001
HEARTBEAT_INTERVAL_SECONDS = 20
HEARTBEAT_TIMEOUT_SECONDS = 10
AUTH_MESSAGE_TIMEOUT_SECONDS = 10


class WebSocketAuthError(RuntimeError):
    pass


class HeartbeatTimeoutError(RuntimeError):
    pass


class BuildingAccessError(RuntimeError):
    pass


def get_allowed_ws_origins() -> set[str]:
    origins = {"http://localhost:5173"}
    for env_var in ("WS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS"):
        raw_value = os.getenv(env_var, "")
        if not raw_value:
            continue
        origins.update({item.strip() for item in raw_value.split(",") if item.strip()})
    return origins


def is_allowed_ws_origin(origin: str | None) -> bool:
    if not origin:
        return True
    return origin in get_allowed_ws_origins()


@dataclass(slots=True)
class WebSocketTaskSession:
    websocket: WebSocket
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pong_event: asyncio.Event = field(default_factory=asyncio.Event)
    closed: bool = False

    async def send_json_message(
        self,
        message: ProgressMessage | AlertMessage | ResultMessage | ErrorMessage | PingMessage | PongMessage,
    ) -> None:
        if self.closed:
            return
        async with self.send_lock:
            await self.websocket.send_json(model_dump(message))

    def mark_pong(self) -> None:
        self.pong_event.set()

    def reset_pong_wait(self) -> None:
        self.pong_event = asyncio.Event()

    async def close(self, code: int, reason: str) -> None:
        if self.closed:
            return
        self.closed = True
        await self.websocket.close(code=code, reason=reason)


async def authenticate_connection(websocket: WebSocket) -> dict:
    try:
        raw_message = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=AUTH_MESSAGE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise WebSocketAuthError("Authentication message timed out") from exc
    except WebSocketDisconnect as exc:
        raise WebSocketAuthError("Client disconnected before authentication") from exc

    if not isinstance(raw_message, dict):
        raise WebSocketAuthError("Expected JSON auth message")

    try:
        auth_message: AuthMessage = parse_auth_message(raw_message)
    except Exception as exc:
        raise WebSocketAuthError("Invalid authentication message") from exc

    try:
        return decode_jwt_token(auth_message.token)
    except HTTPException as exc:
        raise WebSocketAuthError(str(exc.detail)) from exc


async def heartbeat_loop(session: WebSocketTaskSession) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        session.reset_pong_wait()
        await session.send_json_message(PingMessage())
        try:
            await asyncio.wait_for(session.pong_event.wait(), timeout=HEARTBEAT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            await session.close(code=status.WS_1008_POLICY_VIOLATION, reason="Heartbeat timeout")
            raise HeartbeatTimeoutError("No pong received within heartbeat timeout") from exc


async def receive_loop(session: WebSocketTaskSession) -> None:
    while True:
        payload = await session.websocket.receive_json()
        if not isinstance(payload, dict):
            await session.send_json_message(
                ErrorMessage(message="Invalid websocket message payload.", code="invalid_payload")
            )
            continue

        try:
            message = parse_runtime_client_message(payload)
        except Exception:
            await session.send_json_message(
                ErrorMessage(message="Unsupported websocket message type.", code="unsupported_message")
            )
            continue

        if isinstance(message, PingMessage):
            await session.send_json_message(PongMessage())
            continue

        session.mark_pong()


async def run_registered_task(session: WebSocketTaskSession, task_id: str, auth_payload: dict) -> None:
    try:
        handler = resolve_task_handler(task_id)
    except TaskNotRegisteredError as exc:
        await session.send_json_message(
            ErrorMessage(message=str(exc), code="task_not_found")
        )
        raise

    registered_user_id = resolve_registered_user_id_from_auth(auth_payload)
    context = TaskExecutionContext(
        task_id=task_id,
        auth_payload=auth_payload,
        registered_user_id=registered_user_id,
        require_building_access=build_building_access_guard(auth_payload),
        send_progress=session.send_json_message,
        send_alert=session.send_json_message,
        send_result=session.send_json_message,
        send_error=session.send_json_message,
    )

    try:
        await handler(context)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await session.send_json_message(
            ErrorMessage(message="Task execution failed.", code="task_failed")
        )
        raise exc


async def cancel_task(task: asyncio.Task[object] | None) -> None:
    if task is None or task.done():
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def resolve_registered_user_id_from_auth(auth_payload: dict) -> int:
    db: Session = SessionLocal()
    try:
        return resolve_registered_user_id(auth_payload, db)
    finally:
        db.close()


def build_building_access_guard(auth_payload: dict):
    user_id = resolve_registered_user_id_from_auth(auth_payload)

    def _guard(building_id: int) -> int:
        db: Session = SessionLocal()
        try:
            if not has_permission(user_id, "building", building_id, db):
                raise BuildingAccessError("You are not authorized for this building.")
            return user_id
        finally:
            db.close()

    return _guard


@router.websocket("/ws/{task_id}")
async def task_socket(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()

    if not is_allowed_ws_origin(websocket.headers.get("origin")):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return

    try:
        auth_payload = await authenticate_connection(websocket)
    except WebSocketAuthError as exc:
        await websocket.close(code=AUTH_CLOSE_CODE, reason=str(exc))
        return

    session = WebSocketTaskSession(websocket=websocket)
    receiver_task = asyncio.create_task(receive_loop(session), name=f"ws-receiver-{task_id}")
    heartbeat_task = asyncio.create_task(heartbeat_loop(session), name=f"ws-heartbeat-{task_id}")
    worker_task = asyncio.create_task(
        run_registered_task(session, task_id, auth_payload),
        name=f"ws-worker-{task_id}",
    )

    try:
        done, pending = await asyncio.wait(
            {receiver_task, heartbeat_task, worker_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if worker_task in done:
            exc = worker_task.exception()
            if exc is None and not session.closed:
                await session.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Task complete")
            elif exc is not None and not session.closed:
                await session.close(code=status.WS_1011_INTERNAL_ERROR, reason="Task failed")
        elif receiver_task in done:
            receiver_exc = receiver_task.exception()
            if isinstance(receiver_exc, WebSocketDisconnect):
                pass
            elif receiver_exc is not None and not session.closed:
                await session.send_json_message(
                    ErrorMessage(message="WebSocket receive loop failed.", code="receive_failed")
                )
                await session.close(code=status.WS_1011_INTERNAL_ERROR, reason="Receive loop failed")
        elif heartbeat_task in done:
            heartbeat_exc = heartbeat_task.exception()
            if heartbeat_exc and not isinstance(heartbeat_exc, HeartbeatTimeoutError) and not session.closed:
                await session.send_json_message(
                    ErrorMessage(message="Heartbeat loop failed.", code="heartbeat_failed")
                )
                await session.close(code=status.WS_1011_INTERNAL_ERROR, reason="Heartbeat failed")

        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    except WebSocketDisconnect:
        pass
    finally:
        await cancel_task(worker_task)
        await cancel_task(receiver_task)
        await cancel_task(heartbeat_task)
