"""Plan Ultra F4 supply graph through the API on the real seed (D1 Rahim Store, D3 Rahim Rice Farm).
The what-if on a node whose exposure equals the top supplier's share must reproduce the golden D1 delay numbers."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from sqlalchemy import create_engine

from app import demo
from app.core.clock import today
from tests.helpers import login, owner

DEMO_PW = "test-only-demo-2026"  # isolated test DB only
NAMES = ("Supplier A (DEMO wholesaler)", "Supplier B (DEMO)", "Supplier C (DEMO)")


@pytest.fixture()
def seeded(clean_db: str) -> str:
    engine = create_engine(clean_db)
    with engine.begin() as conn:
        demo.seed(conn, DEMO_PW)
    engine.dispose()
    return clean_db


def plus(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


def profile(c, name: str) -> dict:
    return next(p for p in c.get("/api/v1/profiles").json()["items"] if p["display_name"] == name)


def node(g: dict, nid: str) -> dict:
    return next(n for n in g["nodes"] if n["id"] == nid)


def test_d1_graph_exposures(seeded, client) -> None:
    login(client, "01900000001", DEMO_PW)
    p = profile(client, "Rahim Store")
    g = client.get(f"/api/v1/profiles/{p['id']}/supply-graph").json()
    assert g["basis"] == "linked_purchases" and g["whatif_available"] is True
    assert {n["label"] for n in g["nodes"] if n["kind"] == "supplier"} == set(NAMES)  # owner sees own names
    assert node(g, "area:gazipur/kaliakair")["exposure_pct"] == "65.0"
    assert node(g, "area:dhaka/savar")["exposure_pct"] == "25.0"
    assert node(g, "good:lentils")["exposure_pct"] == "90.0"
    news = [n for n in g["nodes"] if n["kind"] == "news"]
    assert len(news) == 1 and news[0]["exposure_pct"] == "65.0" and news[0]["is_demo"]  # Kaliakair blockade only
    assert {"from": news[0]["id"], "to": "area:gazipur/kaliakair", "relation": "affects"} in g["edges"]


def test_whatif_reproduces_golden_delay_and_never_changes_status(seeded, client) -> None:
    login(client, "01900000001", DEMO_PW)
    pid = profile(client, "Rahim Store")["id"]
    url = f"/api/v1/profiles/{pid}/supply-graph/whatif"
    first = client.get(url, params={"node": "area:gazipur/kaliakair"}).json()
    assert first["reason"] == "no_check_yet" and first["result"] is None

    rid = client.get(f"/api/v1/profiles/{pid}/financing-requests").json()["items"][0]["id"]
    a = client.post(f"/api/v1/profiles/{pid}/financing-requests/{rid}/assessments").json()
    w7 = client.get(url, params={"node": "area:gazipur/kaliakair", "days": 7}).json()
    assert w7["exposure_pct"] == "65.0" and w7["result"]["first_shortfall"] == {
        "date": plus(7), "balance_after": "623.10", "shortfall_vs_reserve": "9376.90"}
    w14 = client.get(url, params={"node": "area:gazipur/kaliakair", "days": 14}).json()
    assert w14["result"]["min_balance_after_payment"] == "-16832.08"
    spices = client.get(url, params={"node": "good:spices"}).json()  # 10 % only
    assert spices["exposure_pct"] == "10.0" and spices["result"] is not None

    latest = client.get(f"/api/v1/profiles/{pid}/financing-requests/{rid}/assessments/latest").json()
    assert latest["id"] == a["id"] and latest["status"] == "ready_for_lender_review"  # DEC-30: nothing stored

    assert client.get(url, params={"node": "area:dhaka/savar", "days": 10}).status_code == 422
    assert client.get(url, params={"node": "area:nowhere"}).status_code == 404


def test_farm_graph_and_shop_only_whatif(seeded, client) -> None:
    login(client, "01900000001", DEMO_PW)
    farm = profile(client, "Rahim Rice Farm")
    g = client.get(f"/api/v1/profiles/{farm['id']}/supply-graph").json()
    assert g["whatif_available"] is False
    assert {"from": "business", "to": "good:rice", "relation": "grows"} in g["edges"]
    flood = next(n for n in g["nodes"] if n["kind"] == "news")  # DEMO Dhamrai flood matched via upazila
    assert {"from": flood["id"], "to": "area:dhaka/dhamrai", "relation": "affects"} in g["edges"]
    r = client.get(f"/api/v1/profiles/{farm['id']}/supply-graph/whatif", params={"node": "good:rice"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "PROFILE_TYPE_MISMATCH"


def test_other_owner_gets_404(seeded, client, make_client) -> None:
    login(client, "01900000001", DEMO_PW)
    pid = profile(client, "Rahim Store")["id"]
    other = make_client()
    owner(other)
    assert other.get(f"/api/v1/profiles/{pid}/supply-graph").status_code == 404
    assert other.get(f"/api/v1/profiles/{pid}/supply-graph/whatif", params={"node": "business"}).status_code == 404


def test_lender_snapshot_carries_the_graph_with_labels_only(seeded, client, make_client) -> None:
    lender = make_client()
    login(lender, "01900000101", DEMO_PW)
    sections = ["profile_summary", "financing_request", "supplier_risk"]
    lender.post("/api/v1/lender/access-requests", json={"share_code": "7KQ2M9XA4P", "requested_sections": sections})
    login(client, "01900000001", DEMO_PW)
    pid = profile(client, "Rahim Store")["id"]
    rid = client.get(f"/api/v1/profiles/{pid}/financing-requests").json()["items"][0]["id"]
    client.post(f"/api/v1/profiles/{pid}/financing-requests/{rid}/assessments")
    cid = next(x for x in client.get(f"/api/v1/profiles/{pid}/consents").json()["items"] if x["status"] == "requested")["id"]
    ok = client.post(f"/api/v1/profiles/{pid}/consents/{cid}/approve",
                     json={"approved_sections": sections, "financing_request_id": rid, "valid_days": 14})
    assert ok.status_code == 200, ok.text
    case = lender.get(f"/api/v1/lender/cases/{cid}").json()
    graph = case["snapshot"]["sections"]["supplier_risk"]["graph"]
    assert {n["label"] for n in graph["nodes"] if n["kind"] == "supplier"} == {"Supplier 1", "Supplier 2", "Supplier 3"}
    assert graph["whatif_available"] is False
    assert not any(n in json.dumps(case, ensure_ascii=False) for n in NAMES)  # SEC-12 holds with the graph
