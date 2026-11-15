"""P7-T03 DB constraint script (DB doc §8: "Rejected by DB (18 cases)"). Each statement is
written so that only the constraint under test can fail, and the error must name that table /
trigger — so a different failure cannot make the test pass by accident. These checks complement,
never replace, the service-layer authorization tests (Security doc §7)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.api.test_risk_p4 import assess, demo_profile, seeded  # noqa: F401  (fixture)

STORE = "(SELECT id FROM business_profiles WHERE display_name = 'Rahim Store')"
KARIM = "(SELECT id FROM business_profiles WHERE display_name = 'Karim Variety Store')"
FARM = "(SELECT id FROM business_profiles WHERE display_name = 'Rahim Rice Farm')"
RAHIM = "(SELECT id FROM users WHERE phone_e164 = '+8801900000001')"
SUP_A = f"(SELECT id FROM suppliers WHERE profile_id = {STORE} AND display_name LIKE 'Supplier A%')"
ORG = "(SELECT id FROM lender_organizations WHERE name = 'DEMO Bank Ltd (fictional)')"
OFFICER = "(SELECT user_id FROM lender_officers lo JOIN users u ON u.id = lo.user_id WHERE u.phone_e164 = '+8801900000101')"
REQ = f"(SELECT id FROM financing_requests WHERE profile_id = {STORE})"
ASSESS = f"(SELECT id FROM financial_assessments WHERE profile_id = {STORE} ORDER BY created_at DESC LIMIT 1)"
CONSENT = (f"WITH c AS (INSERT INTO consents (profile_id, lender_organization_id, requested_by_user_id, "
           f"requested_sections) VALUES ({STORE}, {ORG}, {OFFICER}, ARRAY['profile_summary']) RETURNING id)")
REVIEW = (CONSENT + f", r AS (INSERT INTO lender_reviews (consent_id, organization_id) SELECT id, {ORG} FROM c RETURNING id)")

CASES = [
    ("cross-profile supplier link", "transactions",
     f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by, supplier_id) "
     f"VALUES ({KARIM}, 'purchase_cash', 100, CURRENT_DATE, {RAHIM}, {SUP_A})"),
    ("supplier on a sale", "transactions",
     f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by, supplier_id) "
     f"VALUES ({STORE}, 'sale_cash', 100, CURRENT_DATE, {RAHIM}, {SUP_A})"),
    ("zero amount", "transactions",
     f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by) "
     f"VALUES ({STORE}, 'sale_cash', 0, CURRENT_DATE, {RAHIM})"),
    ("void without reason", "transactions",
     f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by, status, voided_at) "
     f"VALUES ({STORE}, 'sale_cash', 100, CURRENT_DATE, {RAHIM}, 'voided', now())"),
    ("document_attached without document", "transactions",
     f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by, evidence_state) "
     f"VALUES ({STORE}, 'sale_cash', 100, CURRENT_DATE, {RAHIM}, 'document_attached')"),
    ("invalid phone", "users",
     "INSERT INTO users (full_name, phone_e164, email, password_hash) VALUES ('Test', '+880123', 't@x.invalid', 'h')"),
    ("duplicate email", "ux_users_email",
     "INSERT INTO users (full_name, phone_e164, email, password_hash) "
     "SELECT 'Test', '+8801712345678', email, 'h' FROM users WHERE phone_e164 = '+8801900000001'"),
    ("bigha without factor", "farming_seasons",
     f"INSERT INTO farming_seasons (profile_id, crop_name, season_name, area_value, area_unit, area_acres, "
     f"sowing_date, expected_harvest_date) VALUES ({FARM}, 'Rice', 'boro', 2, 'bigha', 0.66, "
     "CURRENT_DATE, CURRENT_DATE + 100)"),
    ("harvest before sowing", "farming_seasons",
     f"INSERT INTO farming_seasons (profile_id, crop_name, season_name, area_value, area_unit, area_acres, "
     f"sowing_date, expected_harvest_date) VALUES ({FARM}, 'Rice', 'boro', 1, 'acre', 1, "
     "CURRENT_DATE, CURRENT_DATE - 1)"),
    ("approved consent missing sections", "consents",
     f"INSERT INTO consents (profile_id, lender_organization_id, requested_by_user_id, requested_sections, status, "
     f"approved_sections, valid_until, approved_at, assessment_id) VALUES ({STORE}, {ORG}, {OFFICER}, "
     f"ARRAY['money_summary'], 'approved', ARRAY['money_summary'], now() + interval '14 days', now(), {ASSESS})"),
    ("unknown section key", "consents",
     f"INSERT INTO consents (profile_id, lender_organization_id, requested_by_user_id, requested_sections) "
     f"VALUES ({STORE}, {ORG}, {OFFICER}, ARRAY['credit_score'])"),
    ("real news without URL", "news_events",
     "INSERT INTO news_events (headline, headline_lang, source_name, published_date, event_type, dedup_key, "
     "curated_by) VALUES ('A real headline', 'en', 'Paper', CURRENT_DATE, 'market_fire', 'x-1', 'test')"),
    ("audit UPDATE", "append-only", "UPDATE audit_logs SET outcome = 'failure'"),
    ("audit DELETE", "append-only", "DELETE FROM audit_logs"),
    ("lender decision without reason", "lender_reviews",
     CONSENT + f" INSERT INTO lender_reviews (consent_id, organization_id, status, decision, decided_by, decided_at) "
     f"SELECT id, {ORG}, 'decision_recorded', 'refer', {OFFICER}, now() FROM c"),
    ("lender note visible to owner", "lender_review_events",
     REVIEW + f" INSERT INTO lender_review_events (review_id, officer_user_id, event_type, body, visible_to_owner) "
     f"SELECT id, {OFFICER}, 'note', 'private note', TRUE FROM r"),
    ("unconfirmed non-AI item", "financing_request_items",
     f"INSERT INTO financing_request_items (profile_id, financing_request_id, item_name, quantity, unit, unit_price, "
     f"price_source_type, ai_proposed, confirmed) VALUES ({STORE}, {REQ}, 'Rice', 1, 'bag', 100, 'owner_estimate', "
     "FALSE, FALSE)"),
    ("auto scenario left proposed", "risk_scenarios",
     f"INSERT INTO risk_scenarios (profile_id, assessment_id, scenario_type, origin, parameters, status) "
     f"VALUES ({STORE}, {ASSESS}, 'supplier_delay', 'auto', '{{\"days\": 7}}', 'proposed')"),
]


@pytest.fixture()
def db_with_assessment(seeded, client):  # noqa: F811
    p = demo_profile(client, "01900000001", "Rahim Store")
    assess(client, p["id"])  # a real assessment row for the consent / scenario cases
    engine = create_engine(seeded)
    yield engine
    engine.dispose()


def test_db_rejects_all_18_cases(db_with_assessment) -> None:
    assert len(CASES) == 18
    with db_with_assessment.connect() as conn:
        assert conn.execute(text(f"SELECT count(*) FROM financial_assessments WHERE id = {ASSESS}")).scalar() == 1
        assert conn.execute(text("SELECT count(*) FROM audit_logs")).scalar() > 0  # the audit cases have a row
        for name, expected, sql in CASES:
            with pytest.raises(DBAPIError) as err:
                with conn.begin_nested():
                    conn.execute(text(sql))
            assert expected in str(err.value.orig), f"{name}: failed for another reason: {err.value.orig}"
        conn.rollback()


def test_controls_the_same_rows_are_accepted_when_valid(db_with_assessment) -> None:
    """Positive controls: the fixtures above are valid apart from the one broken rule."""
    ok = [
        f"INSERT INTO transactions (profile_id, txn_type, amount, value_date, created_by, supplier_id) "
        f"VALUES ({STORE}, 'purchase_cash', 100, CURRENT_DATE, {RAHIM}, {SUP_A})",
        f"INSERT INTO farming_seasons (profile_id, crop_name, season_name, area_value, area_unit, decimals_per_bigha, "
        f"area_acres, sowing_date, expected_harvest_date) VALUES ({FARM}, 'Rice', 'boro', 2, 'bigha', 33, 0.66, "
        "CURRENT_DATE, CURRENT_DATE + 100)",
        REVIEW + f" INSERT INTO lender_review_events (review_id, officer_user_id, event_type, body, visible_to_owner) "
        f"SELECT id, {OFFICER}, 'note', 'private note', FALSE FROM r",
        f"INSERT INTO risk_scenarios (profile_id, assessment_id, scenario_type, origin, parameters, status, result) "
        f"VALUES ({STORE}, {ASSESS}, 'supplier_delay', 'auto', '{{\"days\": 7}}', 'computed', '{{}}')",
    ]
    with db_with_assessment.connect() as conn:
        for sql in ok:
            with conn.begin_nested():
                conn.execute(text(sql))
        conn.rollback()
