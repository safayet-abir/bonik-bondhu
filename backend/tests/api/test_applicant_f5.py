import json
import secrets
import uuid
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from pathlib import Path
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.ai.tools import Toolbox
from app.core.clock import today
from app.models import BusinessProfile
from tests.helpers import create_profile, owner
from tests.api.test_consent_p5 import shared, seeded  # existing isolated test fixtures


@pytest.fixture
def identity():
    return {"full_legal_name": "Applicant (DEMO)", "date_of_birth": "1990-01-01",
            "nid_number": "199" + "".join(secrets.choice("0123456789") for _ in range(10)),
            "address": "Fictional test address", "nominee_name": "Nominee (DEMO)",
            "nominee_relation": "Sibling", "years_in_business": 0}


@pytest.fixture
def profile(client):
    owner(client, 901)
    return create_profile(client)


def endpoint(pid):
    return f"/api/v1/profiles/{pid}/applicant-details"


def test_private_partial_upsert_and_masking(client, profile, identity, caplog):
    url = endpoint(profile["id"])
    initial = client.get(url)
    assert initial.status_code == 200
    assert initial.json()["completeness"]["completed"] == 0
    result = client.put(url, json=identity)
    assert result.status_code == 200
    out = result.json()
    assert out["completeness"] == {"completed": 7, "total": 7, "percent": 100, "missing": []}
    assert out["nid_masked"].endswith(identity["nid_number"][-4:])
    assert out["has_date_of_birth"] is True
    assert "nid_number" not in out and "date_of_birth" not in out
    assert identity["nid_number"] not in result.text and identity["date_of_birth"] not in result.text
    # A name-only edit retains private values instead of overwriting them with masks.
    assert client.put(url, json={"full_legal_name": "Updated (DEMO)"}).status_code == 200
    assert client.get(url).json()["completeness"]["percent"] == 100
    assert identity["nid_number"] not in caplog.text and identity["date_of_birth"] not in caplog.text
    assert identity["nid_number"] not in client.get("/api/v1/profiles").text
    assert identity["nid_number"] not in client.get(f"/api/v1/profiles/{profile['id']}/consents").text


@pytest.mark.parametrize("field,value", [
    ("nid_number", "not-a-number"), ("nid_number", "1" * 12), ("nid_number", "1" * 18),
    ("date_of_birth", "1899-01-01"), ("date_of_birth", "3000-01-01"),
    ("full_legal_name", "x"), ("full_legal_name", "x" * 121),
    ("address", "x" * 301), ("nominee_name", "x"), ("nominee_relation", "x" * 81),
    ("trade_licence", "x" * 101), ("years_in_business", -1), ("years_in_business", 81),
    ("years_in_business", True), ("years_in_business", 1.5), ("unexpected", "ignored?")])
def test_validation(client, profile, field, value):
    result = client.put(endpoint(profile["id"]), json={field: value})
    assert result.status_code == 422
    assert field in result.json()["error"]["fields"]


def test_bangla_nid_clear_and_other_owner(client, profile, identity, make_client):
    url = endpoint(profile["id"])
    bn = identity["nid_number"].translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    assert client.put(url, json={"nid_number": bn}).status_code == 200
    assert client.get(url).json()["nid_masked"].endswith(identity["nid_number"][-4:])
    other = make_client()
    owner(other, 902)
    assert other.get(url).status_code == 404
    assert other.put(url, json=identity).status_code == 404
    assert client.put(url, json={"nid_number": None}).status_code == 200
    assert client.get(url).json()["nid_masked"] is None


def test_unauthenticated_and_csrf(client, profile):
    assert client.put(endpoint(profile["id"]), json={}, headers={"X-BB-Client": ""}).status_code == 403


def test_identity_does_not_stale_assessment_or_leave_through_ai(shared, identity):
    own, pid = shared["owner"], shared["pid"]
    assert own.put(endpoint(pid), json=identity).status_code == 200
    assert own.post(f"/api/v1/profiles/{pid}/consents/{shared['cid']}/reshare").status_code == 200
    engine = create_engine(shared["db"])
    with Session(engine) as db:
        p = db.get(BusinessProfile, uuid.UUID(pid))
        tools = Toolbox(db, p, "en")
        blob = json.dumps([tools.data(name) for name in tools.names()], default=str)
        assert identity["nid_number"] not in blob and identity["date_of_birth"] not in blob
        assert db.execute(text("SELECT count(*) FROM ai_interactions")).scalar() == 0
        audit_blob = str(db.execute(text("SELECT metadata FROM audit_logs WHERE action='applicant.update'")).all())
        assert identity["nid_number"] not in audit_blob
    engine.dispose()


def test_explicit_consent_snapshot_and_revocation(shared, identity):
    own, lender, pid, cid = shared["owner"], shared["lender"], shared["pid"], shared["cid"]
    assert own.put(endpoint(pid), json=identity).status_code == 200
    assert "applicant_details" not in lender.get(f"/api/v1/lender/cases/{cid}").json()["snapshot"]["sections"]
    assert lender.get(endpoint(pid)).status_code == 403
    # A separately requested, explicitly approved section is required.
    assert lender.post("/api/v1/lender/access-requests", json={"share_code": "7KQ2M-9XA4P",
        "requested_sections": ["profile_summary", "financing_request", "applicant_details"]}).status_code == 202
    row = next(x for x in own.get(f"/api/v1/profiles/{pid}/consents").json()["items"] if x["status"] == "requested")
    new_cid = row["id"]
    approval = own.post(f"/api/v1/profiles/{pid}/consents/{new_cid}/approve", json={
        "approved_sections": ["profile_summary", "financing_request", "applicant_details"],
        "financing_request_id": shared["rid"], "valid_days": 7})
    assert approval.status_code == 200
    assert identity["nid_number"] not in approval.text
    case = lender.get(f"/api/v1/lender/cases/{new_cid}").json()
    section = case["snapshot"]["sections"]["applicant_details"]
    assert section["nid_number"] == identity["nid_number"] and section["date_of_birth"] == identity["date_of_birth"]
    assert section["label_key"] == "applicant.declared" and case["consent"]["hash_verified"]
    assert identity["nid_number"] not in lender.get("/api/v1/lender/cases").text
    assert own.put(endpoint(pid), json={"full_legal_name": "Later name (DEMO)"}).status_code == 200
    assert lender.get(f"/api/v1/lender/cases/{new_cid}").json()["snapshot"] == case["snapshot"]
    assert own.post(f"/api/v1/profiles/{pid}/consents/{new_cid}/revoke").status_code == 200
    assert lender.get(f"/api/v1/lender/cases/{new_cid}").status_code == 403


def test_populated_downgrade_refused(client, profile, clean_db, identity):
    assert client.put(endpoint(profile["id"]), json=identity).status_code == 200
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.attributes["database_url"] = clean_db
    with pytest.raises(RuntimeError, match="destructive downgrade refused"):
        command.downgrade(cfg, "0001_initial")
    assert client.get(endpoint(profile["id"])).json()["completeness"]["percent"] == 100


def test_incomplete_identity_cannot_be_shared_and_request_stays_pending(shared):
    own, lender, pid = shared["owner"], shared["lender"], shared["pid"]
    lender.post("/api/v1/lender/access-requests", json={"share_code": "7KQ2M-9XA4P",
        "requested_sections": ["profile_summary", "financing_request", "applicant_details"]})
    path = f"/api/v1/profiles/{pid}/consents"
    row = next(x for x in own.get(path).json()["items"] if x["status"] == "requested")
    response = own.post(f"{path}/{row['id']}/approve", json={"financing_request_id": shared["rid"],
        "approved_sections": ["profile_summary", "financing_request", "applicant_details"], "valid_days": 7})
    assert response.status_code == 422
    assert "approved_sections" in response.json()["error"]["fields"]
    assert next(x for x in own.get(path).json()["items"] if x["id"] == row["id"])["status"] == "requested"
    assert lender.get(f"/api/v1/lender/cases/{row['id']}").status_code == 403


def test_farm_and_shop_identity_are_separate(client, profile, identity):
    farm = create_profile(client, activity_type="crop_farm", display_name="F5 Farm (DEMO)")
    assert client.put(endpoint(farm["id"]), json=identity).status_code == 200
    assert client.get(endpoint(farm["id"])).json()["completeness"]["percent"] == 100
    assert client.get(endpoint(profile["id"])).json()["completeness"]["percent"] == 0
