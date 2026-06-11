"""
growders.scripts.seed_demo
───────────────────────────
Inserta el tenant demo (Uniformes Vicky) en la base de datos.

Uso:
    cd backend
    python -m scripts.seed_demo

Variables de entorno requeridas:
    DATABASE_URL — URL de PostgreSQL (Railway la inyecta automáticamente)
    APP_SECRET_KEY — requerida para inicializar Settings

El script es idempotente: si el tenant ya existe, no lo vuelve a crear.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Agregar el directorio backend al path para importar la app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DEMO_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_TENANT_SLUG = "demo"
DEMO_TENANT_NAME = "Uniformes Vicky"


def _get_async_url() -> str:
    """
    Construye URL async para el seed.
    Railway inyecta postgresql:// → corregimos a postgresql+asyncpg://
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. "
            "En local: exporta DATABASE_URL antes de correr el seed."
        )
    url = url.replace("postgres://", "postgresql+asyncpg://")
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    # Si ya tiene el driver correcto, no cambiar
    if not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+", "postgresql+asyncpg://", 1)
    return url


async def seed(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    # Verificar si ya existe
    result = await session.execute(
        text("SELECT id FROM tenants WHERE id = :id"),
        {"id": str(DEMO_TENANT_ID)},
    )
    existing = result.fetchone()

    if existing:
        print(f"✓ Tenant demo ya existe: {DEMO_TENANT_ID}")
        return

    # Insertar con SQL directo para evitar dependencias del ORM en este script
    await session.execute(
        text("""
            INSERT INTO tenants (
                id, name, slug, business_type, city,
                plan, status,
                monthly_conversation_limit, courtesy_margin, conversations_used,
                is_active,
                pilot_started_at, pilot_ends_at,
                created_at, updated_at
            ) VALUES (
                :id, :name, :slug, :business_type, :city,
                :plan, :status,
                :monthly_limit, :courtesy_margin, 0,
                true,
                NULL, NULL,
                :now, :now
            )
        """),
        {
            "id": str(DEMO_TENANT_ID),
            "name": DEMO_TENANT_NAME,
            "slug": DEMO_TENANT_SLUG,
            "business_type": "uniforms",
            "city": "Veracruz",
            "plan": "basic",
            "status": "demo",
            "monthly_limit": 500,
            "courtesy_margin": 50,
            "now": now,
        },
    )

    print(f"✓ Tenant demo creado: {DEMO_TENANT_ID} ({DEMO_TENANT_NAME})")


async def main() -> None:
    url = _get_async_url()
    print(f"Conectando a: {url[:40]}...")

    engine = create_async_engine(url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        async with session.begin():
            await seed(session)

    await engine.dispose()
    print("Seed completado.")


if __name__ == "__main__":
    asyncio.run(main())
