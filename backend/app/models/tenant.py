"""
growders.models.tenant
───────────────────────
Tenant = one business client (e.g. Uniformes Vicky).
Each Tenant has one or more Users (admin panel accounts).

This table is the root of the multi-tenant tree.
It does NOT use TenantMixin (it IS the tenant table).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, _now, _uuid

import enum


class TenantPlan(str, enum.Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(str, enum.Enum):
    DEMO = "demo"
    PILOT = "pilot"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Tenant(AuditMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=_uuid,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    business_type: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))

    plan: Mapped[TenantPlan] = mapped_column(
        Enum(TenantPlan), default=TenantPlan.BASIC, nullable=False
    )
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus), default=TenantStatus.DEMO, nullable=False
    )

    # Conversation limits
    monthly_conversation_limit: Mapped[int] = mapped_column(default=500)
    courtesy_margin: Mapped[int] = mapped_column(default=50)   # extra convos allowed
    conversations_used: Mapped[int] = mapped_column(default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Pilot dates
    pilot_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pilot_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    users: Mapped[list["TenantUser"]] = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant {self.slug} [{self.status}]>"

    @property
    def is_over_limit(self) -> bool:
        hard_limit = self.monthly_conversation_limit + self.courtesy_margin
        return self.conversations_used >= hard_limit

    @property
    def is_in_courtesy(self) -> bool:
        return (
            self.conversations_used >= self.monthly_conversation_limit
            and not self.is_over_limit
        )


class TenantUser(AuditMixin, Base):
    """Admin panel users scoped to a tenant."""
    __tablename__ = "tenant_users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=_uuid,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_tenant_users_tenant_email", "tenant_id", "email"),
    )
