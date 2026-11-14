"""P2 ledger: AT-09 (12 types + link rules), AT-10 duplicates, AT-12 void,
E1 golden fixture through the API (Testing §4.1)."""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core import clock
from app.engine.accounting import TXN_TYPES

from ..helpers import create_profile, owner


def _post(c, pid, txn_type, amount, **extra):
    body = {"txn_type": txn_type, "amount": str(amount), "value_date": clock.today().isoformat(),
            "client_request_id": str(uuid.uuid4()), **extra}
    return c.post(f"/api/v1/profiles/{pid}/transactions", json=body)


def _supplier(c, pid, name="Supplier A (DEMO)"):
    r = c.post(f"/api/v1/profiles/{pid}/suppliers", json={"display_name": name, "district": "Gazipur",
                                                          "upazila": "Kaliakair"})
    assert r.status_code == 201, r.text
    return r.json()


def _debt(c, pid):
    r = c.post(f"/api/v1/profiles/{pid}/debts", json={
        "lender_type": "mfi", "lender_label": "DEMO NGO weekly loan", "original_principal": "100000",
        "outstanding_balance": "60000", "installment_amount": "2500", "installment_frequency": "weekly",
        "next_due_date": (clock.today() + timedelta(days=3)).isoformat()})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def shop(client):
    owner(client)
    return client, create_profile(client)["id"]


def test_all_12_types_can_be_recorded(shop) -> None:  # AT-09
    c, pid = shop
    for i, t in enumerate(sorted(TXN_TYPES), 1):
        r = _post(c, pid, t, 100 + i)
        assert r.status_code == 201, (t, r.text)
        assert r.json()["txn_type"] == t
    assert c.get(f"/api/v1/profiles/{pid}/transactions").json()["total"] == 12
    loans = c.get(f"/api/v1/profiles/{pid}/transactions?txn_type=loan_received&txn_type=loan_principal_repayment")
    assert loans.json()["total"] == 2


@pytest.mark.parametrize("txn_type", ["sale_cash", "operating_expense", "loan_received", "owner_withdrawal"])
def test_supplier_link_only_on_purchase_types(shop, txn_type) -> None:  # AT-09 link rules
    c, pid = shop
    sid = _supplier(c, pid)["id"]
    r = _post(c, pid, txn_type, 500, supplier_id=sid)
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == {"supplier_id": "entry.err.supplier_link_type"}


@pytest.mark.parametrize("txn_type", ["purchase_cash", "purchase_credit", "payable_payment"])
def test_purchase_with_supplier(shop, txn_type) -> None:
    c, pid = shop
    s = _supplier(c, pid)
    r = _post(c, pid, txn_type, 65000, supplier_id=s["id"])
    assert r.status_code == 201
    assert r.json()["supplier"] == {"id": s["id"], "display_name": "Supplier A (DEMO)"}
    listed = c.get(f"/api/v1/profiles/{pid}/transactions", params={"supplier_id": s["id"]}).json()
    assert listed["total"] == 1 and listed["items"][0]["supplier"]["display_name"] == "Supplier A (DEMO)"


def test_debt_link_only_on_loan_types(shop) -> None:
    c, pid = shop
    did = _debt(c, pid)["id"]
    for t in ("loan_received", "loan_principal_repayment", "loan_interest_fee_payment"):
        r = _post(c, pid, t, 2500 + len(t), debt_facility_id=did)
        assert r.status_code == 201, r.text
        assert r.json()["debt_facility_id"] == did
    r = _post(c, pid, "operating_expense", 2500, debt_facility_id=did)
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"debt_facility_id": "entry.err.debt_link_type"}


def test_unknown_link_is_404(shop) -> None:
    c, pid = shop
    assert _post(c, pid, "purchase_cash", 10, supplier_id=str(uuid.uuid4())).status_code == 404
    assert _post(c, pid, "loan_received", 10, debt_facility_id=str(uuid.uuid4())).status_code == 404


def test_season_fields_rejected_on_shop(shop) -> None:
    c, pid = shop
    r = _post(c, pid, "operating_expense", 10, season_id=str(uuid.uuid4()))
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"season_id": "entry.err.season_farm_only"}


def test_settlement_before_value_date_rejected(shop) -> None:
    c, pid = shop
    r = _post(c, pid, "sale_credit", 10, settlement_date=(clock.today() - timedelta(days=1)).isoformat())
    assert r.status_code == 422 and "settlement_date" in r.json()["error"]["fields"]


# ---------------------------------------------------------------- AT-10 duplicates (SUG-28)
def test_duplicate_warning_then_confirm(shop) -> None:
    c, pid = shop
    first = _post(c, pid, "sale_cash", 1200).json()
    r = _post(c, pid, "sale_cash", "1,200")
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "POSSIBLE_DUPLICATE"
    assert err["existing"] == {"id": first["id"], "txn_type": "sale_cash", "amount": "1200.00",
                               "value_date": clock.today().isoformat()}
    ok = _post(c, pid, "sale_cash", 1200, confirm_duplicate=True)
    assert ok.status_code == 201 and ok.json()["duplicate_confirmed"] is True
    assert c.get(f"/api/v1/profiles/{pid}/transactions").json()["total"] == 2


def test_not_duplicate_when_type_date_or_supplier_differs(shop) -> None:
    c, pid = shop
    a, b = _supplier(c, pid, "A")["id"], _supplier(c, pid, "B")["id"]
    assert _post(c, pid, "sale_cash", 500).status_code == 201
    assert _post(c, pid, "operating_expense", 500).status_code == 201
    yesterday = (clock.today() - timedelta(days=1)).isoformat()
    assert _post(c, pid, "sale_cash", 500, value_date=yesterday).status_code == 201
    assert _post(c, pid, "purchase_cash", 900, supplier_id=a).status_code == 201
    assert _post(c, pid, "purchase_cash", 900, supplier_id=b).status_code == 201


def test_voided_entry_is_not_a_duplicate(shop) -> None:
    c, pid = shop
    t = _post(c, pid, "sale_cash", 700).json()
    c.post(f"/api/v1/profiles/{pid}/transactions/{t['id']}/void", json={"reason": "ভুল পরিমাণ"})
    assert _post(c, pid, "sale_cash", 700).status_code == 201


# ---------------------------------------------------------------- AT-12 void
def test_void_excluded_from_summary_and_still_listed(shop) -> None:
    c, pid = shop
    keep = _post(c, pid, "sale_cash", 5000).json()
    wrong = _post(c, pid, "sale_cash", 7000).json()
    r = c.post(f"/api/v1/profiles/{pid}/transactions/{wrong['id']}/void",
               json={"reason": "ভুল পরিমাণ লিখেছিলাম"})
    assert r.status_code == 200
    v = r.json()
    assert v["status"] == "voided" and v["void_reason"] == "ভুল পরিমাণ লিখেছিলাম" and v["voided_at"]
    s = c.get(f"/api/v1/profiles/{pid}/summary").json()
    assert s["sales_recorded"] == "5000.00" and s["operating_cash_in"] == "5000.00"
    statuses = {i["id"]: i["status"] for i in c.get(f"/api/v1/profiles/{pid}/transactions").json()["items"]}
    assert statuses == {keep["id"]: "confirmed", wrong["id"]: "voided"}
    voided = c.get(f"/api/v1/profiles/{pid}/transactions", params={"status": "voided"}).json()
    assert voided["total"] == 1


def test_void_rules(shop) -> None:
    c, pid = shop
    t = _post(c, pid, "sale_cash", 10).json()
    url = f"/api/v1/profiles/{pid}/transactions/{t['id']}/void"
    for reason in ("ab", "x" * 201):
        r = c.post(url, json={"reason": reason})
        assert r.status_code == 422 and r.json()["error"]["fields"] == {"reason": "entry.err.void_reason"}
    assert c.post(url, json={"reason": "wrong"}).status_code == 200
    again = c.post(url, json={"reason": "wrong"})
    assert again.status_code == 409 and again.json()["error"]["message_key"] == "entry.err.already_voided"
    assert c.post(f"/api/v1/profiles/{pid}/transactions/{uuid.uuid4()}/void",
                  json={"reason": "wrong"}).status_code == 404


# ---------------------------------------------------------------- E1 golden fixture
def test_e1_golden_fixture_via_api(shop) -> None:
    c, pid = shop
    for t, a in [("sale_cash", 5000), ("sale_credit", 2000), ("loan_received", 50000), ("purchase_cash", 3000),
                 ("loan_principal_repayment", 4000), ("loan_interest_fee_payment", 500),
                 ("receivable_collection", 1500), ("owner_withdrawal", 1000)]:
        assert _post(c, pid, t, a).status_code == 201
    voided = _post(c, pid, "sale_cash", 7000).json()
    c.post(f"/api/v1/profiles/{pid}/transactions/{voided['id']}/void", json={"reason": "E1 voided row"})

    s = c.get(f"/api/v1/profiles/{pid}/summary").json()
    expected = {
        "sales_recorded": "7000.00", "cash_sales": "5000.00", "credit_sales": "2000.00",
        "operating_cash_in": "6500.00", "operating_cash_out": "3000.00", "net_operating_cash": "3500.00",
        "receivables_outstanding": "500.00", "payables_outstanding": "0.00",
        "financing_received": "50000.00", "principal_repaid": "4000.00", "interest_fees_paid": "500.00",
        "owner_withdrawals": "1000.00", "owner_contributions": "0.00", "cash_net_change": "48000.00",
    }
    assert {k: s[k] for k in expected} == expected


def test_entries_bump_data_version_on_void(shop, clean_db: str) -> None:  # P2-T05
    from sqlalchemy import create_engine, text

    c, pid = shop
    t = _post(c, pid, "sale_cash", 10).json()
    c.post(f"/api/v1/profiles/{pid}/transactions/{t['id']}/void", json={"reason": "wrong"})
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        v = conn.execute(text("SELECT data_version FROM business_profiles WHERE id=:id"), {"id": pid}).scalar_one()
    engine.dispose()
    assert v == 3  # created at 1, +1 entry, +1 void
