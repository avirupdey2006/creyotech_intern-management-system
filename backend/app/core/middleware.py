import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import structlog

from app.core.logging import pino_logger


def get_client_ip(request: Request) -> str:
    """Extracts client IP from Cloudflare/Nginx X-Forwarded-For or fallback client host."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class SecurityAndPinoLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enforces OWASP Top 10 security headers (CSP, HSTS, X-Frame-Options) per Section 3.1
    and emits structured Pino access logs with latency and correlation IDs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        client_ip = get_client_ip(request)
        start_time = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            req_id=req_id,
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            pino_logger.error(
                "Unhandled request exception",
                status_code=500,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Mandatory OWASP Security Headers (Specification Section 2 & 3.1)
        response.headers["X-Request-ID"] = req_id
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        pino_logger.info(
            "HTTP request completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response