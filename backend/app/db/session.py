"""
growders.db.session
────────────────────
Async SQLAlchemy session factory with multi-tenant Row-Level Security.

Two modes (auto-detected from DATABASE_URL):
  - PostgreSQL  → async engine via asyncpg, RLS enforced via SET LOCAL
  - SQLite      → async engine via aiosqlite, tenant filter via app-layer WHERE

Row-Level Security strategy
────────────────────────────
PostgreSQL:
  1. Each table that owns tenant data has a `tenant_id UUID NOT NULL` column.
  2. A PostgreSQL RLS policy (created in migrations) enforces that SELECT /
     INSERT / UPDATE / DELETE only touch rows matching the current tenant.
  3. Before every query we run:
       SET LOCAL app.current_tenant_id = '<uuid>';
  4. The RLS policy references current_setting('app.current_tenant_id').

SQLite (local dev):
  RLS is simulated at the application layer — every query that touches
  tenant-scoped tables must pass tenant_id explicitly. The ORM models
  enforce this via a mixin (see models/base.py).

Callers should always use get_db() as a FastAPI dependency.
Direct engine access is only for migrations and tests.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tenant import get_tenant_id

settings = get_settings()
logger = get_logger(__name__)

# ── Engine factory ────────────────────────────────────────────────────────────

def _make_engine() -> AsyncEngine:
    url = settings.effective_database_url
    is_sqlite = url.startswith("sqlite")

    connect_args: dict = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False

    return create_async_engine(
        url,
        echo=settings.db_echo,
        pool_size=1 if is_sqlite else settings.db_pool_size,
        max_overflow=0 if is_sqlite else settings.db_max_overflow,
        pool_pre_ping=True,          # detect stale connections
        connect_args=connect_args,
    )


engine: AsyncEngine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── RLS helpers ───────────────────────────────────────────────────────────────

async def _set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    For PostgreSQL: set the session-local variable that RLS policies read.
    For SQLite: no-op (tenant filtering is done at the query level).
    """
    url = settings.effective_database_url
    if url.startswith("postgresql"):
        await session.execute(
            # SET LOCAL is transaction-scoped — resets on commit/rollback
            f"SET LOCAL app.current_tenant_id = '{tenant_id}'"  # noqa: S608
        )


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a tenant-scoped async DB session.

    Usage in a router:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    tenant_id = str(get_tenant_id())

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _set_tenant_context(session, tenant_id)
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


# ── Context manager for background tasks ─────────────────────────────────────

@asynccontextmanager
async def get_db_context(tenant_id: str):
    """
    Use this in background tasks / workers that don't go through FastAPI.

    async with get_db_context(str(tenant_id)) as db:
        ...
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _set_tenant_context(session, tenant_id)
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


# ── Init / teardown ───────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables. Called at startup for SQLite; migrations handle Postgres."""
    from app.models.base import Base  # noqa: PLC0415 — avoid circular import at module level

    url = settings.effective_database_url
    if url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite tables created.")
    else:
        logger.info("PostgreSQL detected — run Alembic migrations instead of init_db().")


async def close_db() -> None:
    await engine.dispose()
    logger.info("Database engine disposed.")
