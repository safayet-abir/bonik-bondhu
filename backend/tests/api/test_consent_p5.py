"""P5 consent + lender review on the real seed: AT-23..26, SEC-08..13,
snapshot integrity (Testing §7), read audit, expiry with a clock override."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from app import demo
from app.core import clock
from app.services import snapshot_service
from tests.helpers import login, owner

DEMO_PW = "test-only-demo-2026"  # isolated test DB only
NASRIN, TANVIR, OTHER_ORG = "01900000101", "01900000102", "01900000103"
D1_CODE = "7KQ2M-9XA4P"
SUPPLIER_NAMES = ("Supplier A (DEMO wholesaler)", "Supplier B (DEMO)", "Supplier C (DEMO)")


@pytest.fixture()
def seeded(clean_db: str) -> str:
    engine = create_engine(clean_db)
    with engine.begin() as conn:
        demo.seed(conn, DEMO_PW)
    engine.dispose()
    return clean_db


def as_owner(c, name="Rahim Store", phone="01900000001") -> dict:
    login(c, phone, DEMO_PW)
    return next(p for p in c.get("/api/v1/profiles").json()["items"] if p["display_name"] == name)


def request_access(c, code=D1_CODE, sections=("profile_summary", "financing_request", "obligations")):
    r = c.post("/api/v1/lender/access-requests",
               json={"share_code": code, "requested_sections": list(sections), "message": "Please share (DEMO)."})
    assert r.status_code == 202, r.text
    return r.json()


def assess(c, pid) -> tuple[str, dict]:
    rid = c.get(f"/api/v1/profiles/{pid}/financing-requests").json()["items"][0]["id"]
    a = c.post(f"/api/v1/profiles/{pid}/financing-requests/{rid}/assessments")
    assert a.status_code == 201, a.text
    return rid, a.json()


def pending(c, pid) -> dict:
    return next(x for x in c.get(f"/api/v1/profiles/{pid}/consents").json()["items"] if x["status"] == "requested")


def approve(c, pid, cid, rid, sections, days=14):
    return c.post(f"/api/v1/profiles/{pid}/consents/{cid}/approve",
                  json={"approved_sections": sections, "financing_request_id": rid, "valid_days": days})


def audit_count(db_url: str, action: str, outcome: str | None = None) -> int:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        q = "SELECT count(*) FROM audit_logs WHERE action = :a" + (" AND outcome = :o" if outcome else "")
        n = conn.execute(text(q), {"a": action, "o": outcome}).scalar()
    engine.dispose()
    return n


@pytest.fixture()
def shared(seeded, make_client):
    """Nasrin requests D1; Rahim approves a 3-section subset for 14 days."""
    lender, own = make_client(), make_client()
    login(lender, NASRIN, DEMO_PW)
    request_access(lender)
    p = as_owner(own)
    rid, a = assess(own, p["id"])
    cid = pending(own, p["id"])["id"]
    r = approve(own, p["id"], cid, rid, ["profile_summary", "financing_request", "obligations"])
    assert r.status_code == 200, r.text
    return {"lender": lender, "owner": own, "pid": p["id"], "rid": rid, "cid": cid, "approved": r.json(),
            "make_client": make_client, "db": seeded}


# ----------------------------------------------------------------- SEC-13 / FR-CON-01
def test_sec13_identical_reply_and_row_only_for_valid_code(seeded, client) -> None:
    login(client, NASRIN, DEMO_PW)
    bad = request_access(client, "ZZZZZ-ZZZZZ")
    good = request_access(client, " 7kq2m 9xa4p ")  # spaces/dashes/case ignored
    assert bad == good == {"message_key": "lender.request_sent_if_valid"}
    again = request_access(client)  # an open request from this org already exists -> no duplicate
    assert again == good
    engine = create_engine(seeded)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM consents")).scalar() == 1
    engine.dispose()
    assert audit_count(seeded, "consent.request", "denied") == 2
    pend = client.get("/api/v1/lender/cases?status=pending").json()["items"]
    assert len(pend) == 1 and pend[0]["applicant"] is None  # identity hidden until approval


def test_access_request_validation_and_rate_limit(seeded, client) -> None:
    login(client, NASRIN, DEMO_PW)
    r = client.post("/api/v1/lender/access-requests", json={"share_code": D1_CODE, "requested_sections": ["passwords"]})
    assert r.status_code == 422
    for _ in range(20):  # 20 per hour per officer are fine (a 422 body never reaches the limiter)
        request_access(client, "ZZZZZ-ZZZZZ")
    r = client.post("/api/v1/lender/access-requests",
                    json={"share_code": D1_CODE, "requested_sections": ["profile_summary"]})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


# ----------------------------------------------------------------- approve rules
def test_approve_rules(seeded, make_client) -> None:
    lender, own = make_client(), make_client()
    login(lender, NASRIN, DEMO_PW)
    request_access(lender)
    p = as_owner(own)
    rid = own.get(f"/api/v1/profiles/{p['id']}/financing-requests").json()["items"][0]["id"]
    c = pending(own, p["id"])
    assert c["lender_organization"] == {"name": "DEMO Bank Ltd (fictional)", "is_demo": True}
    assert c["requested_by"] and c["requested_sections"] == ["profile_summary", "financing_request", "obligations"]
    # no assessment yet -> 409
    r = approve(own, p["id"], c["id"], rid, ["profile_summary", "financing_request"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "ASSESSMENT_STALE"
    assess(own, p["id"])
    assert approve(own, p["id"], c["id"], rid, ["profile_summary"]).status_code == 422  # financing_request required
    assert approve(own, p["id"], c["id"], rid, ["profile_summary", "financing_request", "season_summary"]) \
        .status_code == 422  # farm-only section on a shop
    assert approve(own, p["id"], c["id"], rid, ["profile_summary", "financing_request"], days=10).status_code == 422
    # data changed after the check -> stale -> 409
    own.post(f"/api/v1/profiles/{p['id']}/transactions", json={
        "txn_type": "sale_cash", "amount": "100", "value_date": clock.today().isoformat(),
        "client_request_id": "51111111-1111-4111-8111-111111111111"})
    assert approve(own, p["id"], c["id"], rid, ["profile_summary", "financing_request"]).status_code == 409
    # other owner cannot see or act on it
    other = make_client()
    owner(other, 5)
    assert other.post(f"/api/v1/profiles/{p['id']}/consents/{c['id']}/decline").status_code == 404
    d = own.post(f"/api/v1/profiles/{p['id']}/consents/{c['id']}/decline")
    assert d.status_code == 200 and d.json()["status"] == "declined"
    r = approve(own, p["id"], c["id"], rid, ["profile_summary", "financing_request"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONSENT_STATE_INVALID"


# ----------------------------------------------------------------- AT-23 / SEC-12 / integrity
def test_at23_lender_reads_only_approved_sections(shared) -> None:
    lender = shared["lender"]
    f = lender.get(f"/api/v1/lender/cases/{shared['cid']}")
    assert f.status_code == 200, f.text
    case = f.json()
    snap = case["snapshot"]
    assert snap["schema"] == "bb-report-v1" and snap["is_demo"] is True
    assert set(snap["sections"]) == {"profile_summary", "financing_request", "obligations"}
    assert "supplier_risk" not in json.dumps(snap)
    # SUG-58: public World Bank figures beside the snapshot, never inside it (the hash covers owner data only)
    assert len(case["economy_context"]["indicators"]) == 4 and "economy" not in json.dumps(snap)
    blob = json.dumps(case, ensure_ascii=False)
    assert not any(n in blob for n in SUPPLIER_NAMES)  # SEC-12
    assert "phone" not in blob and "@demo.invalid" not in blob
    fr = snap["sections"]["financing_request"]
    assert (fr["requested_amount"], fr["funding_gap"], fr["assessment"]["status"]) == \
        ("200000.00", "150000.00", "ready_for_lender_review")
    assert fr["proposal"]["label"] == "owner_proposal_not_lender_offer"
    assert {s["supplier"] for s in fr["assessment"]["scenarios"] if s["supplier"]} == {"Supplier 1"}
    assert snap["sections"]["obligations"]["no_debt_declared"] is True
    assert "lender" in snap["sections"]["obligations"]["cib_notice"]
    c = case["consent"]
    assert c["version"] == 1 and c["hash_verified"] is True and c["snapshot_sha256"] == \
        shared["approved"]["report"]["snapshot_sha256"] == snapshot_service.sha256(snap)
    assert case["cib_notice_key"] == "debt.cib" and case["review"]["status"] == "under_review"
    assert audit_count(shared["db"], "consent.read", "success") == 1
    act = shared["owner"].get(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/activity").json()
    assert len(act["reads"]) == 1 and act["reads"][0]["organization"] == "DEMO Bank Ltd (fictional)"
    active = lender.get("/api/v1/lender/cases?status=active").json()["items"]
    assert active[0]["applicant"]["display_name"] == "Rahim Store" and active[0]["requested_amount"] == "200000.00"
    assert active[0]["assessment_status"] == "ready_for_lender_review" and active[0]["last_read_at"]


def test_snapshot_tamper_detected_and_supplier_labels(seeded, make_client) -> None:
    lender, own = make_client(), make_client()
    login(lender, NASRIN, DEMO_PW)
    request_access(lender, sections=("profile_summary", "financing_request", "supplier_risk", "news_signals",
                                     "money_summary", "forecast", "transaction_list"))
    p = as_owner(own)
    rid, _ = assess(own, p["id"])
    cid = pending(own, p["id"])["id"]
    secs = ["profile_summary", "money_summary", "forecast", "financing_request", "supplier_risk", "news_signals",
            "transaction_list"]
    assert approve(own, p["id"], cid, rid, secs).status_code == 200
    case = lender.get(f"/api/v1/lender/cases/{cid}").json()
    blob = json.dumps(case, ensure_ascii=False)
    assert not any(n in blob for n in SUPPLIER_NAMES)  # SEC-12 also with supplier_risk + news + entries
    sr = case["snapshot"]["sections"]["supplier_risk"]
    assert [(s["label"], s["share_pct"]) for s in sr["suppliers"]] == \
        [("Supplier 1", "65.0"), ("Supplier 2", "25.0"), ("Supplier 3", "10.0")] and sr["high_dependency"]
    assert case["snapshot"]["sections"]["news_signals"][0]["matched_supplier"] == "Supplier 1"
    assert case["snapshot"]["sections"]["forecast"]["weekly_net"]["expected"] == "32312.50"
    assert {t["supplier"] for t in case["snapshot"]["sections"]["transaction_list"]} >= {"Supplier 1", "Supplier 3"}
    # stored snapshot tampering is detected by verify_snapshot()
    engine = create_engine(seeded)
    with engine.connect() as conn:
        snap, h = conn.execute(text("SELECT snapshot, snapshot_sha256 FROM shared_reports")).one()
    engine.dispose()
    assert snapshot_service.verify_snapshot(snap, h)
    snap["sections"]["financing_request"]["requested_amount"] = "1.00"
    assert not snapshot_service.verify_snapshot(snap, h)


# ----------------------------------------------------------------- SEC-08..11
def test_sec08_pending_and_sec09_other_org(seeded, make_client) -> None:
    lender = make_client()
    login(lender, NASRIN, DEMO_PW)
    request_access(lender)
    cid = lender.get("/api/v1/lender/cases?status=pending").json()["items"][0]["consent_id"]
    r = lender.get(f"/api/v1/lender/cases/{cid}")
    assert r.status_code == 403 and r.json()["error"]["code"] == "CONSENT_REQUIRED"
    other = make_client()
    login(other, OTHER_ORG, DEMO_PW)
    assert other.get(f"/api/v1/lender/cases/{cid}").status_code == 404
    assert other.get("/api/v1/lender/cases").json()["items"] == []
    assert audit_count(seeded, "consent.read_denied", "denied") == 2


def test_sec09_other_org_blocked_on_approved_case_same_org_colleague_allowed(shared) -> None:
    other = shared["make_client"]()
    login(other, OTHER_ORG, DEMO_PW)
    assert other.get(f"/api/v1/lender/cases/{shared['cid']}").status_code == 404
    r = other.post(f"/api/v1/lender/cases/{shared['cid']}/events", json={"event_type": "note", "body": "hello"})
    assert r.status_code == 404
    colleague = shared["make_client"]()
    login(colleague, TANVIR, DEMO_PW)
    assert colleague.get(f"/api/v1/lender/cases/{shared['cid']}").status_code == 200


def test_sec10_revoke_blocks_immediately(shared) -> None:
    own, lender = shared["owner"], shared["lender"]
    r = own.post(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/revoke")
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    g = lender.get(f"/api/v1/lender/cases/{shared['cid']}")
    assert g.status_code == 403 and g.json()["error"]["code"] == "CONSENT_REVOKED"
    e = lender.post(f"/api/v1/lender/cases/{shared['cid']}/events", json={"event_type": "note", "body": "x"})
    assert e.status_code == 403
    assert lender.get("/api/v1/lender/cases?status=closed").json()["items"][0]["status"] == "revoked"
    assert own.post(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/reshare").status_code == 409


def test_sec11_expired_consent_blocked(seeded, make_client) -> None:
    lender, own = make_client(), make_client()
    login(lender, NASRIN, DEMO_PW)
    request_access(lender)
    p = as_owner(own)
    rid, _ = assess(own, p["id"])
    cid = pending(own, p["id"])["id"]
    clock.set_now(datetime.now(UTC) - timedelta(days=7, hours=1))  # approve "7 days and 1 hour ago"
    try:
        assert approve(own, p["id"], cid, rid, ["profile_summary", "financing_request"], days=7).status_code == 200
    finally:
        clock.set_now(None)
    r = lender.get(f"/api/v1/lender/cases/{cid}")
    assert r.status_code == 403 and r.json()["error"]["code"] == "CONSENT_EXPIRED"
    row = own.get(f"/api/v1/profiles/{p['id']}/consents").json()["items"][0]
    assert row["is_expired"] is True and row["status"] == "approved"
    assert lender.get("/api/v1/lender/cases?status=closed").json()["items"][0]["is_expired"] is True


# ----------------------------------------------------------------- AT-24..26
def test_at24_reshare_new_version(shared) -> None:
    own, lender = shared["owner"], shared["lender"]
    own.post(f"/api/v1/profiles/{shared['pid']}/transactions", json={
        "txn_type": "sale_cash", "amount": "500", "value_date": clock.today().isoformat(),
        "client_request_id": "61111111-1111-4111-8111-111111111111"})
    stale = own.post(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/reshare")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "ASSESSMENT_STALE"
    assess(own, shared["pid"])
    r = own.post(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/reshare")
    assert r.status_code == 200 and r.json()["version"] == 2
    case = lender.get(f"/api/v1/lender/cases/{shared['cid']}").json()
    assert case["consent"]["version"] == 2 and case["consent"]["snapshot_sha256"] == r.json()["snapshot_sha256"]
    assert set(case["snapshot"]["sections"]) == {"profile_summary", "financing_request", "obligations"}


def test_at25_info_request_visible_note_private(shared) -> None:
    lender, own = shared["lender"], shared["owner"]
    base = f"/api/v1/lender/cases/{shared['cid']}/events"
    assert lender.post(base, json={"event_type": "note", "body": "Check quotation date"}).status_code == 201
    r = lender.post(base, json={"event_type": "info_request", "body": "অনুগ্রহ করে সরবরাহকারীর দরপত্র দিন"})
    assert r.status_code == 201 and r.json()["review"]["status"] == "info_requested"
    act = own.get(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/activity").json()
    assert [i["body"] for i in act["info_requests"]] == ["অনুগ্রহ করে সরবরাহকারীর দরপত্র দিন"]
    assert "Check quotation date" not in json.dumps(act, ensure_ascii=False)
    row = own.get(f"/api/v1/profiles/{shared['pid']}/consents").json()["items"][0]
    assert row["open_info_requests"] == 1 and "Check quotation date" not in json.dumps(row)
    s = lender.post(base, json={"event_type": "status_change", "status": "under_review"})
    assert s.status_code == 201 and s.json()["review"]["status"] == "under_review"
    events = lender.get(f"/api/v1/lender/cases/{shared['cid']}").json()["review"]["events"]
    assert [e["event_type"] for e in events] == ["note", "info_request", "status_change"]
    assert events[0]["visible_to_owner"] is False and events[1]["visible_to_owner"] is True


def test_at26_decision_needs_reason_and_shows_banner(shared) -> None:
    lender, own = shared["lender"], shared["owner"]
    base = f"/api/v1/lender/cases/{shared['cid']}/events"
    bad = lender.post(base, json={"event_type": "decision", "decision": "refer", "body": "ok"})
    assert bad.status_code == 422 and bad.json()["error"]["fields"] == {"body": "lender.err.reason"}
    assert lender.post(base, json={"event_type": "decision", "body": "Missing decision value"}).status_code == 422
    r = lender.post(base, json={"event_type": "decision", "decision": "refer",
                                "body": "Needs supplier quotation verification at branch"})
    assert r.status_code == 201 and r.json()["banner_key"] == "lender.decision_banner"
    assert r.json()["review"] == {"status": "decision_recorded", "decision": "refer"}
    case = lender.get(f"/api/v1/lender/cases/{shared['cid']}").json()
    assert case["banner_key"] == "lender.decision_banner" and case["review"]["decision_reason"].startswith("Needs")
    assert lender.post(base, json={"event_type": "status_change", "status": "under_review"}).status_code == 409
    again = lender.post(base, json={"event_type": "decision", "decision": "proceed", "body": "Quotation verified"})
    assert again.json()["review"]["decision"] == "proceed"  # latest wins, all logged
    act = own.get(f"/api/v1/profiles/{shared['pid']}/consents/{shared['cid']}/activity").json()
    assert act["decision"]["decision"] == "proceed" and act["decision"]["organization"] == "DEMO Bank Ltd (fictional)"
    assert audit_count(shared["db"], "lender.decision") == 2


def test_owner_cannot_use_lender_api_and_lender_cannot_use_owner_api(shared) -> None:
    assert shared["owner"].post("/api/v1/lender/access-requests",
                                json={"share_code": D1_CODE, "requested_sections": ["profile_summary"]}).status_code == 403
    assert shared["lender"].get(f"/api/v1/profiles/{shared['pid']}/consents").status_code == 403
