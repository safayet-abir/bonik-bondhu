"""HTTP middleware: request id + JSON access log, security headers
(Security doc §1), CSRF header check (SUG-04).

Execution order (outermost first): CORS -> request id/log -> security
headers -> CSRF -> routes. Security headers therefore also apply to CSRF
rejections.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from ..config import Settings
from .errors import error_body

log = logging.getLogger("bonik.access")

API_PREFIX = "/api/"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "X-BB-Client"
CSRF_VALUE = "web"
CSP = (
    "default-src 'self'; img-src 'self' blob: data:; object-src 'none'; "
    "frame-ancestors 'none'"
)

Handler = Callable[[Request], Awaitable[Response]]


def install_middleware(app: FastAPI, settings: Settings) -> None:
    # Starlette runs the LAST registered middleware first, so register
    # innermost (CSRF) first and outermost (request id) last.

    @app.middleware("http")
    async def csrf_header_check(request: Request, call_next: Handler) -> Response:
        if (
            request.url.path.startswith(API_PREFIX)
            and request.method not in SAFE_METHODS
            and request.headers.get(CSRF_HEADER) != CSRF_VALUE
        ):
            return JSONResponse(
                status_code=403,
                content=error_body(request, "CSRF_HEADER_MISSING", "err.csrf_header_missing"),
            )
        return await call_next(request)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Handler) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Content-Security-Policy", CSP)
        if settings.is_production:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith(API_PREFIX):
            h["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def request_id_and_log(request: Request, call_next: Handler) -> Response:
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        # Never log bodies, tokens, phones or AI content (Security T17).
        log.info(
            "request",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
        return response
