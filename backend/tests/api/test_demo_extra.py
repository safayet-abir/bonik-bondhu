"""Extra DEMO personas (SUG-61): the CLI seeds them after D1-D4. They must produce the intended check results
through the real services, show the right cases to each fictional lender, never leak supplier names into a
snapshot, leave the golden D1 result alone, and disappear on reset."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import demo, demo_extra
from tests.helpers import login

DEMO_PW = "test-only-demo-2026"  # isolated test DB only
BANK, SAMITY = "01900000112", "01900000111"


@pytest.fixture()
def seeded(clean_db: str) -> tuple[str, dict]:
    engine = create_engine(clean_db)
    with Session(engine) as db, db.begin():
        demo.seed(db.connection(), DEMO_PW)
        status = demo_extra.seed_extra(db, DEMO_PW)
    engine.dispose()
    return clean_db, status


def test_personas_reach_the_intended_results(seeded) -> None:
    _, status = seeded
    assert status["Nasima Bostro Bitan"] == "ready_for_lender_review"
    assert status["Jamal Fol Bhandar"] == "not_affordable_base_case"
    assert status["Rokeya Sobji Khet"] == "ready_for_lender_review"
    assert status["Monir Dhan Khet"] == "ready_for_lender_review"
    assert set(status) == {"Hasan General Store", "Nasima Bostro Bitan", "Jamal Fol Bhandar", "Rokeya Sobji Khet",
                           "Abdul Dhan Khet", "Monir Dhan Khet"}


def test_each_lender_sees_only_its_own_cases(seeded, make_client) -> None:
    bank = make_client()
    login(bank, BANK, DEMO_PW)
    cases = bank.get("/api/v1/lender/cases").json()["items"]
    by_status = {c["status"]: c for c in cases}
    assert len(cases) == 2 and set(by_status) == {"approved", "requested"}
    assert by_status["approved"]["applicant"]["display_name"] == "Nasima Bostro Bitan"
    assert by_status["approved"]["review_status"] == "info_requested"
    assert by_status["requested"]["applicant"] is None  # pending: applicant hidden until the owner approves

    case = bank.get(f"/api/v1/lender/cases/{by_status['approved']['consent_id']}")
    assert case.status_code == 200, case.text
    body = json.dumps(case.json(), ensure_ascii=False)
    for name in ("Islampur cloth wholesaler", "Madhabdi weaver"):
        assert name not in body  # suppliers reach a lender only as Supplier 1/2 (SEC-12)

    samity = make_client()
    login(samity, SAMITY, DEMO_PW)
    s_cases = samity.get("/api/v1/lender/cases").json()["items"]
    assert [c["applicant"]["display_name"] for c in s_cases] == ["Rokeya Sobji Khet"]
    assert s_cases[0]["applicant"]["activity_type"] == "crop_farm"


def test_golden_d1_unchanged_and_owners_can_log_in(seeded, make_client) -> None:
    c = make_client()
    login(c, "01900000001", DEMO_PW)
    store = next(p for p in c.get("/api/v1/profiles").json()["items"] if p["display_name"] == "Rahim Store")
    rid = c.get(f"/api/v1/profiles/{store['id']}/financing-requests").json()["items"][0]["id"]
    a = c.post(f"/api/v1/profiles/{store['id']}/financing-requests/{rid}/assessments")
    assert a.status_code == 201 and a.json()["status"] == "ready_for_lender_review"

    for phone in ("01900000201", "01900000205"):
        o = make_client()
        login(o, phone, DEMO_PW)
        assert len(o.get("/api/v1/profiles").json()["items"]) == 1


def test_reset_removes_every_extra_persona(seeded) -> None:
    url, _ = seeded
    engine = create_engine(url)
    with engine.begin() as conn:
        demo.reset(conn)
        left = conn.execute(text("SELECT count(*) FROM users WHERE phone_e164 = ANY(:p)"),
                            {"p": list(demo_extra.EXTRA_PHONES)}).scalar()
        orgs = conn.execute(text("SELECT count(*) FROM lender_organizations WHERE is_demo")).scalar()
    engine.dispose()
    assert left == 0 and orgs == 0
