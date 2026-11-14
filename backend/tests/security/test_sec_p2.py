"""P2 security negatives: SEC-04, SEC-05, SEC-18 (Security §7) plus
cross-owner checks on the new P2 resources (always 404, never 403)."""
from __future__ import annotations

import uuid

from sqlalchemy import create_engine, text

from app.core import clock

from ..helpers import create_profile, owner


def _two_owners(make_client):
    a, b = make_client(), make_client()
    owner(a, 1)
    owner(b, 2)
    return a, create_profile(a)["id"], b, create_profile(b, "B Farm", "crop_farm")["id"]


def _txn(c, pid, **body):
    return c.post(f"/api/v1/profiles/{pid}/transactions", json={
        "amount": "100", "value_date": clock.today().isoformat(), **body})


def test_sec04_foreign_supplier_link_is_404(make_client) -> None:
    a, pid_a, b, pid_b = _two_owners(make_client)
    sid_b = b.post(f"/api/v1/profiles/{pid_b}/suppliers", json={"display_name": "B's supplier"}).json()["id"]
    r = _txn(a, pid_a, txn_type="purchase_cash", supplier_id=sid_b)
    assert r.status_code == 404
    assert a.get(f"/api/v1/profiles/{pid_a}/transactions").json()["total"] == 0


def test_sec05_void_other_owners_transaction_is_404(make_client) -> None:
    a, pid_a, b, pid_b = _two_owners(make_client)
    tid_b = _txn(b, pid_b, txn_type="sale_cash").json()["id"]
    assert a.post(f"/api/v1/profiles/{pid_a}/transactions/{tid_b}/void", json={"reason": "hack"}).status_code == 404
    assert a.post(f"/api/v1/profiles/{pid_b}/transactions/{tid_b}/void", json={"reason": "hack"}).status_code == 404
    assert b.get(f"/api/v1/profiles/{pid_b}/transactions/{tid_b}").json()["status"] == "confirmed"


def test_cross_owner_p2_resources_are_404(make_client) -> None:
    a, pid_a, b, pid_b = _two_owners(make_client)
    season = b.post(f"/api/v1/profiles/{pid_b}/seasons", json={
        "crop_name": "Rice", "season_name": "boro", "area_value": "1", "area_unit": "acre",
        "sowing_date": "2027-01-10", "expected_harvest_date": "2027-05-05"}).json()
    debt = b.post(f"/api/v1/profiles/{pid_b}/debts", json={
        "lender_type": "samity", "lender_label": "B samity", "original_principal": "1000",
        "outstanding_balance": "1000", "installment_frequency": "single",
        "next_due_date": clock.today().isoformat()}).json()
    sup = b.post(f"/api/v1/profiles/{pid_b}/suppliers", json={"display_name": "B sup"}).json()

    # A reaching into B's profile: ownership first → 404 (not the type guard's 403)
    assert a.get(f"/api/v1/profiles/{pid_b}/seasons").status_code == 404
    assert a.get(f"/api/v1/profiles/{pid_b}/debts").status_code == 404
    assert a.patch(f"/api/v1/profiles/{pid_b}/suppliers/{sup['id']}", json={"display_name": "x"}).status_code == 404
    # A using B's child ids under A's own profile → 404
    assert a.patch(f"/api/v1/profiles/{pid_a}/debts/{debt['id']}", json={"status": "closed"}).status_code == 404
    assert a.patch(f"/api/v1/profiles/{pid_a}/suppliers/{sup['id']}", json={"display_name": "x"}).status_code == 404
    assert _txn(a, pid_a, txn_type="loan_received", debt_facility_id=debt["id"]).status_code == 404
    # A's own farm cannot link B's season
    farm_a = create_profile(a, "A Farm", "crop_farm")["id"]
    assert _txn(a, farm_a, txn_type="operating_expense", season_id=season["id"]).status_code == 404
    assert a.get(f"/api/v1/profiles/{farm_a}/seasons/{season['id']}").status_code == 404


def test_sec18_sql_metacharacters_stored_as_text(client, clean_db: str) -> None:
    owner(client)
    pid = create_profile(client)["id"]
    evil = "'; DROP TABLE users;--"
    r = _txn(client, pid, txn_type="operating_expense", note=evil, category="rent", client_request_id=str(uuid.uuid4()))
    assert r.status_code == 201 and r.json()["note"] == evil
    s = client.post(f"/api/v1/profiles/{pid}/suppliers", json={"display_name": evil})
    assert s.status_code == 201 and s.json()["display_name"] == evil
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 1
    engine.dispose()
