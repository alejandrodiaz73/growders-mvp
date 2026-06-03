"""
growders.models.base
─────────────────────
Base classes for all SQLAlchemy models.

TenantMixin
  Every table that stores business data must inherit this mixin.
  It adds a `tenant_id` column and an index so tenant-scoped
  queries never do full-table scans.

AuditMixin
  Adds created_at / updated_at with automatic timestamps.

All models should inherit from both:
    class MyModel(TenantMixin, AuditMixin, Base): ...
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    """Declarative base — imported by all models and by Alembic env.py."""
    pass


# ── Mixins ────────────────────────────────────────────────────────────────────

class UUIDPrimaryKeyMixin:
    """UUID primary key — database-agnostic."""
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=_uuid,
        server_default=text("gen_random_uuid()"),
    )


class TenantMixin(UUIDPrimaryKeyMixin):
    """
    Adds tenant_id to every business table.

    Indexed individually so `WHERE tenant_id = $1` is always fast.
    Composite indexes (tenant_id + other columns) should be added in
    the concrete model when queries filter on multiple columns.
    """
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        nullable=False,
        index=True,
    )

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Ensure the composite index is created for tenant_id on each table
        table_name = getattr(cls, "__tablename__", None)
        if table_name:
            Index(
                f"ix_{table_name}_tenant_id",
                "tenant_id",
            )


class AuditMixin:
    """Automatic created_at / updated_at timestamps (UTC)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
