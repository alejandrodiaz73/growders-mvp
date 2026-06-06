"""
growders.core.security
───────────────────────
All HTTP security concerns in one place:
  - CORS
  - Content-Security-Policy
  - Security headers (HSTS, X-Frame-Options, etc.)
  - Trusted host validation
  - Rate limiting helpers

Nothing here changes the business logic.
To tighten or loosen a policy, change this file — not the routers.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()

# ── Rate limiter (shared instance, imported by routers) ───────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ── Security headers middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response.
    CSP is intentionally strict: no inline scripts, no eval.
    Adjust `script-src` only if you add a CDN with a known hash/nonce.
    """

    _CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' https://growders-mvp-production.up.railway.app; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["Content-Security-Policy"] = self._CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"          # let CSP do the job
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # Remove headers that leak server info
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        if "server" in response.headers:
            del response.headers["server"]

        return response


def register_security(app: FastAPI) -> None:
    """
    Attach all security middleware to the FastAPI app.
    Call this once in main.py before registering routers.
    Order matters: TrustedHost → CORS → SecurityHeaders.
    """

    # 1. Trusted host validation (blocks Host header injection)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts,
        )

    # 2. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Tenant-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # 3. Security headers (runs after CORS so CORS headers are preserved)
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Rate limiter exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
