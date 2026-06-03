"""
growders.core.tenant
─────────────────────
Multi-tenant resolution.

Every request carries a tenant context so the rest of the application
never needs to think about which tenant it's serving — it just reads
from the context variable.

Tenant ID is resolved in this priority order:
  1. X-Tenant-ID header  (API / WhatsApp webhook calls)
  2. Subdomain           (future: tenant.growders.app)
  3. JWT claim           (future: authenticated panel sessions)

Row-Level Security is enforced at the DB layer (see db/session.py).
"""

from contextvars import ContextVar
from uuid import UUID

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ── Context variable ──────────────────────────────────────────────────────────
# Available anywhere in the call stack with no argument threading.
_current_tenant_id: ContextVar[UUID | None] = ContextVar(
    "_current_tenant_id", default=None
)


def get_tenant_id() -> UUID:
    """
    Return the current tenant UUID.
    Raises RuntimeError if called outside a request context (e.g. in a raw
    background task that didn't set the tenant).
    """
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise RuntimeError(
            "No tenant in context. "
            "Ensure TenantMiddleware is registered and the request carries X-Tenant-ID."
        )
    return tenant_id


def set_tenant_id(tenant_id: UUID) -> None:
    """Explicitly set tenant — used in tests and background tasks."""
    _current_tenant_id.set(tenant_id)


# ── Middleware ────────────────────────────────────────────────────────────────
class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant from the incoming request and stores it in context.

    Public paths (health, docs, webhooks with their own auth) are excluded
    so they don't require a tenant header.
    """

    PUBLIC_PATHS: frozenset[str] = frozenset(
        [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/webhooks/whatsapp",   # WhatsApp webhook owns its own auth
        ]
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        tenant_id_str = request.headers.get("X-Tenant-ID")

        if not tenant_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Tenant-ID header.",
            )

        try:
            tenant_uuid = UUID(tenant_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Tenant-ID format. Must be a valid UUID.",
            )

        token = _current_tenant_id.set(tenant_uuid)
        try:
            response = await call_next(request)
        finally:
            _current_tenant_id.reset(token)

        return response


# ── FastAPI dependency ─────────────────────────────────────────────────────────
async def require_tenant(request: Request) -> UUID:
    """
    FastAPI dependency that returns the current tenant UUID.
    Use in routers that need explicit access to the tenant ID.

        @router.get("/items")
        async def list_items(tenant_id: UUID = Depends(require_tenant)):
            ...
    """
    return get_tenant_id()
