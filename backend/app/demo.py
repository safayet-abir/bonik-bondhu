"""DEMO data (MP §18; P3-T09). Runs db/seed_demo.sql — fictional records
dated relative to CURRENT_DATE — then replaces the non-loginable placeholder
password hashes with Argon2id hashes of DEMO_PASSWORD (each user its own
salt). Used only from the admin CLI, never over HTTP."""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import Connection, select, text

from .core.security import hash_password
from .models import User

SEED_SQL = Path(__file__).resolve().parents[1] / "db" / "seed_demo.sql"
PLACEHOLDER = "!seed-placeholder-not-loginable!"
DEMO_PHONES = ("+8801900000001", "+8801900000002", "+8801900000004",
               "+8801900000101", "+8801900000102", "+8801900000103")

# FK-safe delete of everything that is DEMO or belongs to DEMO users/profiles/orgs.
# audit_logs are append-only and are kept (they hold ids only, no FKs).
_RESET = """
DROP TABLE IF EXISTS pg_temp._du, pg_temp._dp, pg_temp._do, pg_temp._dc;
CREATE TEMP TABLE _du ON COMMIT DROP AS
  SELECT id FROM users WHERE is_demo OR phone_e164 = ANY(:phones);
CREATE TEMP TABLE _dp ON COMMIT DROP AS
  SELECT id FROM business_profiles WHERE is_demo OR owner_user_id IN (SELECT id FROM _du);
CREATE TEMP TABLE _do ON COMMIT DROP AS
  SELECT id FROM lender_organizations WHERE is_demo;
CREATE TEMP TABLE _dc ON COMMIT DROP AS
  SELECT id FROM consents WHERE profile_id IN (SELECT id FROM _dp)
     OR lender_organization_id IN (SELECT id FROM _do) OR requested_by_user_id IN (SELECT id FROM _du);
DELETE FROM lender_review_events WHERE officer_user_id IN (SELECT id FROM _du)
   OR review_id IN (SELECT id FROM lender_reviews WHERE consent_id IN (SELECT id FROM _dc));
DELETE FROM lender_reviews WHERE consent_id IN (SELECT id FROM _dc) OR decided_by IN (SELECT id FROM _du);
DELETE FROM shared_reports WHERE consent_id IN (SELECT id FROM _dc);
DELETE FROM consents WHERE id IN (SELECT id FROM _dc);
DELETE FROM risk_scenarios WHERE profile_id IN (SELECT id FROM _dp)
   OR news_event_id IN (SELECT id FROM news_events WHERE is_demo);
DELETE FROM financial_assessments WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM forecast_runs WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM financing_request_items WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM financing_requests WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM extraction_drafts WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM transactions WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM debt_facilities WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM documents WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM season_cost_items WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM farming_seasons WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM suppliers WHERE profile_id IN (SELECT id FROM _dp);
DELETE FROM ai_interactions WHERE user_id IN (SELECT id FROM _du) OR profile_id IN (SELECT id FROM _dp);
DELETE FROM business_profiles WHERE id IN (SELECT id FROM _dp);
DELETE FROM news_events WHERE is_demo;
DELETE FROM lender_officers WHERE user_id IN (SELECT id FROM _du);
DELETE FROM users WHERE id IN (SELECT id FROM _du);
DELETE FROM lender_organizations o WHERE o.id IN (SELECT id FROM _do)
   AND NOT EXISTS (SELECT 1 FROM lender_officers lo WHERE lo.organization_id = o.id)
   AND NOT EXISTS (SELECT 1 FROM consents c WHERE c.lender_organization_id = o.id)
   AND NOT EXISTS (SELECT 1 FROM lender_reviews r WHERE r.organization_id = o.id);
"""


def _seed_body() -> str:
    sql = SEED_SQL.read_text(encoding="utf-8")
    sql = re.sub(r"^\s*BEGIN;\s*$", "", sql, count=1, flags=re.MULTILINE)
    return re.sub(r"^\s*COMMIT;\s*$", "", sql, count=1, flags=re.MULTILINE)


def demo_present(conn: Connection) -> bool:
    return conn.execute(text("SELECT 1 FROM users WHERE phone_e164 = ANY(:p) LIMIT 1"),
                        {"p": list(DEMO_PHONES)}).first() is not None


def seed(conn: Connection, password: str) -> int:
    """Insert the DEMO records inside the caller's transaction. Business dates
    are Bangladesh dates, so CURRENT_DATE is evaluated in Asia/Dhaka."""
    conn.execute(text("SET LOCAL TIME ZONE 'Asia/Dhaka'"))
    raw = conn.connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(_seed_body())
    users = conn.execute(select(User.id).where(User.is_demo, User.password_hash == PLACEHOLDER)).scalars().all()
    for uid in users:
        conn.execute(text("UPDATE users SET password_hash = :h WHERE id = :id"),
                     {"h": hash_password(password), "id": uid})
    return len(users)


def reset(conn: Connection) -> None:
    # One statement per execute: bound parameters use the extended protocol.
    for stmt in (s.strip() for s in _RESET.split(";\n")):
        if stmt:
            conn.execute(text(stmt), {"phones": list(DEMO_PHONES)} if ":phones" in stmt else {})
