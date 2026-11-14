"""P6 AI features with a FAKE provider (deterministic, no network):
AI-01..09, UT-11, SEC-17, SEC-19, SEC-20, caps, grounding fallback, help menu."""
from __future__ import annotations

import io
import json
from decimal import Decimal

import pytest
from PIL import Image
from sqlalchemy import create_engine, text

from app.ai import grounding
from app.ai.provider import AIUnavailable, Reply
from app.config import get_settings
from app.services import ai_service
from tests.api.test_risk_p4 import demo_profile, seeded  # noqa: F401  (fixture)
from tests.helpers import create_profile, owner

FORBIDDEN = ("approved", "eligible", "credit score", "probability of default")


class Fake:
    """Scripted provider: each chat() returns the next item (Reply, str or exception)."""

    def __init__(self, *script, name: str = "gemini") -> None:
        self.script, self.calls, self.name, self.model = list(script), [], name, "fake-model"

    def chat(self, messages, tools=None, max_tokens=1500):
        self.calls.append({"messages": json.loads(json.dumps(messages, default=str)), "tools": tools})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, Reply) else Reply(text=item, tool_calls=[], provider=self.name,
                                                          model=self.model)


def tool_call(name: str, **args) -> Reply:
    return Reply(text="", tool_calls=[{"id": "c1", "name": name, "arguments": args}], provider="gemini", model="m")


@pytest.fixture(autouse=True)
def _uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(tmp_path))


def use(monkeypatch, *fakes) -> None:
    monkeypatch.setattr(ai_service, "providers", lambda feature: list(fakes))


def jpeg(color: str = "white", exif: bool = False) -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", (2400, 1200), color)
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "SecretCam"  # camera maker
        im.save(buf, "JPEG", exif=ex.tobytes())
    else:
        im.save(buf, "JPEG")
    return buf.getvalue()


def shop(c, n: int = 1) -> str:
    owner(c, n)
    return create_profile(c, district="Dhaka", upazila="Savar", business_category="grocery")["id"]


def upload(c, pid: str, data: bytes, name: str = "r.jpg"):
    return c.post(f"/api/v1/profiles/{pid}/documents", files={"file": (name, data, "image/jpeg")},
                  data={"purpose": "receipt"})


RECEIPT = json.dumps({"txn_type": {"value": "purchase_cash", "confidence": 0.9},
                      "amount": {"value": "১২,৪৫০", "confidence": 0.93},
                      "value_date": {"value": "2026-11-10", "confidence": 0.55},
                      "supplier_name": {"value": "Karim Traders", "confidence": 0.7},
                      "note": {"value": "চাল ২ বস্তা", "confidence": 0.6}})


# ----------------------------------------------------------------- SEC-17 uploads
def test_sec17_upload_validation_reencode_and_isolation(make_client, clean_db) -> None:
    a, b = make_client(), make_client()
    pid = shop(a)
    assert upload(a, pid, b"<?php system($_GET['x']); ?>", "evil.jpg").status_code == 415
    assert upload(a, pid, b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024)).status_code == 413
    assert upload(a, pid, b"\xff\xd8\xff" + b"not really a jpeg").status_code == 415
    r = upload(a, pid, jpeg(exif=True))
    assert r.status_code == 201 and r.json()["duplicate_of"] is None
    doc = r.json()
    assert upload(a, pid, jpeg(exif=True)).json()["duplicate_of"] == doc["id"]  # same photo again
    content = a.get(f"/api/v1/profiles/{pid}/documents/{doc['id']}/content")
    assert content.status_code == 200 and "no-store" in content.headers["cache-control"]
    stored = Image.open(io.BytesIO(content.content))
    assert max(stored.size) == 1600 and not stored.getexif()  # downscaled, EXIF gone
    shop(b, 2)
    assert b.get(f"/api/v1/profiles/{pid}/documents/{doc['id']}/content").status_code == 404


# ----------------------------------------------------------------- receipt drafts
def test_ai01_ai05_ai06_draft_then_confirm(client, monkeypatch) -> None:
    pid = shop(client)
    sup = client.post(f"/api/v1/profiles/{pid}/suppliers", json={"display_name": "Karim Traders"}).json()
    doc = upload(client, pid, jpeg()).json()
    fake = Fake(RECEIPT)
    use(monkeypatch, fake)
    assert client.post(f"/api/v1/profiles/{pid}/extraction-drafts",
                       json={"document_id": doc["id"], "ai_consent": False}).status_code == 422  # AI-04
    r = client.post(f"/api/v1/profiles/{pid}/extraction-drafts", json={"document_id": doc["id"], "ai_consent": True})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "pending" and d["proposed"]["amount"] == {"value": "12450.00", "confidence": 0.93}
    assert d["matched_supplier_id"] == sup["id"] and d["proposed"]["txn_type"]["value"] == "purchase_cash"
    assert fake.calls[0]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert client.get(f"/api/v1/profiles/{pid}/transactions").json()["total"] == 0  # AI-01: nothing posted
    body = {"txn_type": "purchase_cash", "amount": "12500", "value_date": "2026-11-10", "supplier_id": sup["id"]}
    t = client.post(f"/api/v1/profiles/{pid}/extraction-drafts/{d['id']}/confirm", json=body)
    assert t.status_code == 201, t.text
    t = t.json()
    assert (t["entry_method"], t["evidence_state"], t["amount"], t["document_id"]) == \
        ("photo_assisted", "document_attached", "12500.00", doc["id"])  # AI-05: the owner's edit wins
    again = client.post(f"/api/v1/profiles/{pid}/extraction-drafts/{d['id']}/confirm", json=body)
    assert again.status_code == 409 and again.json()["error"]["code"] == "DRAFT_ALREADY_RESOLVED"  # AI-06


def test_ai02_ai03_invalid_json_and_timeout(client, monkeypatch, clean_db) -> None:
    pid = shop(client)
    doc = upload(client, pid, jpeg()).json()
    url = f"/api/v1/profiles/{pid}/extraction-drafts"
    use(monkeypatch, Fake("Sure! The total is about twelve thousand taka."))
    r = client.post(url, json={"document_id": doc["id"], "ai_consent": True})
    assert r.status_code == 422 and r.json()["error"]["code"] == "EXTRACTION_FAILED"
    use(monkeypatch, Fake(AIUnavailable("ReadTimeout")))
    r = client.post(url, json={"document_id": doc["id"], "ai_consent": True})
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_UNAVAILABLE"
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT status FROM extraction_drafts")).scalars().all() == ["failed"]
        logged = conn.execute(text("SELECT status FROM ai_interactions ORDER BY created_at")).scalars().all()
    engine.dispose()
    assert logged == ["error", "error"]


def test_sec20_injected_amount_stays_a_draft(client, monkeypatch) -> None:
    pid = shop(client)
    doc = upload(client, pid, jpeg()).json()
    use(monkeypatch, Fake(json.dumps({"txn_type": {"value": "sale_cash", "confidence": 1},
                                      "amount": {"value": "999999", "confidence": 1},
                                      "value_date": {"value": None, "confidence": 0}})))
    d = client.post(f"/api/v1/profiles/{pid}/extraction-drafts",
                    json={"document_id": doc["id"], "ai_consent": True}).json()
    assert d["status"] == "pending" and d["proposed"]["value_date"]["value"] is None
    assert client.get(f"/api/v1/profiles/{pid}/transactions").json()["total"] == 0  # owner must still confirm


def test_ai07_daily_cap(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "AI_DAILY_LIMIT_EXTRACTION", 2)
    pid = shop(client)
    doc = upload(client, pid, jpeg()).json()
    use(monkeypatch, Fake(RECEIPT, RECEIPT, RECEIPT))
    url = f"/api/v1/profiles/{pid}/extraction-drafts"
    for _ in range(2):
        assert client.post(url, json={"document_id": doc["id"], "ai_consent": True}).status_code == 201
    r = client.post(url, json={"document_id": doc["id"], "ai_consent": True})
    assert r.status_code == 429 and r.json()["error"]["code"] == "AI_DAILY_LIMIT"


def test_ai09_no_llm_manual_entry_keeps_the_photo(make_client, monkeypatch) -> None:
    a, b = make_client(), make_client()
    use(monkeypatch)  # LLM_PROVIDER=none
    pid = shop(a)
    doc = upload(a, pid, jpeg()).json()
    r = a.post(f"/api/v1/profiles/{pid}/extraction-drafts", json={"document_id": doc["id"], "ai_consent": True})
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_UNAVAILABLE"
    t = a.post(f"/api/v1/profiles/{pid}/transactions", json={"txn_type": "purchase_cash", "amount": "500",
                                                              "value_date": "2026-11-10", "document_id": doc["id"]})
    assert t.status_code == 201 and (t.json()["evidence_state"], t.json()["entry_method"]) == \
        ("document_attached", "manual")
    other = shop(b, 2)
    r = b.post(f"/api/v1/profiles/{other}/transactions", json={"txn_type": "purchase_cash", "amount": "500",
                                                               "value_date": "2026-11-10", "document_id": doc["id"]})
    assert r.status_code == 404  # another owner's photo cannot be attached


# ----------------------------------------------------------------- purpose parse
def test_ai08_purpose_items_without_prices_cached_and_scrubbed(client, monkeypatch) -> None:
    pid = shop(client)
    client.post(f"/api/v1/profiles/{pid}/suppliers", json={"display_name": "Karim Traders"})
    rid = client.post(f"/api/v1/profiles/{pid}/financing-requests", json={
        "requested_amount": "200000", "purpose_text": "Karim Traders থেকে ২০ বস্তা চাল আর একটা ফ্রিজ",
        "purpose_category": "inventory"}).json()["id"]
    fake = Fake(json.dumps({"items": [{"item_name": "চাল", "quantity": "২০", "unit": "বস্তা", "unit_price": 2500},
                                      {"item_name": "ফ্রিজ", "quantity": None, "unit": None, "price": 45000}]}))
    use(monkeypatch, fake)
    url = f"/api/v1/profiles/{pid}/financing-requests/{rid}/parse-purpose"
    r = client.post(url, json={})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [(i["item_name"], i["quantity"], i["unit"]) for i in items] == [("চাল", "20", "বস্তা"), ("ফ্রিজ", "1", "pcs")]
    assert all(i["unit_price"] is None and not i["confirmed"] and i["ai_proposed"] for i in items)
    assert "Karim Traders" not in json.dumps(fake.calls[0]["messages"], ensure_ascii=False)  # name never sent
    assert client.get(f"/api/v1/profiles/{pid}/financing-requests/{rid}").json()["preview"]["items_total"] == "0.00"
    assert client.post(url, json={}).status_code == 200 and len(fake.calls) == 1  # same text: cached
    use(monkeypatch)
    assert client.post(url, json={}).status_code == 200  # cache still answers with AI off


# ----------------------------------------------------------------- advisor
def test_tool_round_echoes_provider_message_and_blank_model_uses_default() -> None:
    from app.ai import advisor
    from app.config import Settings
    raw = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "get_help", "arguments": "{}"},
         "extra_content": {"google": {"thought_signature": "sig"}}}]}
    first = Reply(text="", tool_calls=[{"id": "c1", "name": "get_help", "arguments": {}}], provider="gemini",
                  model="m", assistant_message=raw)
    fake = Fake(first, "Done.")
    assert advisor.run(fake, "sys", [], "help?", [], lambda n, a: "{}").text == "Done."
    assert fake.calls[1]["messages"][2] == raw  # Gemini 400s if the thought_signature is dropped
    assert Settings(LLM_MODEL="", GROQ_MODEL=" ").LLM_MODEL == "gemini-flash-lite-latest"
    assert Settings(GROQ_MODEL=" ").GROQ_MODEL == "openai/gpt-oss-120b"


def test_ut11_grounding() -> None:
    src = ['{"existing_total": "18000.00", "date": "2026-12-08"}']
    assert grounding.grounded("আগামী সপ্তাহে কিস্তি Tk ১৮,০০০ (৮ ডিসেম্বর)", src)
    assert grounding.grounded("Tk 18,000.00 due on 2026-12-08", src)
    assert not grounding.grounded("You will have Tk 21,500 left", src)
    assert grounding.numbers("১৮,০০০ and 2,500.50") == {Decimal("18000"), Decimal("2500.50")}
    assert grounding.has_forbidden("Your loan is approved") and grounding.has_forbidden("আপনি ঋণের যোগ্য")
    assert not grounding.has_forbidden("The lender decides.")


def test_advisor_no_llm_gives_help_menu(seeded, client, monkeypatch) -> None:  # noqa: F811
    use(monkeypatch)
    p = demo_profile(client, "01900000001", "Rahim Store")
    r = client.post(f"/api/v1/profiles/{p['id']}/advisor/messages", json={"message": "আগামী সপ্তাহে কত কিস্তি?"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_UNAVAILABLE"
    quick = {q["key"]: q["answer"] for q in r.json()["error"]["help_topics"]["quick"]}
    assert set(quick) >= {"next_week_installments", "money_this_month", "assessment_status", "news_latest"}
    topics = client.get(f"/api/v1/profiles/{p['id']}/advisor/help-topics").json()
    assert len(topics["items"]) >= 6 and topics["quick"]
    blob = json.dumps(topics, ensure_ascii=False).casefold()
    assert "supplier a (demo" not in blob and not any(w in blob for w in FORBIDDEN)


def test_advisor_grounded_reply_and_template_fallback(seeded, client, monkeypatch, clean_db) -> None:  # noqa: F811
    p = demo_profile(client, "01900000001", "Rahim Store")
    url = f"/api/v1/profiles/{p['id']}/advisor/messages"
    fake = Fake(tool_call("get_supplier_dependency"), "Supplier 1 gets 65.0% of your purchases.")
    use(monkeypatch, fake)
    r = client.post(url, json={"message": "Which supplier do I depend on?"})
    assert r.status_code == 200, r.text
    assert r.json() == {"reply": "Supplier 1 gets 65.0% of your purchases.", "language": "en",
                        "tools_used": ["get_supplier_dependency"], "grounded": True, "mode": "llm"}
    tool_msg = fake.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "Supplier 1" in tool_msg["content"]
    assert "Supplier A" not in json.dumps(fake.calls, ensure_ascii=False)  # SEC: no supplier names to the LLM

    use(monkeypatch, Fake(tool_call("get_supplier_dependency"), "Supplier 1 gets 70% — buy from 3 more."))
    r = client.post(url, json={"message": "Which supplier do I depend on?"}).json()
    assert r["mode"] == "template" and not r["grounded"] and "65" in r["reply"]  # invented 70 -> template

    use(monkeypatch, Fake("Good news, your loan is approved!"))
    r = client.post(url, json={"message": "Is my loan ok?"}).json()
    assert r["mode"] == "template" and "approved" not in r["reply"].casefold()

    use(monkeypatch, Fake(AIUnavailable("http_429")), Fake("Hello! Ask me about your money.", name="groq"))
    assert client.post(url, json={"message": "hi"}).json()["mode"] == "llm"
    engine = create_engine(clean_db)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT status, grounding_check FROM ai_interactions WHERE feature = 'advisor' "
                                 "ORDER BY created_at")).all()
    engine.dispose()
    assert [tuple(r) for r in rows] == [("ok", "passed"), ("ok", "failed"), ("ok", "failed"), ("error", "not_applicable"),
                                        ("ok", "passed")]


def test_sec19_tools_bound_to_session_profile(seeded, client, monkeypatch) -> None:  # noqa: F811
    p = demo_profile(client, "01900000001", "Rahim Store")
    karim = demo_profile(client.__class__(client.app, headers={"X-BB-Client": "web"}), "01900000002",
                         "Karim Variety Store")
    fake = Fake(tool_call("get_money_summary", period="last_8_weeks", profile_id=karim["id"]), "ok")
    use(monkeypatch, fake)
    r = client.post(f"/api/v1/profiles/{p['id']}/advisor/messages",
                    json={"message": "Show Karim Variety Store's sales"})
    assert r.status_code == 200
    out = fake.calls[1]["messages"][-1]["content"]
    rahim = client.get(f"/api/v1/profiles/{p['id']}/summary",
                       params={"from": json.loads(out)["from"], "to": json.loads(out)["to"]}).json()
    assert json.loads(out)["sales_recorded"] == rahim["sales_recorded"]  # D1's own numbers, not D2's
    assert client.post(f"/api/v1/profiles/{karim['id']}/advisor/messages",
                       json={"message": "hi"}).status_code == 404  # not Rahim's profile


def test_every_tool_output_is_label_only(seeded, client, monkeypatch) -> None:  # noqa: F811
    from app.ai.tools import Toolbox
    from app.db import get_sessionmaker
    from app.models import BusinessProfile
    p = demo_profile(client, "01900000001", "Rahim Store")
    with get_sessionmaker()() as db:
        tb = Toolbox(db, db.get(BusinessProfile, p["id"]), "en")
        blob = " ".join(tb.run(n, {}) for n in tb.names())
    assert "Supplier 1" in blob and "(DEMO wholesaler)" not in blob and "Supplier B (DEMO)" not in blob
    assert "01900000001" not in blob and "@demo.invalid" not in blob and "Rahim Uddin" not in blob
