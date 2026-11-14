"""Negative security tests required by the P1 gate: SEC-01, 02, 03, 06, 07,
15, 16 (Security doc §7). SEC-14 lockout lives in tests/api/test_auth.py."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core import clock

from ..helpers import PASSWORD, create_lender, create_profile, login, owner, register


def test_sec01_no_cookie(client) -> None:
    r = client.get("/api/v1/profiles")
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED"


def test_sec02_logged_out_token(client) -> None:
    owner(client)
    token = client.cookies.get("bb_session")
    client.post("/api/v1/auth/logout")
    client.cookies.set("bb_session", token)
    r = client.get("/api/v1/profiles")
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESSION_EXPIRED"


def test_sec03_other_owners_profile_is_404(make_client) -> None:
    a, b = make_client(), make_client()
    owner(a, 1)
    owner(b, 2)
    pid_b = create_profile(b, "B Store")["id"]
    for method, path, body in [
        ("GET", f"/api/v1/profiles/{pid_b}", None),
        ("PATCH", f"/api/v1/profiles/{pid_b}", {"district": "Dhaka"}),
        ("POST", f"/api/v1/profiles/{pid_b}/share-code/regenerate", None),
        ("GET", f"/api/v1/profiles/{pid_b}/summary", None),
        ("GET", f"/api/v1/profiles/{pid_b}/transactions", None),
        ("POST", f"/api/v1/profiles/{pid_b}/transactions",
         {"txn_type": "sale_cash", "amount": "1", "value_date": clock.today().isoformat()}),
    ]:
        r = a.request(method, path, json=body)
        assert r.status_code == 404, (method, path)
        assert r.json()["error"]["code"] == "NOT_FOUND"
    # identical to a profile that does not exist at all
    assert a.get(f"/api/v1/profiles/{uuid.uuid4()}").status_code == 404
    # and B's data is untouched
    assert b.get(f"/api/v1/profiles/{pid_b}").json()["district"] is None
    assert b.get(f"/api/v1/profiles/{pid_b}/transactions").json()["total"] == 0


def test_child_lookup_scoped_to_profile(make_client) -> None:
    """A transaction id from profile A requested under A's other profile -> 404."""
    a = make_client()
    owner(a)
    p1, p2 = create_profile(a, "Shop One")["id"], create_profile(a, "Shop Two")["id"]
    tid = a.post(f"/api/v1/profiles/{p1}/transactions", json={
        "txn_type": "sale_cash", "amount": "5", "value_date": clock.today().isoformat()}).json()["id"]
    assert a.get(f"/api/v1/profiles/{p1}/transactions/{tid}").status_code == 200
    assert a.get(f"/api/v1/profiles/{p2}/transactions/{tid}").status_code == 404


def test_sec06_owner_cannot_use_lender_routes(client) -> None:
    owner(client)
    r = client.get("/api/v1/lender/cases")
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_sec07_lender_cannot_use_owner_routes(client: TestClient) -> None:
    phone = create_lender()
    login(client, phone)
    me = client.get("/api/v1/auth/me").json()
    assert me["role"] == "lender_officer"
    assert me["lender"]["organization"]["name"] == "DEMO Bank Ltd (fictional)"
    for path in ("/api/v1/profiles", f"/api/v1/profiles/{uuid.uuid4()}"):
        r = client.get(path)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE"
    assert client.post("/api/v1/profiles", json={"display_name": "X Shop", "activity_type": "shop"}).status_code == 403
    # lender lands on a working (empty) case list
    assert client.get("/api/v1/lender/cases").json() == {"items": [], "total": 0}


def test_sec15_register_cannot_choose_role(client) -> None:
    u = register(client, role="lender_officer", is_demo=True, preferred_language="en")
    assert u["role"] == "owner" and u["is_demo"] is False


def test_sec16_post_without_csrf_header(client) -> None:
    r = client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": PASSWORD},
                    headers={"X-BB-Client": ""})
    assert r.status_code == 403 and r.json()["error"]["code"] == "CSRF_HEADER_MISSING"


def test_sql_metacharacters_stored_as_text(client) -> None:  # SEC-18 (preview; full in P2)
    owner(client)
    pid = create_profile(client, "Robert'); DROP TABLE users;--")["id"]
    assert client.get(f"/api/v1/profiles/{pid}").json()["display_name"] == "Robert'); DROP TABLE users;--"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_auth_rate_limit_per_ip(client) -> None:  # SUG-05: 30 auth requests / 10 min / IP
    for _ in range(30):
        client.post("/api/v1/auth/login", json={"phone": "01799999999", "password": "x-wrong-123"})
    r = client.post("/api/v1/auth/login", json={"phone": "01799999999", "password": "x-wrong-123"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"
