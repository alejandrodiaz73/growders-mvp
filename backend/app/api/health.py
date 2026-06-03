"""
growders.api.health
────────────────────
Public health endpoints — no tenant, no auth required.
Used by Railway / Render for health checks and by load balancers.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services.cache import get_cache

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    """Minimal liveness probe — returns 200 if the process is up."""
    return JSONResponse({"status": "ok", "env": settings.app_env})


@router.get("/health/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    """
    Readiness probe — checks that dependencies (DB, cache) are reachable.
    Returns 503 if any dependency is unavailable.
    """
    checks: dict[str, str] = {}
    ok = True

    # Cache check
    try:
        cache = get_cache()
        await cache.set("__health__", "1", ttl=5)
        val = await cache.get("__health__")
        checks["cache"] = "ok" if val == "1" else "error"
    except Exception as exc:
        checks["cache"] = f"error: {exc}"
        ok = False

    # DB check (simple import — full ping would require a session)
    try:
        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"
        ok = False

    status_code = 200 if ok else 503
    return JSONResponse(
        {"status": "ready" if ok else "degraded", "checks": checks},
        status_code=status_code,
    )
