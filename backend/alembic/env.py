"""
growders.alembic.env
─────────────────────
Alembic environment for async SQLAlchemy (asyncpg / PostgreSQL).

Cómo funciona:
  - Lee DATABASE_URL desde variable de entorno (igual que la app).
  - Si DATABASE_URL está vacío → usa SQLite como fallback (solo para tests locales).
  - Alembic necesita un engine SÍNCRONO → usa psycopg2 para PostgreSQL,
    pysqlite para SQLite. Esto es correcto: las migraciones no son async.
  - Los modelos se importan aquí para que Alembic detecte cambios automáticamente
    con `alembic revision --autogenerate`.

NUNCA cambiar sqlalchemy.url en alembic.ini — toda la config viene de aquí.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Importar Base y todos los modelos ─────────────────────────────────────────
# Importar Base primero, luego cada modelo para que Alembic los detecte.
# Si agregas un modelo nuevo, importarlo aquí.
from app.models.base import Base  # noqa: F401
from app.models.tenant import Tenant, TenantUser  # noqa: F401
from app.models.conversation import Conversation, Message, Case  # noqa: F401

target_metadata = Base.metadata

# ── Logging ───────────────────────────────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ── URL del engine síncrono para migraciones ─────────────────────────────────

def _get_sync_url() -> str:
    """
    Construye la URL síncrona para Alembic a partir de DATABASE_URL.

    Railway inyecta:  postgresql://user:pass@host/db
    La app corrige a: postgresql+asyncpg://...  (async)
    Alembic necesita: postgresql+psycopg2://... (sync)

    Para SQLite (dev local):
      sqlite+aiosqlite:///./data/growders.db  →  sqlite:///./data/growders.db
    """
    url = os.environ.get("DATABASE_URL", "")

    if not url:
        # Fallback SQLite para entorno local sin DATABASE_URL
        return "sqlite:///./data/growders.db"

    # Normalizar esquemas de Railway/asyncpg → psycopg2
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    url = url.replace("postgres://", "postgresql+psycopg2://")
    url = url.replace("postgresql://", "postgresql+psycopg2://")

    # Normalizar esquema async SQLite → síncrono
    url = url.replace("sqlite+aiosqlite://", "sqlite://")

    return url


def run_migrations_offline() -> None:
    """
    Modo offline: genera SQL sin conectarse a la base de datos.
    Útil para revisar qué SQL se va a ejecutar antes de aplicarlo.
    Correr con: alembic upgrade head --sql
    """
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Incluir esquema de enums para PostgreSQL
        include_schemas=False,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: se conecta a la DB y aplica migraciones directamente.
    Es el modo que usa Railway en cada deploy.
    """
    url = _get_sync_url()

    # Para SQLite usar StaticPool — evita errores de threading en tests
    is_sqlite = url.startswith("sqlite")
    poolclass = pool.StaticPool if is_sqlite else pool.NullPool

    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=poolclass,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # detecta cambios de tipo en columnas
            compare_server_default=True, # detecta cambios en defaults del servidor
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
