"""Plan Ultra F2 — World Bank economy context (SUG-58). Offline: the committed snapshot is the source and
the collector is tested against a fake API."""
from __future__ import annotations

from decimal import Decimal

import httpx

from app.services import economy_service
from tests.api.test_assessment_p3 import assert_no_forbidden, demo_profile, request_id, seeded  # noqa: F401
from tests.helpers import owner


def _wb(request: httpx.Request) -> httpx.Response:
    code = request.url.path.rsplit("/", 1)[-1]
    if code == "FS.AST.PRVT.GD.ZS":
        return httpx.Response(503)  # one indicator down
    return httpx.Response(200, json=[{"page": 1}, [{"indicator": {"id": code, "value": f"Label {code}"},
                                                     "date": "2025", "value": 7.25}]])


def test_collect_keeps_the_last_value_when_an_indicator_fails() -> None:
    old = {i["code"]: i for i in economy_service.context()["indicators"]}
    with httpx.Client(transport=httpx.MockTransport(_wb)) as client:
        data = economy_service.collect(client)
    got = {i["code"]: i for i in data["indicators"]}
    assert set(got) == set(economy_service.INDICATORS)
    assert got["FP.CPI.TOTL.ZG"] == {"code": "FP.CPI.TOTL.ZG", "key": "inflation", "label": "Label FP.CPI.TOTL.ZG",
                                     "year": 2025, "value": "7.2"}  # one decimal, ROUND_HALF_EVEN from Decimal
    assert got["FS.AST.PRVT.GD.ZS"] == old["FS.AST.PRVT.GD.ZS"]  # failed -> previous value kept
    assert data["source"]["name"] == "World Bank Open Data"


def test_snapshot_is_complete_and_dated() -> None:
    ctx = economy_service.context()
    assert ctx["country"] == "Bangladesh" and len(ctx["indicators"]) == 4
    for i in ctx["indicators"]:
        assert i["year"] >= 2020 and Decimal(i["value"]) == Decimal(i["value"]).quantize(Decimal("0.1"))


def _whatif(c, pid: str) -> dict:
    r = c.get(f"/api/v1/profiles/{pid}/financing-requests/{request_id(c, pid)}/economy-whatif")
    assert r.status_code == 200, r.text
    assert_no_forbidden(r.json())
    return r.json()


def test_shop_inflation_whatif_never_changes_the_status(seeded, client) -> None:  # noqa: F811
    pid = demo_profile(client, "01900000001", "Rahim Store")["id"]
    assert client.get(f"/api/v1/profiles/{pid}/economy-context").json() == economy_service.context()
    infl = Decimal(economy_service.indicator("inflation")["value"])
    w = _whatif(client, pid)["whatif"]
    assert w["days"] == 90 and w["inflation_pct"] == str(infl)
    assert w["price_rise_pct"] == f"{(infl / 100 * 90 / 365).quantize(Decimal('0.0001')) * 100:.1f}"
    assert w["result"]["kind"] == "shop_due_dates" and isinstance(w["result"]["covered"], bool)
    assert w["base_status"] == "ready_for_lender_review"
    a = client.post(f"/api/v1/profiles/{pid}/financing-requests/{request_id(client, pid)}/assessments").json()
    assert a["status"] == "ready_for_lender_review"  # DEC-30: the what-if changed nothing


def test_farm_whatif_and_incomplete_case(seeded, client) -> None:  # noqa: F811
    farm = demo_profile(client, "01900000001", "Rahim Rice Farm")["id"]
    w = _whatif(client, farm)["whatif"]
    assert w["result"]["kind"] == "crop_harvest" and 0 < w["days"] <= 365
    selina = demo_profile(client, "01900000004", "Selina Tailoring")["id"]
    assert _whatif(client, selina)["whatif"] is None  # missing basics -> no what-if, not a guess


def test_other_owner_gets_404(seeded, client, make_client) -> None:  # noqa: F811
    pid = demo_profile(client, "01900000001", "Rahim Store")["id"]
    other = make_client()
    owner(other)
    assert other.get(f"/api/v1/profiles/{pid}/economy-context").status_code == 404


def test_advisor_tool_and_quick_answer(seeded, client) -> None:  # noqa: F811
    from app.ai.tools import Toolbox
    from app.db import get_sessionmaker
    from app.models import BusinessProfile
    pid = demo_profile(client, "01900000001", "Rahim Store")["id"]
    with get_sessionmaker()() as db:
        tb = Toolbox(db, db.get(BusinessProfile, pid), "en")
        d = tb.data("get_economy_context")
    assert d["source"] == "World Bank Open Data" and len(d["figures"]) == 4 and "inflation_whatif" in d
    assert "not live" in d["label"]
    help_ = client.get(f"/api/v1/profiles/{pid}/advisor/help-topics?lang=bn").json()
    eco = next(q for q in help_["quick"] if q["key"] == "economy")
    assert "বিশ্বব্যাংক" in eco["answer"] and "আপনার ব্যবসার নয়" in eco["answer"]
