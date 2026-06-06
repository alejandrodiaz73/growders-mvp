"""
growders.core.tenant
─────────────────────
Multi-tenant resolution.
...
"""

from contextvars import ContextVar
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

_current_tenant_id: ContextVar[UUID | None] = ContextVar(
    "_current_tenant_id", default=None
)


def get_tenant_id() -> UUID:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise RuntimeError(
            "No tenant in context. "
            "Ensure TenantMiddleware is registered and the request carries X-Tenant-ID."
        )
    return tenant_id


def set_tenant_id(tenant_id: UUID) -> None:
    _current_tenant_id.set(tenant_id)


class TenantMiddleware(BaseHTTPMiddleware):

    PUBLIC_PATHS: frozenset[str] = frozenset([
        "/health",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/webhooks/whatsapp",
    ])

    async def dispatch(self, request: Request, call_next) -> Response:
        # OPTIONS preflights never carry X-Tenant-ID; let CORSMiddleware handle them.
        if request.method == "OPTIONS" or request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        tenant_id_str = request.headers.get("X-Tenant-ID")

        if not tenant_id_str:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "missing_tenant",
                    "detail": "Missing X-Tenant-ID header.",
                },
            )

        try:
            tenant_uuid = UUID(tenant_id_str)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_tenant",
                    "detail": "Invalid X-Tenant-ID format. Must be a valid UUID.",
                },
            )

        token = _current_tenant_id.set(tenant_uuid)
        try:
            response = await call_next(request)
        finally:
            _current_tenant_id.reset(token)

        return response


async def require_tenant(request: Request) -> UUID:
    return get_tenant_id()