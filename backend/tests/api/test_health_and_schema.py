"""P0-T04/T05: /health against the migrated test DB; migration creates the
25 tables and the audit append-only trigger."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

EXPECTED_TABLES = {
    "users", "user_sessions", "lender_organizations", "lender_officers",
    "business_profiles", "suppliers", "farming_seasons", "season_cost_items",
    "documents", "debt_facilities", "extraction_drafts", "transactions",
    "financing_requests", "financing_request_items", "forecast_runs",
    "financial_assessments", "news_events", "risk_scenarios", "consents",
    "shared_reports", "lender_reviews", "lender_review_events", "audit_logs",
    "ai_interactions", "applicant_details",
}


def test_health_ok(client) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok", "llm": "disabled"}


def test_migration_creates_25_tables(migrated_db: str) -> None:
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        )).scalars().all()
    engine.dispose()
    assert set(rows) - {"alembic_version"} == EXPECTED_TABLES


def test_audit_logs_is_append_only(clean_db: str) -> None:
    engine = create_engine(clean_db)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO audit_logs (action, outcome) VALUES ('test.append', 'success')"))
    with pytest.raises(DBAPIError, match="append-only"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE audit_logs SET outcome='failure' WHERE action='test.append'"))
    engine.dispose()
