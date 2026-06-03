"""
growders.models.conversation
─────────────────────────────
Core entities for the WhatsApp assistant:

  Conversation  — one thread between a customer and the assistant
  Message       — individual message within a conversation
  Case          — escalation / human-in-the-loop ticket

Index strategy:
  - tenant_id is indexed on every table (via TenantMixin)
  - Composite indexes added for the most common query patterns:
      * conversations by tenant + status
      * messages by conversation + created_at (pagination)
      * cases by tenant + status + priority
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, TenantMixin, _uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    HUMAN_TAKEOVER = "human_takeover"
    CLOSED = "closed"
    LIMITED = "limited"      # tenant over conversation limit


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    HUMAN_AGENT = "human_agent"


class MessageChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    WEB_SIMULATOR = "web_simulator"
    VOICE = "voice"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_FOLLOWUP = "pending_followup"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"       # auto-set on complaint detection


class CaseResult(str, enum.Enum):
    ATTENDED = "attended"
    APPOINTMENT_BOOKED = "appointment_booked"
    QUOTE_SENT = "quote_sent"
    SALE_CLOSED = "sale_closed"
    NO_RESPONSE = "no_response"
    REQUIRES_FOLLOWUP = "requires_followup"
    COMPLAINT_RESOLVED = "complaint_resolved"
    COMPLAINT_PENDING = "complaint_pending"
    LOST = "lost"
    OUT_OF_SCOPE = "out_of_scope"


# ── Models ────────────────────────────────────────────────────────────────────

class Conversation(TenantMixin, AuditMixin, Base):
    __tablename__ = "conversations"

    # Customer identity (no PII beyond what's needed)
    customer_phone: Mapped[str | None] = mapped_column(String(30), index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[MessageChannel] = mapped_column(
        Enum(MessageChannel), default=MessageChannel.WEB_SIMULATOR, nullable=False
    )

    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.OPEN, nullable=False
    )
    is_ai_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Session token (for web simulator, maps to sessionStorage key)
    session_token: Mapped[str | None] = mapped_column(String(100), index=True)

    # Detected intent / topic of the conversation
    detected_intent: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
        lazy="select",
    )
    cases: Mapped[list["Case"]] = relationship(back_populates="conversation")

    __table_args__ = (
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
        Index("ix_conversations_tenant_phone", "tenant_id", "customer_phone"),
    )


class Message(AuditMixin, Base):
    """
    Individual message within a conversation.
    Does NOT use TenantMixin — tenant is resolved via conversation FK.
    Access is always through a Conversation, so tenant isolation is inherited.
    """
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=_uuid,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_audio_transcription: Mapped[bool] = mapped_column(Boolean, default=False)

    # LLM metadata (for cost tracking and debugging)
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class Case(TenantMixin, AuditMixin, Base):
    """
    A case is created whenever human intervention is needed.
    It tracks the full lifecycle of human-in-the-loop resolution.
    """
    __tablename__ = "cases"

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), default=CaseStatus.OPEN, nullable=False
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority), default=CasePriority.NORMAL, nullable=False
    )
    result: Mapped[CaseResult | None] = mapped_column(Enum(CaseResult), nullable=True)

    subject: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)      # AI-generated context
    resolution_note: Mapped[str | None] = mapped_column(Text)

    assigned_to: Mapped[str | None] = mapped_column(String(255))  # user email

    conversation: Mapped["Conversation | None"] = relationship(back_populates="cases")

    __table_args__ = (
        Index("ix_cases_tenant_status_priority", "tenant_id", "status", "priority"),
    )
