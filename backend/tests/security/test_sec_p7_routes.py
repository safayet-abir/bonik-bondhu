"""P7-T04 security checklist, made permanent: walk every API route of the real app and check
its dependency tree, so a new route that forgets the ownership / role guard fails CI.
  * every route with {pid} depends on get_owned_profile (404 for other owners) and is owner-only
  * every /lender/ route depends on require_lender
  * every other route needs a session, except the public ones listed here"""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.core.deps import current_session, get_owned_profile, require_lender, require_owner
from app.main import create_app

PUBLIC = {("GET", "/api/v1/health"), ("POST", "/api/v1/auth/register"), ("POST", "/api/v1/auth/login"),
          ("POST", "/api/v1/auth/logout"), ("GET", "/api/v1/auth/me")}


def _calls(dependant) -> set:
    out = set()
    for d in dependant.dependencies:
        out.add(d.call)
        out |= _calls(d)
    return out


def _api_routes():
    for r in create_app().routes:
        router = getattr(r, "original_router", None)
        for route in getattr(router, "routes", []):
            if isinstance(route, APIRoute):
                for method in route.methods:
                    yield method, "/api/v1" + route.path, _calls(route.dependant)


def test_database_errors_are_logged_without_values(clean_db) -> None:
    """Checklist "logs: no phones/emails": PostgreSQL error text repeats the row values."""
    import asyncio
    import logging

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from starlette.requests import Request

    from app.core.errors import _unhandled
    from app.db import get_engine
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT CAST(:p AS int)"), {"p": "+8801712345678 secret@example.com"})
    except DBAPIError as exc:
        error = exc
    assert "secret@example.com" in str(error)  # the raw error does carry the value …
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append
    logger = logging.getLogger("bonik.errors")
    logger.addHandler(handler)
    try:
        response = asyncio.run(_unhandled(Request({"type": "http", "headers": [], "state": {}}), error))
    finally:
        logger.removeHandler(handler)
    assert response.status_code == 500
    logged = " ".join(f"{r.getMessage()} {r.__dict__}" for r in records)
    assert records and "secret@example.com" not in logged and "8801712345678" not in logged  # … the log does not


def test_production_refuses_to_start_without_secret_salt(monkeypatch) -> None:
    import pytest

    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "APP_ENV", "production")
    monkeypatch.setattr(get_settings(), "SECRET_SALT", "")
    with pytest.raises(RuntimeError, match="SECRET_SALT"):
        create_app()
    monkeypatch.setattr(get_settings(), "SECRET_SALT", "a" * 32)
    create_app()  # starts once the salt is set


def test_every_route_has_its_guard() -> None:
    routes = list(_api_routes())
    assert len(routes) >= 58  # the API spec lists 58 endpoints (+ a few documented extras)
    problems = []
    for method, path, calls in routes:
        if "{pid}" in path and get_owned_profile not in calls:
            problems.append(f"{method} {path}: no get_owned_profile")
        elif path.startswith("/api/v1/lender/") and require_lender not in calls:
            problems.append(f"{method} {path}: no require_lender")
        elif (method, path) not in PUBLIC and current_session not in calls:
            problems.append(f"{method} {path}: no session check")
        if "{pid}" in path and require_owner not in calls:
            problems.append(f"{method} {path}: not owner-only")
    assert problems == []
