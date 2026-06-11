"""initial schema: tenants, conversations, messages, cases

Revision ID: 0001
Revises: 
Create Date: 2026-06-10

Crea el schema completo del MVP.

NOTA: Usa IF NOT EXISTS en todas las operaciones para ser idempotente.
El deploy anterior (sin Alembic) ya creó algunos tipos/tablas via init_db().
Esta migración es segura de correr aunque esos objetos ya existan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enums necesarios con sus valores
ENUMS = [
    ("tenantplan",    ["basic", "professional", "enterprise"]),
    ("tenantstatus",  ["demo", "pilot", "active", "suspended", "archived"]),
    ("conversationstatus", ["open", "human_takeover", "closed", "limited"]),
    ("messagerole",   ["user", "assistant", "system", "human_agent"]),
    ("messagechannel",["whatsapp", "web_simulator", "voice"]),
    ("casestatus",    ["open", "in_progress", "pending_followup", "closed"]),
    ("casepriority",  ["low", "normal", "high", "urgent"]),
    ("caseresult",    [
        "attended", "appointment_booked", "quote_sent", "sale_closed",
        "no_response", "requires_followup", "complaint_resolved",
        "complaint_pending", "lost", "out_of_scope",
    ]),
]


def _enum_type(name: str, is_sqlite: bool):
    """Devuelve el tipo correcto según el motor."""
    if is_sqlite:
        return sa.String(30)
    return sa.Enum(name=name, create_type=False)


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # ── pgvector (PostgreSQL only) ─────────────────────────────────────────
    if not is_sqlite:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Enums (PostgreSQL only) ────────────────────────────────────────────
    # CREATE TYPE IF NOT EXISTS es seguro aunque el tipo ya exista
    if not is_sqlite:
        for enum_name, values in ENUMS:
            quoted = ", ".join(f"'{v}'" for v in values)
            op.execute(
                f"DO $$ BEGIN "
                f"  CREATE TYPE {enum_name} AS ENUM ({quoted}); "
                f"EXCEPTION WHEN duplicate_object THEN NULL; "
                f"END $$"
            )

    # ── tenants ───────────────────────────────────────────────────────────
    if not _table_exists(conn, "tenants"):
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
            sa.Column("plan", _enum_type("tenantplan", is_sqlite),
                      nullable=False, server_default="basic"),
            sa.Column("status", _enum_type("tenantstatus", is_sqlite),
                      nullable=False, server_default="demo"),
            sa.Column("monthly_conversation_limit", sa.Integer(),
                      nullable=False, server_default="500"),
            sa.Column("courtesy_margin", sa.Integer(),
                      nullable=False, server_default="50"),
            sa.Column("conversations_used", sa.Integer(),
                      nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(),
                      nullable=False, server_default="true"),
            sa.Column("pilot_started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pilot_ends_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ── tenant_users ──────────────────────────────────────────────────────
    if not _table_exists(conn, "tenant_users"):
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
        op.create_index("ix_tenant_users_tenant_email", "tenant_users",
                        ["tenant_id", "email"])

    # ── conversations ─────────────────────────────────────────────────────
    if not _table_exists(conn, "conversations"):
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
            sa.Column("channel", _enum_type("messagechannel", is_sqlite),
                      nullable=False, server_default="web_simulator"),
            sa.Column("status", _enum_type("conversationstatus", is_sqlite),
                      nullable=False, server_default="open"),
            sa.Column("is_ai_paused", sa.Boolean(),
                      nullable=False, server_default="false"),
            sa.Column("session_token", sa.String(100), nullable=True),
            sa.Column("detected_intent", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
        op.create_index("ix_conversations_tenant_status", "conversations",
                        ["tenant_id", "status"])
        op.create_index("ix_conversations_tenant_phone", "conversations",
                        ["tenant_id", "customer_phone"])
        op.create_index("ix_conversations_session_token", "conversations",
                        ["session_token"])

    # ── messages ──────────────────────────────────────────────────────────
    if not _table_exists(conn, "messages"):
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
            sa.Column("role", _enum_type("messagerole", is_sqlite), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("is_audio_transcription", sa.Boolean(),
                      nullable=False, server_default="false"),
            sa.Column("llm_provider", sa.String(50), nullable=True),
            sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_messages_conversation_created", "messages",
                        ["conversation_id", "created_at"])

    # ── cases ─────────────────────────────────────────────────────────────
    if not _table_exists(conn, "cases"):
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
            sa.Column("status", _enum_type("casestatus", is_sqlite),
                      nullable=False, server_default="open"),
            sa.Column("priority", _enum_type("casepriority", is_sqlite),
                      nullable=False, server_default="normal"),
            sa.Column("result", _enum_type("caseresult", is_sqlite), nullable=True),
            sa.Column("subject", sa.String(255), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column("assigned_to", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_cases_tenant_id", "cases", ["tenant_id"])
        op.create_index("ix_cases_tenant_status_priority", "cases",
                        ["tenant_id", "status", "priority"])

    # ── RLS (PostgreSQL only) ─────────────────────────────────────────────
    if not is_sqlite:
        for table in ("conversations", "cases", "tenant_users"):
            # Habilitar RLS solo si no está ya habilitado
            op.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
                EXCEPTION WHEN others THEN NULL;
                END $$
            """)
            # Crear policy solo si no existe
            op.execute(f"""
                DO $$ BEGIN
                    CREATE POLICY tenant_isolation ON {table}
                    USING (
                        tenant_id = current_setting('app.current_tenant_id', true)::uuid
                    );
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$
            """)


def _table_exists(conn, table_name: str) -> bool:
    """Verifica si una tabla ya existe en la base de datos."""
    if conn.dialect.name == "sqlite":
        result = conn.execute(
            sa.text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=:name"
            ),
            {"name": table_name},
        )
    else:
        result = conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname='public' AND tablename=:name"
            ),
            {"name": table_name},
        )
    return result.fetchone() is not None


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    for table in ["cases", "messages", "conversations", "tenant_users", "tenants"]:
        if _table_exists(conn, table):
            op.drop_table(table)

    if not is_sqlite:
        for enum_name, _ in reversed(ENUMS):
            op.execute(
                f"DO $$ BEGIN DROP TYPE {enum_name}; "
                f"EXCEPTION WHEN undefined_object THEN NULL; END $$"
            )
