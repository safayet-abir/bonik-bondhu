"""P3 financing request API (AT-17; FR-FIN-01..09) and assessment rules
that the seed does not cover (overdue debts, horizon, harvest order)."""
from __future__ import annotations

from datetime import timedelta

from app.core.clock import today
from tests.helpers import create_profile, owner


def iso(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


def setup_shop(c, n: int = 1) -> tuple[str, str]:
    owner(c, n)
    p = create_profile(c, "Test Store", district="Dhaka", upazila="Savar", business_category="grocery",
                       household_withdrawal_monthly="3000")
    r = c.post(f"/api/v1/profiles/{p['id']}/financing-requests",
               json={"requested_amount": "60000", "purpose_text": "স্টক কিনবো", "purpose_category": "inventory"})
    assert r.status_code == 201, r.text
    return p["id"], r.json()["id"]


def weekly_history(c, pid: str, weeks: int = 4, sale: str = "30000", cost: str = "12000") -> None:
    for k in range(1, weeks + 1):
        d = iso(-7 * k + 2)
        for ty, amt in (("sale_cash", sale), ("purchase_cash", cost)):
            r = c.post(f"/api/v1/profiles/{pid}/transactions",
                       json={"txn_type": ty, "amount": amt, "value_date": d,
                             "client_request_id": f"{k:08d}-0000-4000-8000-{'1' if ty == 'sale_cash' else '2'}" + "0" * 11})
            assert r.status_code in (200, 201), r.text


def test_preview_gap_and_installments(client) -> None:  # AT-17
    pid, rid = setup_shop(client)
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}"
    item = client.post(url + "/items", json={"item_name": "Rice sacks", "quantity": "20", "unit": "sack",
                                              "unit_price": "2500", "price_source_type": "supplier_quote"})
    assert item.status_code == 201 and item.json()["line_total"] == "50000.00"
    r = client.patch(url, json={"associated_expenses": "2000", "liquidity_buffer": "3000",
                                "cash_safely_available": "5000", "committed_financing": "0",
                                "schedule_type": "equal_installments", "installment_count": 3,
                                "installment_frequency": "weekly", "first_due_date": iso(7),
                                "interest_fees_total": "1000", "minimum_cash_reserve": "2000"})
    assert r.status_code == 200, r.text
    pv = r.json()["preview"]
    assert (pv["items_total"], pv["funding_gap"], pv["request_minus_gap"], pv["gap_inputs_complete"]) == \
        ("50000.00", "50000.00", "10000.00", True)
    assert [i["amount"] for i in pv["installments"]] == ["20333.33", "20333.33", "20333.34"]
    assert pv["installments"][2]["due_date"] == iso(21) and pv["repayment_total"] == "61000.00"
    assert r.json()["label_key"] == "fin.proposal_banner"


def test_terms_validation(client) -> None:
    pid, rid = setup_shop(client)
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}"
    r = client.patch(url, json={"first_due_date": iso(-1)})
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"first_due_date": "fin.err.first_due_past"}
    r = client.patch(url, json={"schedule_type": "equal_installments"})
    assert r.status_code == 422 and "installment_frequency" in r.json()["error"]["fields"]
    r = client.patch(url, json={"schedule_type": "single_payment", "installment_count": 5,
                                "installment_frequency": "weekly"}).json()
    assert (r["installment_count"], r["installment_frequency"]) == (1, None)
    r = client.patch(url, json={"interest_fees_total": "500"}).json()
    assert (r["interest_fees_total"], r["interest_fees_unknown"]) == ("500.00", False)
    r = client.patch(url, json={"interest_fees_unknown": True}).json()
    assert (r["interest_fees_total"], r["interest_fees_unknown"]) == (None, True)
    assert client.patch(url, json={"installment_count": 61}).status_code == 422
    assert client.patch(url, json={"requested_amount": "0"}).status_code == 422


def test_items_crud_and_unconfirmed_never_count(client) -> None:
    pid, rid = setup_shop(client)
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}"
    a = client.post(url + "/items", json={"item_name": "Oil", "quantity": "10", "unit": "tin", "unit_price": "1800"})
    assert a.json()["price_source_type"] == "owner_estimate" and a.json()["confirmed"] is True
    iid = a.json()["id"]
    assert client.patch(f"{url}/items/{iid}", json={"unit_price": "1900"}).json()["line_total"] == "19000.00"
    assert client.get(url).json()["preview"]["items_total"] == "19000.00"
    assert client.post(url + "/items", json={"item_name": "x"}).status_code == 422
    assert client.delete(f"{url}/items/{iid}").status_code == 204
    assert client.get(url).json()["preview"]["items_total"] == "0.00"
    assert client.delete(f"{url}/items/{iid}").status_code == 404


def test_farm_copy_season_cost_item(client) -> None:  # FR-FIN-08
    owner(client)
    p = create_profile(client, "Farm", activity_type="crop_farm", district="Dhaka", upazila="Dhamrai")
    s = client.post(f"/api/v1/profiles/{p['id']}/seasons", json={
        "crop_name": "Rice", "season_name": "boro", "area_value": "100", "area_unit": "decimal",
        "sowing_date": iso(10), "expected_harvest_date": iso(120)}).json()
    ci = client.post(f"/api/v1/profiles/{p['id']}/seasons/{s['id']}/cost-items", json={
        "category": "fertilizer", "item_name": "Urea", "quantity": "2", "unit": "bag", "unit_cost": "1400"}).json()
    r = client.post(f"/api/v1/profiles/{p['id']}/financing-requests", json={
        "requested_amount": "2800", "purpose_text": "সার", "purpose_category": "farm_inputs"}).json()
    url = f"/api/v1/profiles/{p['id']}/financing-requests/{r['id']}"
    assert client.post(url + "/items", json={"copy_from_season_cost_item_id": ci["id"]}).status_code == 422
    client.patch(url, json={"season_id": s["id"]})
    item = client.post(url + "/items", json={"copy_from_season_cost_item_id": ci["id"]})
    assert item.status_code == 201 and item.json()["line_total"] == "2800.00"
    assert item.json()["source_season_cost_item_id"] == ci["id"]
    dup = client.post(url + "/items", json={"copy_from_season_cost_item_id": ci["id"]})
    assert dup.status_code == 409 and dup.json()["error"]["message_key"] == "fin.err.item_already_copied"
    # deleting the cost item is now refused (used by a request)
    assert client.delete(f"/api/v1/profiles/{p['id']}/seasons/{s['id']}/cost-items/{ci['id']}").status_code == 409


def _complete_shop(client, pid: str, rid: str, **terms) -> str:
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}"
    client.post(url + "/items", json={"item_name": "Stock", "quantity": "1", "unit": "lot", "unit_price": "60000",
                                      "price_source_type": "supplier_quote"})
    body = {"associated_expenses": "0", "liquidity_buffer": "0", "cash_safely_available": "0",
            "committed_financing": "0", "current_cash_balance": "10000", "minimum_cash_reserve": "1000",
            "schedule_type": "equal_installments", "installment_count": 6, "installment_frequency": "weekly",
            "first_due_date": iso(7), "interest_fees_total": "0", **terms}
    assert client.patch(url, json=body).status_code == 200
    return url


def test_shop_complete_ready_then_overdue_debt_counts(client) -> None:
    pid, rid = setup_shop(client)
    weekly_history(client, pid)
    client.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    url = _complete_shop(client, pid, rid)
    a = client.post(url + "/assessments").json()
    assert a["status"] == "ready_for_lender_review", a["missing_items"]
    assert a["flags"] == []
    # A declared overdue amount is owed now: it is paid on as_of and can push the case into a shortfall.
    d = client.post(f"/api/v1/profiles/{pid}/debts", json={
        "lender_type": "mohajon", "lender_label": "Local lender", "original_principal": "40000",
        "outstanding_balance": "40000", "installment_amount": "5000", "installment_frequency": "weekly",
        "next_due_date": iso(30), "is_overdue": True, "overdue_amount": "15000"})
    assert d.status_code == 201, d.text
    a2 = client.post(url + "/assessments").json()
    assert "existing_debt_overdue" in a2["flags"]
    first = a2["base_result"]["checks"][0]
    assert first["date"] == iso(0) and first["existing_paid"] == "15000.00"
    assert a2["status"] == "not_affordable_base_case"
    total_existing = sum(float(c["existing_paid"]) for c in a2["base_result"]["checks"])
    assert total_existing <= 40000  # never more than the declared outstanding


def test_every_input_service_makes_assessment_stale(client) -> None:  # FR-ASM-09; closes P2 F-3
    pid, rid = setup_shop(client)
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}"
    latest = url + "/assessments/latest"
    base = f"/api/v1/profiles/{pid}"
    sup = None

    def supplier():
        nonlocal sup
        sup = client.post(base + "/suppliers", json={"display_name": "Wholesaler"}).json()

    changes = [
        supplier,
        lambda: client.patch(f"{base}/suppliers/{sup['id']}", json={"district": "Gazipur"}),
        lambda: client.post(base + "/debts/declare-none"),
        lambda: client.post(base + "/debts", json={
            "lender_type": "ngo", "lender_label": "NGO", "original_principal": "1000", "outstanding_balance": "500",
            "installment_amount": "100", "installment_frequency": "weekly", "next_due_date": iso(3)}),
        lambda: client.patch(base, json={"household_withdrawal_monthly": "4000"}),
        lambda: client.patch(url, json={"liquidity_buffer": "100"}),
        lambda: client.post(url + "/items", json={"item_name": "Oil", "quantity": "1", "unit": "tin",
                                                  "unit_price": "1"}),
    ]
    for change in changes:
        client.post(url + "/assessments")
        assert client.get(latest).json()["is_stale"] is False
        change()
        assert client.get(latest).json()["is_stale"] is True, change


def test_shop_term_beyond_90_days_is_insufficient(client) -> None:  # DEC-33
    pid, rid = setup_shop(client)
    weekly_history(client, pid)
    client.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    url = _complete_shop(client, pid, rid, installment_count=12, installment_frequency="monthly")
    a = client.post(url + "/assessments").json()
    assert a["status"] == "insufficient_information"
    assert a["missing_items"] == ["term_beyond_forecast_horizon"]
    assert a["funding_gap"] == "60000.00"  # the gap itself is still shown


def test_unknown_cash_and_interest_flags(client) -> None:
    pid, rid = setup_shop(client)
    weekly_history(client, pid)
    client.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    url = _complete_shop(client, pid, rid, current_cash_balance=None, interest_fees_unknown=True,
                         minimum_cash_reserve="0")
    a = client.post(url + "/assessments").json()
    assert {"starting_cash_unknown", "interest_fees_unknown", "reserve_zero"} <= set(a["flags"])
    assert a["base_result"]["start_balance"] == "0.00"


def test_farm_due_before_harvest(client) -> None:
    owner(client)
    p = create_profile(client, "Farm", activity_type="crop_farm", district="Dhaka", upazila="Dhamrai",
                       household_withdrawal_monthly="0")
    pid = p["id"]
    client.post(f"/api/v1/profiles/{pid}/debts/declare-none")
    s = client.post(f"/api/v1/profiles/{pid}/seasons", json={
        "crop_name": "Rice", "season_name": "boro", "area_value": "1", "area_unit": "acre",
        "sowing_date": iso(5), "expected_harvest_date": iso(100), "expected_output_low": "1800",
        "expected_output_expected": "2200", "expected_output_high": "2500", "expected_price_low": "28",
        "expected_price_expected": "31", "expected_price_high": "34"}).json()
    r = client.post(f"/api/v1/profiles/{pid}/financing-requests", json={
        "requested_amount": "20000", "purpose_text": "সার ও সেচ", "purpose_category": "farm_inputs",
        "season_id": s["id"]}).json()
    url = f"/api/v1/profiles/{pid}/financing-requests/{r['id']}"
    client.post(url + "/items", json={"item_name": "Inputs", "quantity": "1", "unit": "lot", "unit_price": "20000"})
    client.patch(url, json={"associated_expenses": "0", "liquidity_buffer": "0", "cash_safely_available": "0",
                            "committed_financing": "0", "minimum_cash_reserve": "1000", "schedule_type": "single_payment",
                            "first_due_date": iso(60), "interest_fees_total": "1000"})
    a = client.post(url + "/assessments").json()
    assert a["missing_items"] == ["repayment_due_before_expected_harvest"]
    client.patch(url, json={"first_due_date": iso(115)})
    a = client.post(url + "/assessments").json()
    assert a["status"] == "ready_for_lender_review", a
    assert a["base_result"]["available_at_due_date"] == "49400.00"  # 1800×28 − 1000 reserve


def test_season_incomplete_without_estimates(client) -> None:
    owner(client)
    p = create_profile(client, "Farm", activity_type="crop_farm", district="Dhaka", upazila="Dhamrai")
    r = client.post(f"/api/v1/profiles/{p['id']}/financing-requests", json={
        "requested_amount": "5000", "purpose_text": "বীজ", "purpose_category": "farm_inputs"}).json()
    a = client.post(f"/api/v1/profiles/{p['id']}/financing-requests/{r['id']}/assessments").json()
    assert "season_incomplete" in a["missing_items"] and "forecast_insufficient_history" not in a["missing_items"]
    assert a["forecast_run_id"] is None


def test_location_missing_is_listed(client) -> None:
    owner(client)
    p = create_profile(client, "No Place Shop")
    r = client.post(f"/api/v1/profiles/{p['id']}/financing-requests", json={
        "requested_amount": "5000", "purpose_text": "মাল", "purpose_category": "inventory"}).json()
    a = client.post(f"/api/v1/profiles/{p['id']}/financing-requests/{r['id']}/assessments").json()
    assert a["missing_items"][-1] == "profile_location_missing"
