"""Stable error codes + i18n message keys (API spec §1 envelope, §3 codes).

Clients never receive stack traces; they get
{"error": {"code", "message_key", "fields", "request_id", ...extra}}.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("bonik.errors")
_MESSAGE_KEY = re.compile(r"[a-z_]+(\.[a-z_]+)+")


class AppError(Exception):
    def __init__(
        self,
        code: str,
        http_status: int,
        message_key: str | None = None,
        fields: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.message_key = message_key or f"err.{code.lower()}"
        self.fields = fields or {}
        self.extra = extra or {}
        # Commit the request's DB work even though an error is returned
        # (failed-login counters, denied-access audit rows).
        self.commit = commit


def not_found() -> AppError:
    """404 for missing AND not-owned resources (never leak existence)."""
    return AppError("NOT_FOUND", 404, "err.not_found")


def field_error(field: str, key: str) -> AppError:
    return AppError("VALIDATION_ERROR", 422, "err.validation", fields={field: key})


def error_body(
    request: Request,
    code: str,
    message_key: str,
    fields: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    err: dict[str, Any] = {
        "code": code,
        "message_key": message_key,
        "fields": fields or {},
        "request_id": getattr(request.state, "request_id", None),
    }
    if extra:
        err.update(extra)
    return {"error": err}


def _field_name(loc: tuple[Any, ...]) -> str:
    # ("body", "amount") -> "amount"; ("query", "from") -> "from"
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) or "_"


async def _app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=error_body(request, exc.code, exc.message_key, exc.fields, exc.extra),
    )


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(e.get("type") == "json_invalid" for e in errors):
        return JSONResponse(
            status_code=400, content=error_body(request, "BAD_REQUEST", "err.bad_request")
        )
    fields: dict[str, str] = {}
    for e in errors:
        name = _field_name(tuple(e.get("loc", ())))
        # Custom validators may raise ValueError("entry.err.amount") to choose the key.
        msg = str(e.get("msg", "")).removeprefix("Value error, ")
        key = msg if _MESSAGE_KEY.fullmatch(msg) else f"err.field.{e.get('type', 'invalid')}"
        fields.setdefault(name, key)
    return JSONResponse(
        status_code=422, content=error_body(request, "VALIDATION_ERROR", "err.validation", fields)
    )


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        code, key = "NOT_FOUND", "err.not_found"
    elif exc.status_code == 405:
        code, key = "METHOD_NOT_ALLOWED", "err.bad_request"
    else:
        code, key = "BAD_REQUEST", "err.bad_request"
    return JSONResponse(status_code=exc.status_code, content=error_body(request, code, key))


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    if isinstance(exc, DBAPIError):
        # PostgreSQL messages echo values ("Failing row contains (… phone, email …)"): log the code only
        log.error("database error", extra={"request_id": rid, "error": type(exc.orig).__name__,
                                           "sqlstate": getattr(exc.orig, "sqlstate", None)})
    else:
        log.exception("unhandled error", extra={"request_id": rid})
    return JSONResponse(status_code=500, content=error_body(request, "INTERNAL_ERROR", "err.generic"))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled)
