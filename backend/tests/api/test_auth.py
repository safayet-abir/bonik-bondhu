"""AT-01..AT-07, FR-AUTH-08/09 (Testing §3)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine, text

from app.core import clock

from ..helpers import PASSWORD, login, owner, register


def test_at01_register_valid(client) -> None:
    u = register(client, full_name="মোঃ রহিম উদ্দিন")
    assert u["role"] == "owner"
    assert u["phone"] == "+8801712340001"
    assert u["preferred_language"] == "bn"
    assert u["full_name"] == "মোঃ রহিম উদ্দিন"  # Bangla stored UTF-8 end to end
    # no auto-login (API spec §4.2)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_at02_duplicate_phone_and_email(client) -> None:
    register(client, 1)
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Other", "phone": "+8801712340001", "email": "x@example.com", "password": PASSWORD})
    assert r.status_code == 409 and r.json()["error"]["code"] == "PHONE_TAKEN"
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Other", "phone": "01812345678", "email": "OWNER1@Example.com", "password": PASSWORD})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_validation_keys(client) -> None:
    r = client.post("/api/v1/auth/register", json={
        "full_name": "R", "phone": "01212345678", "email": "not-an-email", "password": "12345678"})
    assert r.status_code == 422
    fields = r.json()["error"]["fields"]
    assert fields == {
        "full_name": "auth.err.full_name",
        "phone": "auth.err.phone_invalid",
        "email": "auth.err.email_invalid",
        "password": "auth.err.password_digits",
    }
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Rahim", "phone": "01712345678", "email": "r@example.com", "password": "01712345678x"[:11]})
    assert r.json()["error"]["fields"]["password"] == "auth.err.password_digits"


def test_at03_login_correct_wrong_unknown(client) -> None:
    u = register(client)
    r = client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["id"] == u["id"]
    cookie = r.headers["set-cookie"]
    assert "bb_session=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert "Secure" not in cookie  # only in production

    wrong = client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": "wrong-pass-1"})
    unknown = client.post("/api/v1/auth/login", json={"phone": "01799999999", "password": "wrong-pass-1"})
    assert wrong.status_code == unknown.status_code == 401
    strip = lambda b: {k: v for k, v in b["error"].items() if k != "request_id"}  # noqa: E731
    assert strip(wrong.json()) == strip(unknown.json())
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_accepts_bangla_digits_phone(client) -> None:
    register(client)
    r = client.post("/api/v1/auth/login", json={"phone": "০১৭১২৩৪০০০১", "password": PASSWORD})
    assert r.status_code == 200


def test_at04_lockout_after_five_failures(client) -> None:  # also SEC-14
    register(client)
    for _ in range(5):
        r = client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": "wrong-pass-1"})
        assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": PASSWORD})
    assert r.status_code == 429
    err = r.json()["error"]
    assert err["code"] == "ACCOUNT_LOCKED" and 0 < err["retry_after_seconds"] <= 900
    # lock lifts after 15 minutes
    clock.set_now(clock.utcnow() + timedelta(minutes=16))
    assert client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": PASSWORD}).status_code == 200


def test_failed_logins_are_audited(client, clean_db: str) -> None:
    register(client)
    client.post("/api/v1/auth/login", json={"phone": "01712340001", "password": "wrong-pass-1"})
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        actions = conn.execute(text("SELECT action FROM audit_logs ORDER BY id")).scalars().all()
        raw = conn.execute(text("SELECT metadata::text || coalesce(ip_sha256,'') FROM audit_logs")).scalars().all()
    engine.dispose()
    assert actions == ["auth.register", "auth.login_failed"]
    assert not any(PASSWORD in r or "testclient" in r for r in raw)  # no passwords or raw IPs


def test_at05_logout_then_me(client) -> None:
    owner(client)
    assert client.get("/api/v1/auth/me").status_code == 200
    token = client.cookies.get("bb_session")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("bb_session", token)  # replay the old token
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESSION_EXPIRED"


def test_at06_session_expires(client) -> None:
    owner(client)
    clock.set_now(clock.utcnow() + timedelta(days=7, minutes=1))  # owner sessions: 7 days (SUG-03)
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESSION_EXPIRED"


def test_at07_password_hash_never_returned(client, clean_db: str) -> None:
    u = owner(client)
    bodies = [client.get("/api/v1/auth/me").text,
              client.patch("/api/v1/auth/me", json={"full_name": "Renamed"}).text,
              client.post("/api/v1/auth/login", json={"phone": u["phone"], "password": PASSWORD}).text]
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar_one()
    engine.dispose()
    assert stored.startswith("$argon2id$") and PASSWORD not in stored
    for b in bodies:
        assert "password" not in b and stored not in b


def test_fr_auth_08_language_persists(client) -> None:
    u = owner(client)
    assert client.patch("/api/v1/auth/me", json={"preferred_language": "en"}).json()["preferred_language"] == "en"
    client.post("/api/v1/auth/logout")
    assert login(client, u["phone"])["preferred_language"] == "en"
    assert client.patch("/api/v1/auth/me", json={"preferred_language": "fr"}).status_code == 422


def test_fr_auth_09_no_password_reset_endpoint(client) -> None:
    paths = client.get("/api/v1/openapi.json").json()["paths"]
    assert not [p for p in paths if "reset" in p or "forgot" in p]
