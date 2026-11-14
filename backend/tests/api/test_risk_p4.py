"""P4 through the real API on the real seed: supplier concentration (#24),
auto scenarios (golden D1/D3), news matching + proposals (golden §4.2/4.4),
confirm/dismiss (AT-21, DEC-30), empty news (AT-22), import-news CLI."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app import demo
from app.cli import main as cli
from app.core.clock import today
from tests.helpers import create_profile, login, owner

DEMO_PW = "test-only-demo-2026"  # isolated test DB only
REPO = Path(__file__).resolve().parents[3]
FORBIDDEN = ("approved", "eligible", "credit score", "probability of default")


@pytest.fixture()
def seeded(clean_db: str) -> str:
    engine = create_engine(clean_db)
    with engine.begin() as conn:
        demo.seed(conn, DEMO_PW)
    engine.dispose()
    return clean_db


def plus(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


def demo_profile(c, phone: str, name: str) -> dict:
    login(c, phone, DEMO_PW)
    return next(p for p in c.get("/api/v1/profiles").json()["items"] if p["display_name"] == name)


def assess(c, pid: str) -> dict:
    rid = c.get(f"/api/v1/profiles/{pid}/financing-requests").json()["items"][0]["id"]
    r = c.post(f"/api/v1/profiles/{pid}/financing-requests/{rid}/assessments")
    assert r.status_code == 201, r.text
    return r.json()


def by(scenarios: list[dict], kind: str, origin: str = "auto", **params) -> dict:
    return next(s for s in scenarios if s["scenario_type"] == kind and s["origin"] == origin
                and all(s["parameters"].get(k) == v for k, v in params.items()))


# ----------------------------------------------------------------- P4-T01 concentration
def test_d1_supplier_concentration(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    c = client.get(f"/api/v1/profiles/{p['id']}/supplier-concentration").json()
    assert (c["basis"], c["window_days"], c["total_purchases"]) == ("linked_purchases", 56, "752000.00")
    assert [(s["display_name"], s["amount"], s["share_pct"]) for s in c["suppliers"]] == [
        ("Supplier A (DEMO wholesaler)", "488800.00", "65.0"), ("Supplier B (DEMO)", "188000.00", "25.0"),
        ("Supplier C (DEMO)", "75200.00", "10.0")]
    assert (c["top_share_pct"], c["high_dependency"], c["threshold_pct"], c["note_key"]) == ("65.0", True, "50.0", None)


def test_concentration_none_owner_reported_and_sparse(client) -> None:  # FR-SUP-05/06
    owner(client)
    pid = create_profile(client)["id"]
    url = f"/api/v1/profiles/{pid}/supplier-concentration"
    c = client.get(url).json()
    assert (c["basis"], c["note_key"], c["suppliers"], c["high_dependency"]) == ("none", "supplier.add_prompt", [], False)
    s1 = client.post(f"/api/v1/profiles/{pid}/suppliers",
                     json={"display_name": "Wholesaler", "declared_purchase_share_pct": "40"}).json()
    client.post(f"/api/v1/profiles/{pid}/suppliers", json={"display_name": "Mill", "declared_purchase_share_pct": "30"})
    c = client.get(url).json()
    assert (c["basis"], c["total_purchases"], c["top_share_pct"], c["high_dependency"]) == \
        ("owner_reported", None, "40.0", False)
    assert c["note_key"] == "supplier.sparse"  # sparse data is never shown as low risk
    # one linked purchase is still < 2 -> owner-reported stays
    client.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": "purchase_cash", "amount": "5000", "value_date": (today() - timedelta(days=3)).isoformat(),
        "supplier_id": s1["id"], "client_request_id": "21111111-1111-4111-8111-111111111111"})
    assert client.get(url).json()["basis"] == "owner_reported"
    client.post(f"/api/v1/profiles/{pid}/transactions", json={
        "txn_type": "purchase_cash", "amount": "7000", "value_date": (today() - timedelta(days=2)).isoformat(),
        "supplier_id": s1["id"], "client_request_id": "31111111-1111-4111-8111-111111111111"})
    c = client.get(url).json()
    assert (c["basis"], c["top_share_pct"], c["high_dependency"], c["note_key"]) == \
        ("linked_purchases", "100.0", True, None)


# ----------------------------------------------------------------- P4-T02/T03 auto scenarios
def test_d1_auto_scenarios_golden_and_status_unchanged(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    a = assess(client, p["id"])
    assert a["status"] == "ready_for_lender_review"  # DEC-30: shortfalls in what-ifs never change it
    assert a["flags"] == ["request_exceeds_gap", "high_supplier_dependency", "scenario_shortfall"]
    sc = a["scenarios"]
    d7 = by(sc, "supplier_delay", days=7)
    assert d7["status"] == "computed" and d7["parameters"]["share"] == "0.6500" and d7["parameters"]["start"] == plus(0)
    assert d7["supplier_name"] == "Supplier A (DEMO wholesaler)" and d7["assumption_key"] == "scn.delay"
    assert d7["result"]["first_shortfall"] == {"date": plus(7), "balance_after": "623.10",
                                               "shortfall_vs_reserve": "9376.90"}
    d14 = by(sc, "supplier_delay", days=14)["result"]
    assert d14["first_shortfall"] == {"date": plus(7), "balance_after": "-2377.35", "shortfall_vs_reserve": "12377.35"}
    assert d14["min_balance_after_payment"] == "-16832.08"
    pr = by(sc, "input_price_rise")["result"]
    assert pr["first_shortfall"] == {"date": plus(14), "balance_after": "5534.88", "shortfall_vs_reserve": "4465.12"}
    assert pr["min_balance_after_payment"] == "-50635.67" and pr["checks_count"] == 12
    assert all(s["label_key"] == "scn.whatif" for s in sc)
    blob = str(a).lower()
    assert not any(w in blob for w in FORBIDDEN)


def test_d3_crop_scenarios_golden(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Rice Farm")
    a = assess(client, p["id"])
    assert a["status"] == "ready_for_lender_review"
    sc = a["scenarios"]
    price = by(sc, "harvest_price_fall")["result"]
    assert (price["available_at_due_date"], price["surplus_or_shortfall"], price["covered"]) == ("53260.00", "10860.00", True)
    yld = by(sc, "yield_shortfall")["result"]
    assert (yld["available_at_due_date"], yld["surplus_or_shortfall"], yld["loan_cover_price_per_unit"]) == \
        ("49480.00", "7080.00", "24.72")
    inp = by(sc, "input_price_rise")
    assert inp["assumption_key"] == "scn.input_cost"
    assert (inp["result"]["pre_harvest_shortfall"], inp["result"]["available_at_due_date"], inp["result"]["covered"]) == \
        ("1275.00", "63325.00", True)
    assert "pre_harvest_cash_shortfall" in a["flags"] and "scenario_shortfall" not in a["flags"]


def test_d4_insufficient_has_no_scenarios(seeded, client) -> None:
    p = demo_profile(client, "01900000004", "Selina Tailoring")
    a = assess(client, p["id"])
    assert a["status"] == "insufficient_information" and a["scenarios"] == []


# ----------------------------------------------------------------- P4-T05/T06 news
def test_d1_news_blockade_via_supplier_not_dhamrai_flood(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    a = assess(client, p["id"])
    sig = a["news_signals"]
    assert len(sig) == 1  # the Dhamrai flood is crop-field news; Supplier C (spices) there is not affected
    s = sig[0]
    assert s["event_type"] == "hartal_road_blockade" and s["is_demo"] is True
    assert "supplier_location" in s["match_reasons"] and s["matched_supplier"] == "Supplier A (DEMO wholesaler)"
    assert (s["corroboration"], s["source_name"]) == ("single_source", "DEMO (fictional)")
    prop = next(x for x in a["scenarios"] if x["origin"] == "news")
    assert prop["id"] == s["proposed_scenario_id"] and prop["status"] == "proposed" and prop["result"] is None
    assert (prop["scenario_type"], prop["parameters"]["days"], prop["parameters"]["start"]) == \
        ("supplier_delay", 7, plus(0))
    live = client.get(f"/api/v1/profiles/{p['id']}/news-signals").json()["items"]
    assert [x["id"] for x in live] == [s["id"]]


def test_d3_news_flood_via_upazila_proposes_yield(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Rice Farm")
    a = assess(client, p["id"])
    assert len(a["news_signals"]) == 1
    s = a["news_signals"][0]
    assert s["event_type"] == "flood_waterlogging" and "location" in s["match_reasons"]
    prop = next(x for x in a["scenarios"] if x["origin"] == "news")
    assert (prop["scenario_type"], prop["parameters"]["pct"], prop["status"]) == ("yield_shortfall", "0.20", "proposed")


def test_at21_confirm_computes_and_status_unchanged(seeded, client) -> None:
    p = demo_profile(client, "01900000001", "Rahim Store")
    a = assess(client, p["id"])
    prop = next(x for x in a["scenarios"] if x["origin"] == "news")
    r = client.post(f"/api/v1/profiles/{p['id']}/scenarios/{prop['id']}/confirm")
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "computed"
    assert done["result"] == by(a["scenarios"], "supplier_delay", days=7)["result"]  # same as the auto 7-day case
    after = client.get(f"/api/v1/profiles/{p['id']}/assessments/{a['id']}").json()
    assert after["status"] == a["status"] == "ready_for_lender_review"
    assert "news_signal_single_source" in after["flags"]
    assert after["news_signals"][0]["scenario_status"] == "computed"
    again = client.post(f"/api/v1/profiles/{p['id']}/scenarios/{prop['id']}/confirm")
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT"
    auto = by(a["scenarios"], "supplier_delay", days=14)
    assert client.post(f"/api/v1/profiles/{p['id']}/scenarios/{auto['id']}/dismiss").status_code == 409


def test_dismiss_and_stale_and_isolation(seeded, make_client) -> None:
    c = make_client()
    farm = demo_profile(c, "01900000001", "Rahim Rice Farm")
    a = assess(c, farm["id"])
    prop = next(x for x in a["scenarios"] if x["origin"] == "news")
    other = make_client()
    owner(other, 9)
    mine = create_profile(other, "Other Shop")
    assert other.post(f"/api/v1/profiles/{farm['id']}/scenarios/{prop['id']}/dismiss").status_code == 404
    assert other.post(f"/api/v1/profiles/{mine['id']}/scenarios/{prop['id']}/dismiss").status_code == 404
    shop = demo_profile(c, "01900000001", "Rahim Store")
    a2 = assess(c, shop["id"])
    prop2 = next(x for x in a2["scenarios"] if x["origin"] == "news")
    c.post(f"/api/v1/profiles/{shop['id']}/transactions", json={
        "txn_type": "sale_cash", "amount": "100", "value_date": today().isoformat(),
        "client_request_id": "41111111-1111-4111-8111-111111111111"})
    stale = c.post(f"/api/v1/profiles/{shop['id']}/scenarios/{prop2['id']}/confirm")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "ASSESSMENT_STALE"
    d = c.post(f"/api/v1/profiles/{farm['id']}/scenarios/{prop['id']}/dismiss")
    assert d.status_code == 200 and d.json()["status"] == "dismissed"
    assert c.get(f"/api/v1/profiles/{farm['id']}/assessments/{a['id']}").json()["status"] == a["status"]


def test_at22_empty_news_table(seeded, client) -> None:  # FR-NEWS-06
    engine = create_engine(seeded)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM news_events"))
    engine.dispose()
    p = demo_profile(client, "01900000001", "Rahim Store")
    assert client.get(f"/api/v1/profiles/{p['id']}/news-signals").json() == {"items": []}
    a = assess(client, p["id"])
    assert a["news_signals"] == [] and a["status"] == "ready_for_lender_review"
    assert not [s for s in a["scenarios"] if s["origin"] == "news"]


# ----------------------------------------------------------------- P4-T04 import-news
HEADER = ("headline,headline_lang,summary,source_name,source_url,published_date,event_date,event_type,"
          "districts,upazilas,sectors,commodities,is_demo,curated_by\n")


def test_import_news_validates_dedups_and_is_idempotent(clean_db, tmp_path, capsys) -> None:
    d = (today() - timedelta(days=2)).isoformat()
    f = tmp_path / "news.csv"
    f.write_text(HEADER + "\n".join([
        f"Road blocked near test market,en,Short summary,Paper A,https://a.example/1,{d},{d},hartal_road_blockade,"
        "Gazipur,Kaliakair,,,false,tester",
        f"Road blocked near test market (B),en,Same event,Paper B,https://b.example/2,{d},{d},hartal_road_blockade,"
        "Gazipur,Kaliakair,,,false,tester",
        f"No URL real news,en,x,Paper C,,{d},,price_shock,Dhaka,,grocery,rice,false,tester",
        f"Bad type row,en,x,Paper D,https://d.example,{d},,earthquake,Dhaka,,,,false,tester",
        f"Fake demo source,en,x,Paper E,,{d},,price_shock,Dhaka,,,,true,tester",
        f"Future news,en,x,Paper F,https://f.example,{(today() + timedelta(days=3)).isoformat()},,price_shock,Dhaka,,,,false,tester",
    ]) + "\n", encoding="utf-8")
    assert cli(["import-news", str(f)]) == 1  # some rows rejected -> non-zero exit, valid rows kept
    out = capsys.readouterr().out
    assert "1 inserted, 0 updated, 4 rejected" in out
    for line in ("line 4: source_url", "line 5: event_type", "line 6: DEMO rows", "line 7: published_date"):
        assert line in out
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT source_count, source_name, upazilas FROM news_events")).one()
    assert (row.source_count, row.source_name, row.upazilas) == (2, "Paper A", ["Kaliakair"])
    assert cli(["import-news", str(f)]) == 1
    assert "0 inserted, 1 updated" in capsys.readouterr().out
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*), max(source_count) FROM news_events")).one() == (1, 2)
    engine.dispose()


def test_repo_curated_news_csv_imports_cleanly(clean_db, capsys) -> None:  # P4-T08 file stays valid
    assert cli(["import-news", str(REPO / "data" / "news" / "curated_news.csv")]) == 0
    assert "0 rejected" in capsys.readouterr().out
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        n, demo_rows, corroborated = conn.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE is_demo), count(*) FILTER (WHERE source_count >= 2) "
            "FROM news_events")).one()
        urls = conn.execute(text("SELECT count(*) FROM news_events WHERE source_url !~ '^https://'")).scalar()
    engine.dispose()
    assert n >= 5 and demo_rows == 0 and corroborated >= 2 and urls == 0
