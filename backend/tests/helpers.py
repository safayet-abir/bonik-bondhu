"""Small helpers for API tests (fictional test data only)."""
from __future__ import annotations

import os
from typing import Any

from fastapi.testclient import TestClient

PASSWORD = "bazar-2026!"


def register(c: TestClient, n: int = 1, **overrides: Any) -> dict[str, Any]:
    body = {
        "full_name": f"Test Owner {n}",
        "phone": f"0171234{n:04d}",
        "email": f"owner{n}@example.com",
        "password": PASSWORD,
        **overrides,
    }
    r = c.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def login(c: TestClient, phone: str, password: str = PASSWORD) -> dict[str, Any]:
    r = c.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def owner(c: TestClient, n: int = 1) -> dict[str, Any]:
    """Register + log in an owner on client `c`; returns the user."""
    user = register(c, n)
    login(c, user["phone"])
    return user


def create_profile(c: TestClient, name: str = "Rahim Store", activity_type: str = "shop", **extra: Any) -> dict[str, Any]:
    r = c.post("/api/v1/profiles", json={"display_name": name, "activity_type": activity_type, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def create_lender(n: int = 1, org: str = "DEMO Bank Ltd (fictional)") -> str:
    """Provision a lender officer through the real admin CLI; returns phone."""
    from app.cli import main

    phone = f"0190000{n:04d}"
    os.environ["BB_NEW_PASSWORD"] = PASSWORD
    try:
        assert main(["create-lender", "--org", org, "--name", f"Officer {n}", "--phone", phone,
                     "--email", f"officer{n}@example.com", "--designation", "SME Officer"]) == 0
    finally:
        del os.environ["BB_NEW_PASSWORD"]
    return phone
