"""P2-T06 debts (FR-DEBT-01..03) and P2-T07 suppliers (FR-SUP-01/02)."""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core import clock

from ..helpers import create_profile, owner


@pytest.fixture
def shop(client):
    owner(client)
    return client, create_profile(client)["id"]


def _mfi(**over):
    return {"lender_type": "mfi", "lender_label": "DEMO NGO weekly loan", "original_principal": "100000",
            "outstanding_balance": "60000", "installment_amount": "2500", "installment_frequency": "weekly",
            "next_due_date": (clock.today() + timedelta(days=3)).isoformat(), **over}


def test_create_and_list_debt_with_next_installments(shop) -> None:
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi())
    assert r.status_code == 201, r.text
    d = r.json()
    t = clock.today()
    assert d["evidence_state"] == "declared" and d["status"] == "active"
    assert d["outstanding_as_of"] == t.isoformat()
    assert d["next_installments"] == [
        {"due_date": (t + timedelta(days=k)).isoformat(), "amount": "2500.00"} for k in (3, 10, 17)]
    assert d["dates_outdated"] is False
    listed = c.get(f"/api/v1/profiles/{pid}/debts").json()
    assert listed["total"] == 1 and listed["no_debt_declared"] is False


def test_single_debt_needs_no_installment(shop) -> None:
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi(
        lender_type="dealer_credit", installment_frequency="single", installment_amount="999",
        original_principal="6000", outstanding_balance="6000",
        next_due_date=(clock.today() + timedelta(days=20)).isoformat()))
    assert r.status_code == 201
    d = r.json()
    assert d["installment_amount"] is None
    assert d["next_installments"] == [{"due_date": (clock.today() + timedelta(days=20)).isoformat(),
                                       "amount": "6000.00"}]


@pytest.mark.parametrize(("over", "field", "key"), [
    ({"installment_amount": None}, "installment_amount", "debt.err.installment_required"),
    ({"next_due_date": None}, "next_due_date", "debt.err.next_due_required"),
    ({"lender_type": "cib"}, "lender_type", None),
    ({"lender_label": ""}, "lender_label", "debt.err.label"),
    ({"is_overdue": True, "overdue_amount": "70000"}, "overdue_amount", "debt.err.overdue_amount"),
])
def test_debt_validation(shop, over, field, key) -> None:
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi(**over))
    assert r.status_code == 422, r.text
    fields = r.json()["error"]["fields"]
    assert field in fields
    if key:
        assert fields[field] == key


def test_outdated_next_due_flagged(shop) -> None:
    c, pid = shop
    d = c.post(f"/api/v1/profiles/{pid}/debts",
               json=_mfi(next_due_date=(clock.today() - timedelta(days=7)).isoformat())).json()
    assert d["dates_outdated"] is True
    assert d["next_installments"][0]["due_date"] == clock.today().isoformat()


def test_declare_none_rules(shop) -> None:  # FR-DEBT-02
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    assert r.status_code == 200 and r.json() == {"no_debt_declared": True}
    assert c.get(f"/api/v1/profiles/{pid}").json()["no_debt_declared"] is True

    debt = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi()).json()
    assert c.get(f"/api/v1/profiles/{pid}").json()["no_debt_declared"] is False  # cleared by a real debt
    blocked = c.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    assert blocked.status_code == 409 and blocked.json()["error"]["message_key"] == "debt.err.active_exists"

    closed = c.patch(f"/api/v1/profiles/{pid}/debts/{debt['id']}", json={"status": "closed"})
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
    assert closed.json()["next_installments"] == []
    assert c.post(f"/api/v1/profiles/{pid}/debts/declare-none").status_code == 200


def test_patch_debt(shop) -> None:
    c, pid = shop
    d = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi()).json()
    r = c.patch(f"/api/v1/profiles/{pid}/debts/{d['id']}", json={"outstanding_balance": "5000", "is_overdue": True,
                                                                   "overdue_amount": "2500"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["outstanding_balance"], body["overdue_amount"], body["is_overdue"]) == ("5000.00", "2500.00", True)
    assert [i["amount"] for i in body["next_installments"]] == ["2500.00", "2500.00"]


def test_debt_season_link_is_farm_only(shop) -> None:
    import uuid
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/debts", json=_mfi(season_id=str(uuid.uuid4())))
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"season_id": "entry.err.season_farm_only"}


# ---------------------------------------------------------------- suppliers
def test_supplier_crud(shop) -> None:
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/suppliers", json={
        "display_name": "Supplier A (DEMO wholesaler)", "goods_supplied": "rice, oil",
        "district": "Gazipur", "upazila": "Kaliakair", "declared_purchase_share_pct": "65"})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["declared_purchase_share_pct"] == "65.00" and s["is_active"] is True
    p = c.patch(f"/api/v1/profiles/{pid}/suppliers/{s['id']}", json={"is_active": False,
                                                                     "declared_purchase_share_pct": None})
    assert p.status_code == 200
    assert (p.json()["is_active"], p.json()["declared_purchase_share_pct"]) == (False, None)
    assert c.get(f"/api/v1/profiles/{pid}/suppliers").json()["total"] == 1


@pytest.mark.parametrize(("body", "field", "key"), [
    ({"display_name": ""}, "display_name", "supplier.err.name"),
    ({"display_name": "A", "declared_purchase_share_pct": "101"}, "declared_purchase_share_pct", "supplier.err.share"),
    ({"display_name": "A", "declared_purchase_share_pct": "-1"}, "declared_purchase_share_pct", "supplier.err.share"),
])
def test_supplier_validation(shop, body, field, key) -> None:
    c, pid = shop
    r = c.post(f"/api/v1/profiles/{pid}/suppliers", json=body)
    assert r.status_code == 422 and r.json()["error"]["fields"][field] == key
