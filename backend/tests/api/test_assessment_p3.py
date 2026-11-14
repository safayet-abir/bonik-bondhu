"""P3 golden cases through the real API on the real seed (P3-T09):
AT-16 forecast, AT-18 assessments D1–D4, AT-19 staleness, AT-20 forbidden
words. Seed dates are relative to CURRENT_DATE (Asia/Dhaka) = app today()."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text

from app import demo
from app.core.clock import today
from tests.helpers import create_profile, login, owner

DEMO_PW = "test-only-demo-2026"  # isolated test DB only; not the dev/demo DEMO_PASSWORD
FORBIDDEN = ("approved", "eligible", "credit score", "probability of default")


@pytest.fixture()
def seeded(clean_db: str) -> str:
    engine = create_engine(clean_db)
    with engine.begin() as conn:
        assert demo.seed(conn, DEMO_PW) == 6
    engine.dispose()
    return clean_db


def plus(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


def demo_profile(c, phone: str, name: str) -> dict:
    login(c, phone, DEMO_PW)
    return next(p for p in c.get("/api/v1/profiles").json()["items"] if p["display_name"] == name)


def request_id(c, pid: str) -> str:
    items = c.get(f"/api/v1/profiles/{pid}/financing-requests").json()["items"]
    assert len(items) == 1
    return items[0]["id"]


def assess(c, pid: str) -> dict:
    r = c.post(f"/api/v1/profiles/{pid}/financing-requests/{request_id(c, pid)}/assessments")
    assert r.status_code == 201, r.text
    return r.json()


def assert_no_forbidden(payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False).lower()
    for word in FORBIDDEN:
        assert word not in blob, word


# ----------------------------------------------------------------- AT-16 forecast
def test_d1_forecast_golden(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    r = client.post(f"/api/v1/profiles/{p['id']}/forecasts")
    assert r.status_code == 201, r.text
    f = r.json()
    assert (f["status"], f["weeks_with_records"], f["method_version"]) == ("ok", 8, "weekly-baseline-v1")
    assert f["weekly"]["net"] == {"low": "25000.00", "expected": "32312.50", "high": "41000.00"}
    assert (f["weekly"]["collections_expected"], f["weekly"]["payments_expected"],
            f["weekly"]["purchases_expected"]) == ("144312.50", "112000.00", "94000.00")
    assert f["horizons"]["30"] == {"low": "107142.86", "expected": "138482.14", "known_debt_service": "0.00"}
    assert f["horizons"]["90"]["expected"] == "415446.43"
    assert len(f["weeks"]) == 8 and all(w["has_records"] for w in f["weeks"])
    assert f["disclaimer_key"] == "forecast.estimate" and f["is_stale"] is False
    assert client.get(f"/api/v1/profiles/{p['id']}/forecasts/latest").json()["id"] == f["id"]


def test_d4_forecast_insufficient_and_d2_debt_service(seeded, make_client) -> None:
    c4 = make_client()
    p4 = demo_profile(c4, "01900000004", "Selina Tailoring")
    f4 = c4.post(f"/api/v1/profiles/{p4['id']}/forecasts").json()
    assert (f4["status"], f4["weeks_with_records"], f4["weekly"], f4["horizons"]) == \
        ("insufficient_history", 2, None, {})
    c2 = make_client()
    p2 = demo_profile(c2, "01900000002", "Karim Variety Store")
    f2 = c2.post(f"/api/v1/profiles/{p2['id']}/forecasts").json()
    assert f2["weeks_with_records"] == 6 and f2["weekly"]["net"]["expected"] == "8666.67"
    # MFI 2,500 at +3; samity 3,000 at +10 -> 7 days: 2,500; 30 days: 4 × 2,500 + 3,000
    assert f2["horizons"]["7"]["known_debt_service"] == "2500.00"
    assert f2["horizons"]["30"]["known_debt_service"] == "13000.00"


def test_farm_has_no_forecast(seeded, client) -> None:  # FR-SEA-08, closes P2 F-4
    p = demo_profile(client, "01900000001", "Rahim Rice Farm")
    r = client.post(f"/api/v1/profiles/{p['id']}/forecasts")
    assert r.status_code == 403 and r.json()["error"]["code"] == "PROFILE_TYPE_MISMATCH"


# ----------------------------------------------------------------- AT-18 assessments
def test_d1_ready_for_lender_review(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    a = assess(client, p["id"])
    assert a["status"] == "ready_for_lender_review" and a["missing_items"] == []
    assert (a["purpose_items_total"], a["funding_gap"], a["request_minus_gap"]) == \
        ("150000.00", "150000.00", "50000.00")
    assert "request_exceeds_gap" in a["flags"]
    b = a["base_result"]
    assert (b["kind"], b["start_balance"], b["reserve"]) == ("shop_due_dates", "15000.00", "10000.00")
    assert len(b["checks"]) == 12 and b["first_shortfall"] is None
    assert b["min_balance_after_payment"] == "21626.22"
    assert b["checks"][0] == {"date": plus(7), "paid": "18000.00", "new_installment": "18000.00",
                              "existing_paid": "0.00", "balance_after": "21626.22", "shortfall_vs_reserve": "0.00"}
    assert b["checks"][-1]["date"] == plus(84)
    prop = a["explanation"]["proposal"]
    assert prop["repayment_total"] == "216000.00" and prop["label"] == "owner_proposal_not_lender_offer"
    assert a["forecast_run_id"] and a["disclaimer_key"] == "asm.not_approval" and a["is_stale"] is False
    assert_no_forbidden(a)


def test_d2_not_affordable_base_case(seeded, client) -> None:
    p = demo_profile(client, "01900000002", "Karim Variety Store")
    a = assess(client, p["id"])
    assert a["status"] == "not_affordable_base_case"
    assert (a["funding_gap"], a["request_minus_gap"]) == ("70000.00", "10000.00")
    assert {"request_exceeds_gap", "weak_price_evidence"} <= set(a["flags"])
    b = a["base_result"]
    assert len(b["checks"]) == 27 and b["min_balance_after_payment"] == "-69216.63"
    fs = b["first_shortfall"]
    assert (fs["date"], fs["balance_after"], fs["shortfall_vs_reserve"]) == (plus(7), "-746.97", "2746.97")
    assert_no_forbidden(a)


def test_d3_farm_ready_and_loan_cover(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Rice Farm")
    a = assess(client, p["id"])
    assert a["status"] == "ready_for_lender_review", a["missing_items"]
    assert (a["funding_gap"], a["request_minus_gap"]) == ("40000.00", "0.00")
    b = a["base_result"]
    assert b["kind"] == "crop_harvest"
    assert (b["income_low"], b["remaining_costs_outside_request"], b["start_balance"]) == \
        ("75600.00", "8500.00", "8500.00")
    assert (b["pre_harvest_balance"], b["available_at_due_date"], b["surplus_or_shortfall"]) == \
        ("0.00", "64600.00", "22200.00")
    assert (b["debts_due_by_due_date"], b["repayment_due"], b["covered"]) == ("6000.00", "42400.00", True)
    assert (b["break_even_price_per_unit"], b["loan_cover_price_per_unit"]) == ("19.70", "19.78")
    assert b["pre_harvest_shortfall"] == "0.00"  # base case fine; P4 inputs +15% scenario adds the flag (golden §4.4)
    assert "weak_price_evidence" in a["flags"] and "pre_harvest_cash_shortfall" in a["flags"]
    assert_no_forbidden(a)
    sid = client.get(f"/api/v1/profiles/{p['id']}/seasons").json()["items"][0]["id"]
    s = client.get(f"/api/v1/profiles/{p['id']}/seasons/{sid}/summary").json()
    assert s["loan_cover_price_per_kg"] == "19.78" and s["loan_cover_basis"]["repayment_total"] == "42400.00"


def test_d4_insufficient_exact_codes(seeded, client) -> None:
    p = demo_profile(client, "01900000004", "Selina Tailoring")
    a = assess(client, p["id"])
    assert a["status"] == "insufficient_information"
    assert a["missing_items"] == ["debts_not_declared", "household_withdrawal_not_declared",
                                  "purpose_items_missing", "gap_inputs_missing", "terms_incomplete",
                                  "forecast_insufficient_history"]
    assert a["funding_gap"] is None and a["base_result"] == {}
    assert_no_forbidden(a)


# ----------------------------------------------------------------- AT-19 stale
def test_any_input_change_makes_assessment_stale(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    a = assess(client, p["id"])
    rid = a["financing_request_id"]
    latest = f"/api/v1/profiles/{p['id']}/financing-requests/{rid}/assessments/latest"
    assert client.get(latest).json()["is_stale"] is False
    again = assess(client, p["id"])
    assert again["inputs_sha256"] == a["inputs_sha256"]  # same inputs -> same hash
    client.post(f"/api/v1/profiles/{p['id']}/transactions",
                json={"txn_type": "sale_cash", "amount": "100", "value_date": today().isoformat(),
                      "client_request_id": "11111111-1111-4111-8111-111111111111"})
    assert client.get(latest).json()["is_stale"] is True
    assert client.get(f"/api/v1/profiles/{p['id']}/forecasts/latest").json()["is_stale"] is True
    r = client.patch(f"/api/v1/profiles/{p['id']}/financing-requests/{rid}",
                     json={"over_request_explanation": "Eid stock plus a safety margin for festival week."})
    fresh = assess(client, p["id"])
    assert "over_request_explained" in fresh["flags"] and "request_exceeds_gap" not in fresh["flags"]
    assert r.json()["latest_assessment"]["is_stale"] is True
    assert fresh["inputs_sha256"] != a["inputs_sha256"]


def test_other_owner_cannot_read_assessment(seeded, make_client) -> None:
    c1 = make_client()
    p = demo_profile(c1, "01900000001", "Rahim Store")
    a = assess(c1, p["id"])
    c2 = make_client()
    owner(c2, 7)
    assert c2.get(f"/api/v1/profiles/{p['id']}/assessments/{a['id']}").status_code == 404
    mine = create_profile(c2, "My Shop")
    assert c2.get(f"/api/v1/profiles/{mine['id']}/assessments/{a['id']}").status_code == 404
    assert c2.get(f"/api/v1/profiles/{mine['id']}/financing-requests/{a['financing_request_id']}").status_code == 404


# ----------------------------------------------------------------- P3-T09 reset-demo
def test_reset_demo_is_repeatable_and_keeps_audit(seeded, client) -> None:
    demo_profile(client, "01900000001", "Rahim Store")  # creates an auth.login audit row
    engine = create_engine(seeded)
    with engine.begin() as conn:
        audits = conn.execute(text("SELECT count(*) FROM audit_logs")).scalar()
        assert demo.demo_present(conn)
        demo.reset(conn)
        assert not demo.demo_present(conn)
        assert conn.execute(text("SELECT count(*) FROM business_profiles")).scalar() == 0
        demo.reset(conn)  # nothing left: still fine
        demo.seed(conn, DEMO_PW)
        assert conn.execute(text("SELECT count(*) FROM audit_logs")).scalar() == audits
        assert conn.execute(text("SELECT count(*) FROM business_profiles WHERE is_demo")).scalar() == 4
    engine.dispose()
