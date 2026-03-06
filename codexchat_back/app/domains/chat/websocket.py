from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select

from app.db.archive_queries import get_conversation
from app.db.models import Message, User
from app.db.session import SessionLocal

logger = logging.getLogger("app.api")


class ResumeEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["resume"]
    conversation_id: UUID


class SendMessageEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["send_message"]
    conversation_id: UUID
    content: str


ClientEvent = ResumeEvent | SendMessageEvent


class ClientEventError(Exception):
    def __init__(self, *, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class RuntimeUnavailableError(Exception):
    pass


class RuntimeExecutionError(Exception):
    pass


def _chunk_text(content: str, *, chunk_size: int = 24) -> list[str]:
    return [content[index : index + chunk_size] for index in range(0, len(content), chunk_size)] or [""]


class MockCodexRuntime:
    """MVP placeholder runtime until Codex bridge integration is implemented."""

    async def stream_assistant_reply(self, *, prompt: str) -> AsyncIterator[str]:
        normalized = prompt.strip()
        lowered = normalized.lower()

        if lowered.startswith("/runtime-unavailable"):
            raise RuntimeUnavailableError("Codex runtime is currently unavailable")
        if lowered.startswith("/runtime-error"):
            raise RuntimeExecutionError("Codex runtime failed while processing the turn")

        response = f"MVP stream placeholder response:\n{normalized}"
        for chunk in _chunk_text(response):
            await asyncio.sleep(0.04)
            yield chunk


@dataclass(slots=True)
class ActiveTurn:
    task: asyncio.Task[None]
    owner_user_id: UUID


class ChatWebSocketService:
    def __init__(self) -> None:
        self._runtime = MockCodexRuntime()
        self._state_lock = asyncio.Lock()
        self._subscriptions: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._socket_subscriptions: dict[WebSocket, set[UUID]] = defaultdict(set)
        self._active_turns: dict[UUID, ActiveTurn] = {}
        self._turn_timeout_seconds = 45

    async def handle_connection(self, websocket: WebSocket, *, user: User) -> None:
        request_id = websocket.headers.get("x-request-id") or str(uuid4())
        await websocket.accept()
        logger.info(
            "websocket_connected",
            extra={
                "event_data": {
                    "user_id": str(user.id),
                    "request_id": request_id,
                }
            },
        )

        try:
            while True:
                payload_text = await websocket.receive_text()
                try:
                    event = _parse_client_event(payload_text)
                except ClientEventError as exc:
                    await self._send_error(
                        websocket,
                        code=exc.code,
                        message=exc.message,
                        details=exc.details,
                    )
                    continue

                if isinstance(event, ResumeEvent):
                    await self._handle_resume(websocket, event=event)
                    continue

                await self._handle_send_message(websocket, user=user, event=event)
        except WebSocketDisconnect:
            logger.info(
                "websocket_disconnected",
                extra={"event_data": {"user_id": str(user.id), "request_id": request_id}},
            )
        finally:
            await self._unsubscribe_socket(websocket)

    async def _handle_resume(self, websocket: WebSocket, *, event: ResumeEvent) -> None:
        conversation_id = event.conversation_id
        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                await self._send_error(
                    websocket,
                    code="NOT_FOUND",
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
                return

            latest_assistant_message = db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == "assistant",
                    Message.archived_at.is_(None),
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()

        await self._subscribe_socket_to_conversation(websocket, conversation_id)

        if latest_assistant_message is not None:
            await self._send_json(
                websocket,
                {
                    "type": "assistant_done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(latest_assistant_message.id),
                    "content": latest_assistant_message.content,
                },
            )

    async def _handle_send_message(
        self,
        websocket: WebSocket,
        *,
        user: User,
        event: SendMessageEvent,
    ) -> None:
        conversation_id = event.conversation_id
        content = event.content.strip()
        if not content:
            await self._send_error(
                websocket,
                code="VALIDATION_ERROR",
                message="Message content cannot be empty",
                details={"conversation_id": str(conversation_id)},
            )
            return

        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                await self._send_error(
                    websocket,
                    code="NOT_FOUND",
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
                return

        await self._subscribe_socket_to_conversation(websocket, conversation_id)

        is_busy = False
        async with self._state_lock:
            if conversation_id in self._active_turns:
                is_busy = True
            else:
                task = asyncio.create_task(
                    self._run_turn(
                        conversation_id=conversation_id,
                        user_id=user.id,
                        content=content,
                    )
                )
                self._active_turns[conversation_id] = ActiveTurn(task=task, owner_user_id=user.id)

        if is_busy:
            await self._send_error(
                websocket,
                code="THREAD_BUSY",
                message="Conversation is already processing a turn",
                details={"conversation_id": str(conversation_id), "busy": True},
            )
            return

    async def _run_turn(self, *, conversation_id: UUID, user_id: UUID, content: str) -> None:
        assistant_content = ""
        try:
            with SessionLocal() as db:
                db.add(
                    Message(
                        conversation_id=conversation_id,
                        role="user",
                        content=content,
                    )
                )
                db.commit()

            try:
                async with asyncio.timeout(self._turn_timeout_seconds):
                    async for delta in self._runtime.stream_assistant_reply(prompt=content):
                        assistant_content += delta
                        await self._broadcast_to_conversation(
                            conversation_id,
                            {
                                "type": "assistant_delta",
                                "conversation_id": str(conversation_id),
                                "delta": delta,
                            },
                        )
            except TimeoutError:
                await self._broadcast_error(
                    conversation_id,
                    code="CODEX_TIMEOUT",
                    message="Codex runtime timed out",
                )
                return
            except RuntimeUnavailableError as exc:
                await self._broadcast_error(
                    conversation_id,
                    code="CODEX_UNAVAILABLE",
                    message=str(exc),
                )
                return
            except RuntimeExecutionError as exc:
                await self._broadcast_error(
                    conversation_id,
                    code="CODEX_RUNTIME_ERROR",
                    message=str(exc),
                )
                return

            with SessionLocal() as db:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                )
                db.add(assistant_message)
                db.commit()
                db.refresh(assistant_message)

            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "assistant_done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(assistant_message.id),
                    "content": assistant_content,
                },
            )
        except Exception:
            logger.exception(
                "websocket_turn_runtime_failure",
                extra={"event_data": {"conversation_id": str(conversation_id), "user_id": str(user_id)}},
            )
            await self._broadcast_error(
                conversation_id,
                code="CODEX_RUNTIME_ERROR",
                message="Codex runtime failed while processing the turn",
            )
        finally:
            async with self._state_lock:
                self._active_turns.pop(conversation_id, None)

    async def _send_error(
        self,
        websocket: WebSocket,
        *,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        payload = {
            "type": "error",
            "code": code,
            "message": message,
            "details": details or {},
        }
        await self._send_json(websocket, payload)

    async def _broadcast_error(self, conversation_id: UUID, *, code: str, message: str) -> None:
        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "error",
                "conversation_id": str(conversation_id),
                "code": code,
                "message": message,
                "details": {
                    "conversation_id": str(conversation_id),
                    "busy": False,
                },
            },
        )

    async def _send_json(self, websocket: WebSocket, payload: dict[str, object]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            await self._unsubscribe_socket(websocket)

    async def _broadcast_to_conversation(self, conversation_id: UUID, payload: dict[str, object]) -> None:
        async with self._state_lock:
            subscribers = list(self._subscriptions.get(conversation_id, set()))

        for socket in subscribers:
            await self._send_json(socket, payload)

    async def _subscribe_socket_to_conversation(self, websocket: WebSocket, conversation_id: UUID) -> None:
        async with self._state_lock:
            self._subscriptions[conversation_id].add(websocket)
            self._socket_subscriptions[websocket].add(conversation_id)

    async def _unsubscribe_socket(self, websocket: WebSocket) -> None:
        async with self._state_lock:
            conversations = self._socket_subscriptions.pop(websocket, set())
            for conversation_id in conversations:
                subscribers = self._subscriptions.get(conversation_id)
                if subscribers is None:
                    continue
                subscribers.discard(websocket)
                if not subscribers:
                    self._subscriptions.pop(conversation_id, None)


def _normalize_client_payload(raw_payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(raw_payload)
    if "conversation_id" not in normalized and "conversationId" in normalized:
        normalized["conversation_id"] = normalized["conversationId"]
    return normalized


def _parse_client_event(payload_text: str) -> ClientEvent:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ClientEventError(
            code="INVALID_JSON",
            message="WebSocket payload must be valid JSON",
            details={"error": str(exc)},
        ) from exc

    if not isinstance(payload, dict):
        raise ClientEventError(
            code="VALIDATION_ERROR",
            message="WebSocket payload must be an object",
            details={},
        )

    normalized = _normalize_client_payload(payload)
    event_type = normalized.get("type")
    try:
        if event_type == "resume":
            return ResumeEvent.model_validate(normalized)
        if event_type == "send_message":
            return SendMessageEvent.model_validate(normalized)
    except ValidationError as exc:
        raise ClientEventError(
            code="VALIDATION_ERROR",
            message="WebSocket payload validation failed",
            details={"errors": exc.errors()},
        ) from exc

    raise ClientEventError(
        code="BAD_EVENT_TYPE",
        message="Unsupported websocket event type",
        details={"allowed_types": ["send_message", "resume"]},
    )


chat_websocket_service = ChatWebSocketService()
