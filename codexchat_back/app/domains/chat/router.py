from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.archive_queries import get_conversation, list_conversations, list_messages_for_conversation
from app.db.models import Conversation, Message, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["chat"])

DEFAULT_CONVERSATION_TITLE = "New Conversation"
MAX_TITLE_LENGTH = 255


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)


class ConversationRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=MAX_TITLE_LENGTH)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata_json: dict[str, object]
    created_at: datetime
    archived_at: datetime | None
    is_archived: bool


class ConversationResponse(BaseModel):
    id: str
    title: str
    codex_thread_id: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    is_archived: bool


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


def _normalize_title_or_default(title: str | None) -> str:
    normalized = (title or "").strip()
    if not normalized:
        return DEFAULT_CONVERSATION_TITLE
    return normalized


def _normalize_title_or_error(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Title cannot be empty",
            details={},
        )
    return normalized


def _conversation_to_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        codex_thread_id=conversation.codex_thread_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
        is_archived=conversation.archived_at is not None,
    )


def _message_to_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        metadata_json=message.metadata_json or {},
        created_at=message.created_at,
        archived_at=message.archived_at,
        is_archived=message.archived_at is not None,
    )


@router.get("")
def get_conversations(
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[ConversationResponse]]:
    conversations = list_conversations(db, include_archived=include_archived, limit=200)
    return {
        "conversations": [
            _conversation_to_response(conversation) for conversation in conversations
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreateRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ConversationResponse]:
    conversation = Conversation(title=_normalize_title_or_default(payload.title))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"conversation": _conversation_to_response(conversation)}


@router.get("/{conversation_id}")
def get_conversation_detail(
    conversation_id: UUID,
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ConversationDetailResponse]:
    conversation = get_conversation(
        db,
        conversation_id,
        include_archived=include_archived,
    )
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={},
        )

    messages = list_messages_for_conversation(
        db,
        conversation_id,
        include_archived=include_archived,
    )

    detail = ConversationDetailResponse(
        **_conversation_to_response(conversation).model_dump(),
        messages=[_message_to_response(message) for message in messages],
    )
    return {"conversation": detail}


@router.post("/{conversation_id}/title")
def rename_conversation(
    conversation_id: UUID,
    payload: ConversationRenameRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ConversationResponse]:
    conversation = get_conversation(db, conversation_id, include_archived=False)
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={},
        )

    conversation.title = _normalize_title_or_error(payload.title)
    db.commit()
    db.refresh(conversation)
    return {"conversation": _conversation_to_response(conversation)}
