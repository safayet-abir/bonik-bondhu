"""App-shell behaviour that needs no database: CSRF (SEC-16), security
headers, error envelope."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_post_without_csrf_header_is_rejected() -> None:  # SEC-16
    r = _client().post("/api/v1/health", json={})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CSRF_HEADER_MISSING"
    assert r.json()["error"]["request_id"]
    # Security headers also apply to CSRF rejections
    assert r.headers["X-Frame-Options"] == "DENY"


def test_unknown_api_route_uses_error_envelope() -> None:
    r = _client().get("/api/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()["error"]
    assert body["code"] == "NOT_FOUND" and body["message_key"] == "err.not_found"


def test_security_headers_and_no_store_on_api() -> None:
    r = _client().get("/api/v1/does-not-exist")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "same-origin"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in r.headers  # only in production


def test_openapi_is_under_api_prefix() -> None:
    assert _client().get("/api/v1/openapi.json").status_code == 200
