"""Initial schema: executes db/schema.sql (24 tables, DB doc §7 step 1).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-14
"""
from __future__ import annotations

import re
from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

# Reverse FK order; used only by downgrade.
TABLES = [
    "ai_interactions", "audit_logs", "lender_review_events", "lender_reviews",
    "shared_reports", "consents", "risk_scenarios", "news_events",
    "financial_assessments", "forecast_runs", "financing_request_items",
    "financing_requests", "transactions", "extraction_drafts", "debt_facilities",
    "documents", "season_cost_items", "farming_seasons", "suppliers",
    "business_profiles", "lender_officers", "lender_organizations",
    "user_sessions", "users",
]


def _schema_body() -> str:
    """schema.sql wraps itself in BEGIN/COMMIT; Alembic already runs the
    migration inside a transaction, so strip those two statements."""
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    sql = re.sub(r"^\s*BEGIN;\s*$", "", sql, count=1, flags=re.MULTILINE)
    sql = re.sub(r"^\s*COMMIT;\s*$", "", sql, count=1, flags=re.MULTILINE)
    return sql


def _exec_raw(sql: str) -> None:
    # Raw driver cursor: no SQLAlchemy bind-param parsing, multi-statement OK.
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_raw(_schema_body())


def downgrade() -> None:
    _exec_raw(
        "".join(f"DROP TABLE IF EXISTS {t} CASCADE;\n" for t in TABLES)
        + "DROP FUNCTION IF EXISTS audit_logs_append_only();\n"
    )
