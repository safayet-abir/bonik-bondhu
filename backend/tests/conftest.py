"""Shared fixtures.

DB tests run against TEST_DATABASE_URL (never DATABASE_URL): the session
fixture drops and recreates the `public` schema there and runs `alembic
upgrade head`; every DB test then starts from empty tables. If
TEST_DATABASE_URL is unset or unreachable, DB tests are skipped with a clear
reason (they are still required by the phase gates).
"""
from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]

_base = Settings()
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or _base.TEST_DATABASE_URL

# Point the app at the test DB before anything builds an engine.
if TEST_DB_URL:
    os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["APP_ENV"] = "test"
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("SECRET_SALT", "test-salt")
get_settings.cache_clear()

TABLES = (
    "ai_interactions, audit_logs, lender_review_events, lender_reviews, shared_reports, "
    "consents, risk_scenarios, news_events, financial_assessments, forecast_runs, "
    "financing_request_items, financing_requests, transactions, extraction_drafts, "
    "debt_facilities, documents, season_cost_items, farming_seasons, suppliers, "
    "business_profiles, lender_officers, lender_organizations, user_sessions, users"
)


def _reset_caches() -> None:
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[str]:
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set (see backend/.env.example)")
    engine = create_engine(TEST_DB_URL, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    except OperationalError as exc:
        pytest.skip(f"test database unreachable: {exc.orig}")
    finally:
        engine.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = TEST_DB_URL
    command.upgrade(cfg, "head")
    _reset_caches()
    yield TEST_DB_URL


@pytest.fixture()
def clean_db(migrated_db: str) -> Iterator[str]:
    """Empty tables, fresh rate limiter, real clock — for every DB test.
    (TRUNCATE does not fire the audit_logs row trigger, so it is allowed.)"""
    from app.core import clock
    from app.core.rate_limit import auth_ip_limiter

    engine = create_engine(migrated_db, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    engine.dispose()
    auth_ip_limiter.reset()
    clock.set_now(None)
    yield migrated_db
    clock.set_now(None)


@pytest.fixture()
def make_client(clean_db: str) -> Iterator[Callable[[], "TestClient"]]:  # noqa: F821
    """Factory: each call returns an independent browser (own cookie jar)."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    _reset_caches()
    app = create_app()
    clients: list[TestClient] = []

    def factory() -> TestClient:
        c = TestClient(app, headers={"X-BB-Client": "web"})
        clients.append(c)
        return c

    yield factory
    for c in clients:
        c.close()


@pytest.fixture()
def client(make_client: Callable[[], "TestClient"]) -> "TestClient":  # noqa: F821
    return make_client()
