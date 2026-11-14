"""AT-08, FR-PROF-01..07."""
from __future__ import annotations

import re

from ..helpers import create_profile, owner


def test_at08_shop_and_farm_under_one_user(client) -> None:
    owner(client)
    shop = create_profile(client, "Rahim Store", "shop")
    farm = create_profile(client, "Rahim Rice Farm", "crop_farm")
    items = client.get("/api/v1/profiles").json()["items"]
    assert [(p["display_name"], p["activity_type"]) for p in items] == [
        ("Rahim Store", "shop"), ("Rahim Rice Farm", "crop_farm")]
    assert shop["id"] != farm["id"] and shop["share_code"] != farm["share_code"]


def test_minimal_profile_and_defaults(client) -> None:  # FR-PROF-02, FR-PROF-06
    owner(client)
    p = create_profile(client)
    assert re.fullmatch(r"[A-HJ-NP-Z2-9]{10}", p["share_code"])
    assert p["household_declared"] is False and p["no_debt_declared"] is False
    assert p["financing_fields_complete"] is False and p["is_demo"] is False


def test_profile_validation(client) -> None:
    owner(client)
    r = client.post("/api/v1/profiles", json={"display_name": "X", "activity_type": "poultry"})
    assert r.status_code == 422
    assert set(r.json()["error"]["fields"]) == {"display_name", "activity_type"}
    assert r.json()["error"]["fields"]["display_name"] == "profile.err.name"


def test_patch_progressive_fields_and_household(client) -> None:
    owner(client)
    p = create_profile(client)
    r = client.patch(f"/api/v1/profiles/{p['id']}", json={
        "district": "Dhaka", "upazila": "Savar", "business_category": "grocery",
        "household_withdrawal_monthly": "১৫,০০০"})
    assert r.status_code == 200
    body = r.json()
    assert body["household_withdrawal_monthly"] == "15000.00" and body["household_declared"] is True
    assert body["financing_fields_complete"] is True
    # declaring zero is a valid declaration (DEC-37)
    body = client.patch(f"/api/v1/profiles/{p['id']}", json={"household_withdrawal_monthly": 0}).json()
    assert body["household_withdrawal_monthly"] == "0.00" and body["household_declared"] is True
    r = client.patch(f"/api/v1/profiles/{p['id']}", json={"household_withdrawal_monthly": "-5"})
    assert r.status_code == 422


def test_regenerate_share_code(client) -> None:  # FR-PROF-07
    owner(client)
    p = create_profile(client)
    r = client.post(f"/api/v1/profiles/{p['id']}/share-code/regenerate")
    assert r.status_code == 200
    new = r.json()["share_code"]
    assert new != p["share_code"]
    assert client.get(f"/api/v1/profiles/{p['id']}").json()["share_code"] == new
