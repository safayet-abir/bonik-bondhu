"""Plan Ultra F1 — Repayment Fit Finder (SUG-56). The property that matters: every schedule the finder
returns is accepted by the UNCHANGED assessment when the owner copies it into the proposal."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.engine import schedule_search as ss
from tests.api.test_assessment_p3 import assert_no_forbidden, demo_profile, request_id, seeded  # noqa: F401
from tests.helpers import owner

AS_OF = date(2026, 12, 1)


def test_candidates_stay_inside_their_limits() -> None:
    end = AS_OF + timedelta(days=89)
    shop = ss.shop_candidates(AS_OF)
    assert len(shop) == len(set(shop)) and len(shop) > 30
    for kind, n, freq, first in shop:
        rows = ss.new_loan_schedule(Decimal("100000"), Decimal("0"), kind, n, freq, first)
        assert AS_OF < rows[0][0] and rows[-1][0] <= end  # DEC-33: inside the 90-day horizon
    harvest = date(2027, 5, 5)
    assert all(first > harvest for _, _, _, first in ss.farm_candidates(AS_OF, harvest))  # SUG-13
    assert all(first > AS_OF for _, _, _, first in ss.farm_candidates(AS_OF, AS_OF - timedelta(days=10)))


def test_pick_labels_and_closest() -> None:
    def res(n: int, fits: bool, margin: str, short: str = "0") -> ss.Result:
        cand = ("equal_installments", n, "weekly", AS_OF + timedelta(days=7))
        rows = tuple(ss.new_loan_schedule(Decimal("12000"), Decimal("0"), *cand))
        return ss.Result(cand, rows, fits, Decimal(margin), Decimal(short))

    chosen, closest = ss.pick([res(2, True, "100"), res(6, True, "900"), res(12, True, "500"), res(3, False, "-5", "5")])
    assert closest is None
    assert [(label, r.candidate[1]) for label, r in chosen] == [("safest", 6), ("fastest", 2), ("smallest_installment", 12)]
    chosen, closest = ss.pick([res(2, True, "100")])
    assert [label for label, _ in chosen] == ["safest"]  # one schedule is shown once, not three times
    chosen, closest = ss.pick([res(2, False, "-9", "9"), res(4, False, "-3", "3")])
    assert chosen == [] and closest.candidate[1] == 4
    assert ss.pick([]) == ([], None)


def _options(c, pid: str) -> dict:
    r = c.get(f"/api/v1/profiles/{pid}/financing-requests/{request_id(c, pid)}/schedule-options")
    assert r.status_code == 200, r.text
    assert_no_forbidden(r.json())
    return r.json()


def _apply_and_assess(c, pid: str, opt: dict) -> dict:
    url = f"/api/v1/profiles/{pid}/financing-requests/{request_id(c, pid)}"
    patch = {k: opt[k] for k in ("schedule_type", "installment_count", "installment_frequency", "first_due_date")}
    assert c.patch(url, json=patch).status_code == 200
    a = c.post(url + "/assessments")
    assert a.status_code == 201, a.text
    return a.json()


def test_d1_shop_options_all_pass_the_real_assessment(seeded, client) -> None:  # noqa: F811
    pid = demo_profile(client, "01900000001", "Rahim Store")["id"]
    out = _options(client, pid)
    assert out["blocked_by"] == [] and out["closest"] is None and out["margin_kind"] == "lowest_balance_above_reserve"
    assert 1 <= len(out["options"]) <= 3 and out["options"][0]["label"] == "safest"
    assert out["fit_count"] >= len(out["options"]) and out["tried"] > 30
    for opt in out["options"]:
        assert opt["total_repayment"] == "216000.00"  # 200,000 + the 16,000 the owner entered, for every option
        a = _apply_and_assess(client, pid, opt)
        assert a["status"] == "ready_for_lender_review", opt
        assert Decimal(a["base_result"]["min_balance_after_payment"]) - Decimal("10000") == Decimal(opt["margin"])


def test_d2_nothing_fits_is_said_plainly(seeded, client) -> None:  # noqa: F811
    pid = demo_profile(client, "01900000002", "Karim Variety Store")["id"]
    out = _options(client, pid)
    assert out["blocked_by"] == [] and out["options"] == [] and out["fit_count"] == 0
    assert Decimal(out["closest"]["shortfall"]) > 0  # the nearest miss, with how much is short
    assert _apply_and_assess(client, pid, out["closest"])["status"] == "not_affordable_base_case"


def test_d3_farm_options_follow_the_harvest(seeded, client) -> None:  # noqa: F811
    client_profile = demo_profile(client, "01900000001", "Rahim Rice Farm")
    out = _options(client, client_profile["id"])
    assert out["blocked_by"] == [] and out["margin_kind"] == "surplus_at_due_date" and out["options"]
    for opt in out["options"]:
        a = _apply_and_assess(client, client_profile["id"], opt)
        assert a["status"] == "ready_for_lender_review", opt
        assert a["base_result"]["surplus_or_shortfall"] == opt["margin"]
        assert opt["first_due_date"] > a["base_result"]["expected_harvest_date"]


def test_d4_blocked_until_the_basics_exist_and_other_owner_404(seeded, client, make_client) -> None:  # noqa: F811
    pid = demo_profile(client, "01900000004", "Selina Tailoring")["id"]
    out = _options(client, pid)
    assert out["options"] == [] and out["closest"] is None and out["tried"] == 0
    assert "debts_not_declared" in out["blocked_by"] and "terms_incomplete" not in out["blocked_by"]
    other = make_client()
    owner(other)
    r = other.get(f"/api/v1/profiles/{pid}/financing-requests/{request_id(client, pid)}/schedule-options")
    assert r.status_code == 404
