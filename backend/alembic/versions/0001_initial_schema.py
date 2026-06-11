"""initial schema: tenants, conversations, messages, cases

Revision ID: 0001
Revises: 
Create Date: 2026-06-10

Esta migración crea el schema completo del MVP:
  - Extensión pgvector (para Knowledge Base en Sprint 2)
  - Enums de PostgreSQL
  - Tablas: tenants, tenant_users, conversations, messages, cases
  - Índices compuestos para queries tenant-scoped
  - RLS: habilita Row-Level Security en tablas con tenant_id

NOTA: RLS se habilita aquí pero las POLICIES se aplican por tabla.
La policy lee app.current_tenant_id (seteada por session.py antes de cada query).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # ── pgvector extension (PostgreSQL only, needed for Sprint 2 Knowledge Base) ──
    if not is_sqlite:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Enums (PostgreSQL only — SQLite uses VARCHAR) ─────────────────────────
    if not is_sqlite:
        sa.Enum("basic", "professional", "enterprise", name="tenantplan").create(conn)
        sa.Enum("demo", "pilot", "active", "suspended", "archived", name="tenantstatus").create(conn)
        sa.Enum("open", "human_takeover", "closed", "limited", name="conversationstatus").create(conn)
        sa.Enum("user", "assistant", "system", "human_agent", name="messagerole").create(conn)
        sa.Enum("whatsapp", "web_simulator", "voice", name="messagechannel").create(conn)
        sa.Enum("open", "in_progress", "pending_followup", "closed", name="casestatus").create(conn)
        sa.Enum("low", "normal", "high", "urgent", name="casepriority").create(conn)
        sa.Enum(
            "attended", "appointment_booked", "quote_sent", "sale_closed",
            "no_response", "requires_followup", "complaint_resolved",
            "complaint_pending", "lost", "out_of_scope",
            name="caseresult"
        ).create(conn)

    # ── tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("business_type", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column(
            "plan",
            sa.Enum("basic", "professional", "enterprise", name="tenantplan", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
            server_default="basic",
        ),
        sa.Column(
            "status",
            sa.Enum("demo", "pilot", "active", "suspended", "archived", name="tenantstatus", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
            server_default="demo",
        ),
        sa.Column("monthly_conversation_limit", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("courtesy_margin", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("conversations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("pilot_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pilot_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ── tenant_users ──────────────────────────────────────────────────────────
    op.create_table(
        "tenant_users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenant_users_email", "tenant_users", ["email"], unique=True)
    op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])
    op.create_index("ix_tenant_users_tenant_email", "tenant_users", ["tenant_id", "email"])

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_phone", sa.String(30), nullable=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("whatsapp", "web_simulator", "voice", name="messagechannel", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
            server_default="web_simulator",
        ),
        sa.Column(
            "status",
            sa.Enum("open", "human_takeover", "closed", "limited", name="conversationstatus", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
            server_default="open",
        ),
        sa.Column("is_ai_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("session_token", sa.String(100), nullable=True),
        sa.Column("detected_intent", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_tenant_status", "conversations", ["tenant_id", "status"])
    op.create_index("ix_conversations_tenant_phone", "conversations", ["tenant_id", "customer_phone"])
    op.create_index("ix_conversations_session_token", "conversations", ["session_token"])

    # ── messages ──────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", "human_agent", name="messagerole", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_audio_transcription", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    # ── cases ─────────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True) if not is_sqlite else sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "pending_followup", "closed", name="casestatus", create_type=False)
            if not is_sqlite else sa.String(20),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "normal", "high", "urgent", name="casepriority", create_type=False)
            if not is_sqlite else sa.String(10),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "result",
            sa.Enum(
                "attended", "appointment_booked", "quote_sent", "sale_closed",
                "no_response", "requires_followup", "complaint_resolved",
                "complaint_pending", "lost", "out_of_scope",
                name="caseresult", create_type=False,
            ) if not is_sqlite else sa.String(30),
            nullable=True,
        ),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cases_tenant_id", "cases", ["tenant_id"])
    op.create_index("ix_cases_tenant_status_priority", "cases", ["tenant_id", "status", "priority"])

    # ── RLS: habilitar en tablas con tenant_id (PostgreSQL only) ──────────────
    if not is_sqlite:
        for table in ("conversations", "cases", "tenant_users"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                )
            """)


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # Eliminar tablas en orden inverso (respetar FK)
    op.drop_table("cases")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("tenant_users")
    op.drop_table("tenants")

    # Eliminar enums (PostgreSQL only)
    if not is_sqlite:
        for enum_name in [
            "caseresult", "casepriority", "casestatus",
            "messagechannel", "messagerole", "conversationstatus",
            "tenantstatus", "tenantplan",
        ]:
            sa.Enum(name=enum_name).drop(conn)
