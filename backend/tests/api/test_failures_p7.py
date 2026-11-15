"""P7 failure scenarios (Testing §9) not covered elsewhere: FS-01 database down, FS-03 upload
storage not writable. (FS-02 = AI-03, FS-04 = import-news test, FS-06 = engine/API debt tests.)"""
from __future__ import annotations

from sqlalchemy import create_engine

from app.api import health
from app.config import get_settings
from tests.helpers import create_profile, owner


def test_fs01_database_down_health_503(client, monkeypatch) -> None:
    dead = create_engine("postgresql+psycopg://x:x@127.0.0.1:1/x", connect_args={"connect_timeout": 2})
    monkeypatch.setattr(health, "get_engine", lambda: dead)
    r = client.get("/api/v1/health")
    assert r.status_code == 503 and r.json() == {"status": "degraded", "db": "down", "llm": "disabled"}


def test_fs03_upload_storage_unwritable_503_manual_still_works(client, tmp_path, monkeypatch) -> None:
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("x")  # UPLOAD_DIR points at a file: the folder cannot be created or written
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(blocked))
    owner(client)
    pid = create_profile(client)["id"]
    png = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c4944415408d763f8ffff3f0005fe02fea7d6a9b60000000049454e44ae426082")
    r = client.post(f"/api/v1/profiles/{pid}/documents", files={"file": ("r.png", png, "image/png")})
    assert r.status_code == 503 and r.json()["error"]["message_key"] == "doc.err.storage"
    t = client.post(f"/api/v1/profiles/{pid}/transactions",
                    json={"txn_type": "operating_expense", "amount": "500", "value_date": "2026-11-10"})
    assert t.status_code == 201
