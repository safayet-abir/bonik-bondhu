"""P2-T08 seasons (FR-SEA-01..08), AT-14 bigha factor, AT-15 / P2-T11
profile-type guard. D3 numbers from Testing §4.4."""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core import clock

from ..helpers import create_profile, owner

D3_SEASON = {
    "crop_name": "Rice", "variety": "BRRI dhan29", "season_name": "boro", "season_label": "2026-27",
    "area_value": "150", "area_unit": "decimal", "sowing_date": "2027-01-10", "expected_harvest_date": "2027-05-05",
    "expected_output_low": "2700", "expected_output_expected": "3300", "expected_output_high": "3750",
    "expected_price_low": "28", "expected_price_expected": "32", "expected_price_high": "35",
}
D3_COSTS = [("seed", 4500), ("fertilizer", 18000), ("irrigation", 12000), ("labour", 22000),
            ("pesticide", 5500), ("transport", 3000)]


@pytest.fixture
def farm(client):
    owner(client)
    return client, create_profile(client, "Rahim Rice Farm", "crop_farm")["id"]


def _season(c, pid, **over):
    return c.post(f"/api/v1/profiles/{pid}/seasons", json={**D3_SEASON, **over})


def test_d3_season_area_and_income(farm) -> None:  # FR-SEA-01/03, US-08
    c, pid = farm
    r = _season(c, pid)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["area_acres"] == "1.5000" and s["area_value"] == "150" and s["status"] == "planned"
    assert s["income_range"] == {"low": "75600.00", "expected": "105600.00", "high": "131250.00"}
    assert c.get(f"/api/v1/profiles/{pid}/seasons").json()["total"] == 1


@pytest.mark.parametrize(("over", "acres"), [
    ({"area_value": "21780", "area_unit": "sq_ft"}, "0.5000"),
    ({"area_value": "2", "area_unit": "bigha", "decimals_per_bigha": "33"}, "0.6600"),
    ({"area_value": "1.25", "area_unit": "acre"}, "1.2500"),
])
def test_units(farm, over, acres) -> None:
    c, pid = farm
    r = _season(c, pid, **over)
    assert r.status_code == 201, r.text
    assert r.json()["area_acres"] == acres


def test_bigha_without_factor(farm) -> None:  # AT-14
    c, pid = farm
    r = _season(c, pid, area_value="2", area_unit="bigha")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "BIGHA_FACTOR_REQUIRED"
    assert err["fields"] == {"decimals_per_bigha": "season.err.bigha_factor"}


@pytest.mark.parametrize(("over", "field", "key"), [
    ({"expected_harvest_date": "2027-01-10"}, "expected_harvest_date", "season.err.harvest_after_sowing"),
    ({"expected_output_low": "4000"}, "expected_output_expected", "season.err.range_order"),
    ({"expected_price_high": "30"}, "expected_price_high", "season.err.range_order"),
    ({"area_value": "0"}, "area_value", "season.err.positive"),
    ({"season_name": "summer"}, "season_name", None),
])
def test_season_validation(farm, over, field, key) -> None:
    c, pid = farm
    r = _season(c, pid, **over)
    assert r.status_code == 422, r.text
    fields = r.json()["error"]["fields"]
    assert field in fields
    if key:
        assert fields[field] == key


def test_season_endpoints_on_shop_are_403(client) -> None:  # AT-15
    owner(client)
    shop = create_profile(client)["id"]
    sid = uuid.uuid4()
    for method, url in [
        ("get", f"/api/v1/profiles/{shop}/seasons"),
        ("post", f"/api/v1/profiles/{shop}/seasons"),
        ("get", f"/api/v1/profiles/{shop}/seasons/{sid}"),
        ("get", f"/api/v1/profiles/{shop}/seasons/{sid}/summary"),
        ("post", f"/api/v1/profiles/{shop}/seasons/{sid}/harvest"),
    ]:
        r = getattr(client, method)(url, **({"json": D3_SEASON} if method == "post" else {}))
        assert r.status_code == 403, (method, url, r.text)
        assert r.json()["error"]["code"] == "PROFILE_TYPE_MISMATCH"


def test_cost_items_paid_entry_and_summary(farm) -> None:  # FR-SEA-04/05/07
    c, pid = farm
    sid = _season(c, pid).json()["id"]
    items = {}
    for cat, cost in D3_COSTS:
        r = c.post(f"/api/v1/profiles/{pid}/seasons/{sid}/cost-items", json={
            "category": cat, "item_name": f"{cat.title()} (DEMO)", "quantity": "1", "unit": "lot",
            "unit_cost": str(cost)})
        assert r.status_code == 201, r.text
        assert r.json()["total_cost"] == f"{cost}.00"
        items[cat] = r.json()["id"]

    # "Paid" seed → a ledger entry linked to the cost item; season comes from the item.
    r = c.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": "purchase_cash", "amount": "4500", "value_date": clock.today().isoformat(),
        "category": "seed", "season_cost_item_id": items["seed"]})
    assert r.status_code == 201, r.text
    assert r.json()["season_id"] == sid
    # an unpaid credit purchase is not "paid"
    c.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": "purchase_credit", "amount": "1000", "value_date": clock.today().isoformat(), "season_id": sid})

    s = c.get(f"/api/v1/profiles/{pid}/seasons/{sid}/summary").json()
    assert s["planned_cost_total"] == "65000.00"
    assert s["paid_cost_total"] == "4500.00"
    assert s["actual_sales_total"] == "0.00"
    assert s["break_even_price_per_kg"] == "19.70"
    assert s["loan_cover_price_per_kg"] is None and s["labels"] == ["owner_estimates"]

    detail = c.get(f"/api/v1/profiles/{pid}/seasons/{sid}").json()
    paid = {i["category"]: i["paid_total"] for i in detail["cost_items"]}
    assert paid["seed"] == "4500.00" and paid["labour"] == "0.00"

    seasonal = c.get(f"/api/v1/profiles/{pid}/transactions", params={"season_id": sid}).json()
    assert seasonal["total"] == 2

    # an item paid by an entry cannot be deleted; an unused one can
    used = c.delete(f"/api/v1/profiles/{pid}/seasons/{sid}/cost-items/{items['seed']}")
    assert used.status_code == 409 and used.json()["error"]["message_key"] == "season.err.cost_item_in_use"
    assert c.delete(f"/api/v1/profiles/{pid}/seasons/{sid}/cost-items/{items['transport']}").status_code == 204
    patched = c.patch(f"/api/v1/profiles/{pid}/seasons/{sid}/cost-items/{items['labour']}",
                      json={"quantity": "2", "unit_cost": "11500"})
    assert patched.status_code == 200 and patched.json()["total_cost"] == "23000.00"


def test_cost_item_link_rules(farm) -> None:
    c, pid = farm
    sid = _season(c, pid).json()["id"]
    other = _season(c, pid, crop_name="Potato", season_name="winter_vegetables").json()["id"]
    iid = c.post(f"/api/v1/profiles/{pid}/seasons/{sid}/cost-items", json={
        "category": "seed", "item_name": "Seed", "quantity": "1", "unit": "lot", "unit_cost": "100"}).json()["id"]
    base = {"amount": "100", "value_date": clock.today().isoformat(), "season_cost_item_id": iid}
    r = c.post(f"/api/v1/profiles/{pid}/transactions", json={"txn_type": "sale_cash", **base})
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"season_cost_item_id": "entry.err.cost_item_link_type"}
    r = c.post(f"/api/v1/profiles/{pid}/transactions", json={"txn_type": "purchase_cash", "season_id": other, **base})
    assert r.status_code == 422 and r.json()["error"]["fields"] == {"season_cost_item_id": "entry.err.cost_item_season"}


def test_harvest_and_patch(farm) -> None:  # FR-SEA-06
    c, pid = farm
    sid = _season(c, pid, sowing_date=(clock.today() - timedelta(days=100)).isoformat(),
                  expected_harvest_date=(clock.today() + timedelta(days=5)).isoformat()).json()["id"]
    assert c.patch(f"/api/v1/profiles/{pid}/seasons/{sid}", json={"status": "growing"}).json()["status"] == "growing"
    r = c.post(f"/api/v1/profiles/{pid}/seasons/{sid}/harvest",
               json={"actual_harvest_date": clock.today().isoformat(), "actual_output": "3100"})
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["actual_output"]) == ("harvested", "3100.00")
    future = c.post(f"/api/v1/profiles/{pid}/seasons/{sid}/harvest",
                    json={"actual_harvest_date": (clock.today() + timedelta(days=3)).isoformat(),
                          "actual_output": "1"})
    assert future.status_code == 422
    # switching to bigha through PATCH without a factor is refused too
    r = c.patch(f"/api/v1/profiles/{pid}/seasons/{sid}", json={"area_unit": "bigha"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "BIGHA_FACTOR_REQUIRED"


def test_season_sales_count_in_summary(farm) -> None:
    c, pid = farm
    sid = _season(c, pid).json()["id"]
    c.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": "sale_cash", "amount": "30000", "value_date": clock.today().isoformat(), "season_id": sid})
    assert c.get(f"/api/v1/profiles/{pid}/seasons/{sid}/summary").json()["actual_sales_total"] == "30000.00"
