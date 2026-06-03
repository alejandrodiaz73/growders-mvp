"""
growders.main
──────────────
FastAPI application factory.

Middleware registration order (outermost → innermost):
  TrustedHost → CORS → SecurityHeaders → TenantMiddleware → Routers

Startup / shutdown lifecycle:
  startup  → init DB (SQLite) or verify connection (Postgres)
  shutdown → close DB pool and cache connections
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import register_security
from app.core.tenant import TenantMiddleware
from app.db.session import close_db, init_db
from app.services.cache import close_cache

settings = get_settings()
logger = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Starting Growders MVP [env=%s]", settings.app_env)
    await init_db()
    logger.info("Database ready.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────
    await close_db()
    await close_cache()
    logger.info("Growders MVP shutdown complete.")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Growders MVP API",
        version="0.1.0",
        description="AI commercial assistant for SMBs",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # 1. Security middleware (CORS, CSP, headers, trusted hosts)
    register_security(app)

    # 2. Tenant resolution middleware
    app.add_middleware(TenantMiddleware)

    # 3. Routers
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    from app.api.health import router as health_router
    from app.api.chat import router as chat_router

    app.include_router(health_router)
    app.include_router(chat_router, prefix="/api/v1")

    # Future routers (uncomment as built):
    # from app.api.tenants import router as tenants_router
    # from app.api.knowledge import router as knowledge_router
    # from app.api.cases import router as cases_router
    # from app.api.orders import router as orders_router
    # from app.api.calendar import router as calendar_router
    # from app.api.webhooks import router as webhooks_router
    # app.include_router(tenants_router, prefix="/api/v1")
    # app.include_router(knowledge_router, prefix="/api/v1")
    # app.include_router(cases_router, prefix="/api/v1")
    # app.include_router(orders_router, prefix="/api/v1")
    # app.include_router(calendar_router, prefix="/api/v1")
    # app.include_router(webhooks_router, prefix="/api/v1")


app = create_app()
