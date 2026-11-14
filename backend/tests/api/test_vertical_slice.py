"""P1 vertical slice (Implementation Plan §4): register → login → profile →
save entry → reopen → correct summary. Sale 8,500 + rent 1,500 → net 7,000."""
from __future__ import annotations

import uuid
from datetime import timedelta

from app.core import clock

from ..helpers import create_profile, login, owner


def _entry(c, pid: str, txn_type: str, amount, **extra):
    return c.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": txn_type, "amount": amount, "value_date": clock.today().isoformat(),
        "client_request_id": str(uuid.uuid4()), **extra})


def test_slice_sale_and_rent_then_reload(make_client) -> None:
    phone_browser = make_client()
    user = owner(phone_browser)
    pid = create_profile(phone_browser)["id"]

    r = _entry(phone_browser, pid, "sale_cash", "8500")
    assert r.status_code == 201
    t = r.json()
    assert (t["amount"], t["entry_method"], t["evidence_state"], t["status"]) == (
        "8500.00", "manual", "declared", "confirmed")
    assert _entry(phone_browser, pid, "operating_expense", 1500, category="rent").status_code == 201

    # "Reload": a brand-new browser session logs in and reads the summary.
    fresh = make_client()
    login(fresh, user["phone"])
    s = fresh.get(f"/api/v1/profiles/{pid}/summary").json()
    assert s["has_data"] is True
    assert s["operating_cash_in"] == "8500.00"
    assert s["operating_cash_out"] == "1500.00"
    assert s["net_operating_cash"] == "7000.00"
    assert s["sales_recorded"] == s["cash_sales"] == "8500.00"
    assert s["cash_net_change"] == "7000.00"
    assert s["evidence_mix"] == {"declared_pct": "100.0", "document_attached_pct": "0.0"}
    assert s["from"] == clock.today().replace(day=1).isoformat()

    items = fresh.get(f"/api/v1/profiles/{pid}/transactions").json()
    assert items["total"] == 2 and {i["txn_type"] for i in items["items"]} == {"sale_cash", "operating_expense"}


def test_empty_summary(client) -> None:  # FR-LED-09
    owner(client)
    pid = create_profile(client)["id"]
    s = client.get(f"/api/v1/profiles/{pid}/summary").json()
    assert s["has_data"] is False and s["net_operating_cash"] == "0.00"
    assert s["record_coverage"] == {"weeks_with_records": 0, "window_weeks": 8}


def test_idempotent_create(client) -> None:  # FR-LED-10 / AT-11
    owner(client)
    pid = create_profile(client)["id"]
    body = {"txn_type": "sale_cash", "amount": "100", "value_date": clock.today().isoformat(),
            "client_request_id": str(uuid.uuid4())}
    first = client.post(f"/api/v1/profiles/{pid}/transactions", json=body)
    again = client.post(f"/api/v1/profiles/{pid}/transactions", json=body)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["id"] == again.json()["id"]
    assert client.get(f"/api/v1/profiles/{pid}/transactions").json()["total"] == 1


def test_entry_validation(client) -> None:  # FR-LED-04, AT-13
    owner(client)
    pid = create_profile(client)["id"]
    today = clock.today()
    cases = [
        ({"amount": "0"}, "amount", "entry.err.amount"),
        ({"amount": "-5"}, "amount", "entry.err.amount"),
        ({"amount": "10.555"}, "amount", "entry.err.amount_decimals"),
        ({"amount": "100000000000"}, "amount", "entry.err.amount_too_large"),
        ({"value_date": (today + timedelta(days=2)).isoformat()}, "value_date", "entry.err.future_date"),
        ({"note": "x" * 301}, "note", "entry.err.note_length"),
    ]
    for override, field, key in cases:
        body = {"txn_type": "sale_cash", "amount": "100", "value_date": today.isoformat(), **override}
        r = client.post(f"/api/v1/profiles/{pid}/transactions", json=body)
        assert r.status_code == 422, override
        assert r.json()["error"]["fields"][field] == key, override
    # tomorrow is allowed (date not more than 1 day in the future)
    assert _entry(client, pid, "sale_cash", "1", value_date=(today + timedelta(days=1)).isoformat()).status_code == 201


def test_bangla_digit_amount(client) -> None:  # FR-I18N-04
    owner(client)
    pid = create_profile(client)["id"]
    assert _entry(client, pid, "sale_cash", "৮,৫০০").json()["amount"] == "8500.00"


def test_p1_slice_accepts_only_cash_sale_and_expense(client) -> None:
    owner(client)
    pid = create_profile(client)["id"]
    r = _entry(client, pid, "loan_received", "50000")
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"txn_type": "entry.err.type_unavailable"}


def test_entry_bumps_data_version(client, clean_db: str) -> None:  # FR-ASM-09 groundwork
    from sqlalchemy import create_engine, text

    owner(client)
    pid = create_profile(client)["id"]
    _entry(client, pid, "sale_cash", "100")
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        v = conn.execute(text("SELECT data_version FROM business_profiles WHERE id=:id"), {"id": pid}).scalar_one()
    engine.dispose()
    assert v == 2
