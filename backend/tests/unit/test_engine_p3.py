"""P3 engine unit tests: UT-02 baseline, UT-03 new schedule, UT-05 gap,
UT-06 projection (base + scenario hooks), UT-07 crop check, UT-10 rounding.
Every golden number is asserted literally (Testing §4) AND against the oracle."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.engine import baseline as bl
from app.engine import crop, funding, projection, schedules
from app.engine.money import money
from tests.golden import reference_calculations as ref

AS_OF = date(2026, 12, 1)
GOLD = ref.golden_cases(AS_OF)


def plus(n: int) -> str:
    return (AS_OF + timedelta(days=n)).isoformat()


# ----------------------------------------------------------------- fixtures as ledger rows
def d1_rows() -> list[tuple[date, str, D]]:
    """Seed-shaped D1 ledger: per week one cash sale, 3 linked purchases,
    one 18,000 expense and (weeks 4, 8) an owner withdrawal (not operating)."""
    coll = [152000, 128500, 171000, 140500, 118000, 162000, 149500, 133000]
    purch = [100000, 83000, 112000, 92000, 75000, 106000, 98000, 86000]
    rows = []
    for i in range(1, 9):
        d = AS_OF - timedelta(days=7 * (9 - i) - 3)
        rows.append((d, "sale_cash", D(coll[i - 1])))
        for share in ("0.65", "0.25", "0.10"):
            rows.append((d, "purchase_cash", money(D(purch[i - 1]) * D(share))))
        rows.append((d, "operating_expense", D(18000)))
        if i in (4, 8):
            rows.append((d, "owner_withdrawal", D(15000)))
    return rows


def d2_rows() -> list[tuple[date, str, D]]:
    nets = [9000, 7500, 11000, 6000, 8500, 10000]
    rows = []
    for i in range(1, 7):
        d = AS_OF - timedelta(days=7 * (7 - i) - 3)
        rows += [(d, "sale_cash", D(30000 + nets[i - 1])), (d, "purchase_cash", D(24000)),
                 (d, "operating_expense", D(6000))]
    return rows


def d4_rows() -> list[tuple[date, str, D]]:
    rows = []
    for i in (1, 2):
        d = AS_OF - timedelta(days=7 * (3 - i) - 3)
        rows += [(d, "sale_cash", D(9000)), (d, "purchase_cash", D(3000)), (d, "operating_expense", D(2000))]
    return rows


def base_of(rows) -> bl.Baseline:
    return bl.weekly_baseline(bl.weekly_blocks(AS_OF, rows))


# ----------------------------------------------------------------- UT-02 baseline
def test_blocks_are_complete_weeks_ending_yesterday() -> None:
    blocks = bl.weekly_blocks(AS_OF, [])
    assert len(blocks) == 8
    assert blocks[-1].start == AS_OF - timedelta(days=7) and blocks[-1].end == AS_OF - timedelta(days=1)
    assert blocks[0].start == AS_OF - timedelta(days=56)


def test_today_and_older_than_window_ignored() -> None:
    rows = [(AS_OF, "sale_cash", D(999)), (AS_OF - timedelta(days=57), "sale_cash", D(999))]
    assert not any(b.has_records for b in bl.weekly_blocks(AS_OF, rows))


def test_d1_baseline_matches_golden() -> None:
    b = base_of(d1_rows())
    g = GOLD["D1"]["baseline"]
    assert b.status == "ok" and b.weeks_used == 8
    assert money(b.net_weekly_expected) == D("32312.50") == D(g["net_weekly_expected"])
    assert money(b.net_weekly_low) == D("25000.00") and money(b.net_weekly_high) == D("41000.00")
    assert money(b.collections_weekly_expected) == D("144312.50")
    assert money(b.payments_weekly_expected) == D("112000.00")
    assert money(b.purchases_weekly_expected) == D("94000.00") == D(g["purchases_weekly_expected"])


def test_owner_withdrawal_is_not_an_operating_payment() -> None:
    rows = [r for r in d1_rows() if r[1] != "owner_withdrawal"]
    assert base_of(rows) == base_of(d1_rows())


def test_d2_missing_weeks_are_not_zero() -> None:
    b = base_of(d2_rows())
    assert b.weeks_used == 6
    assert money(b.net_weekly_expected) == D("8666.67") == D(GOLD["D2"]["baseline"]["net_weekly_expected"])
    assert money(b.net_weekly_low) == D("6000.00") and money(b.net_weekly_high) == D("11000.00")


def test_d4_two_weeks_is_insufficient() -> None:
    b = base_of(d4_rows())
    assert b.status == "insufficient_history" and b.weeks_used == 2
    assert bl.horizons(b, AS_OF, []) == {}


def test_weekly_only_recorder_four_weeks_is_ok() -> None:  # Testing §6
    rows = [(AS_OF - timedelta(days=7 * k), "sale_cash", D(5000)) for k in range(1, 5)]
    assert base_of(rows).status == "ok"


def test_d1_horizons() -> None:
    h = bl.horizons(base_of(d1_rows()), AS_OF, [])
    assert h["7"] == {"low": "25000.00", "expected": "32312.50", "known_debt_service": "0.00"}
    assert (h["30"]["low"], h["30"]["expected"]) == ("107142.86", "138482.14")
    assert (h["60"]["low"], h["60"]["expected"]) == ("214285.71", "276964.29")
    assert (h["90"]["low"], h["90"]["expected"]) == ("321428.57", "415446.43")


def test_horizon_known_debt_service_window() -> None:
    rows = [(AS_OF, D(100)), (AS_OF + timedelta(days=6), D(200)), (AS_OF + timedelta(days=7), D(400))]
    h = bl.horizons(base_of(d1_rows()), AS_OF, rows)
    assert h["7"]["known_debt_service"] == "300.00" and h["30"]["known_debt_service"] == "700.00"


# ----------------------------------------------------------------- UT-03 new schedule
def test_d1_new_schedule_12_weekly() -> None:
    rows = schedules.new_loan_schedule(D(200000), D(16000), "equal_installments", 12, "weekly",
                                       AS_OF + timedelta(days=7))
    assert [a for _, a in rows] == [D("18000.00")] * 12
    assert rows[0][0].isoformat() == plus(7) and rows[-1][0].isoformat() == plus(84)
    assert [(d.isoformat(), str(a)) for d, a in rows] == GOLD["D1"]["installments"]


def test_rounding_remainder_goes_to_last() -> None:
    rows = schedules.new_loan_schedule(D(100000), D(0), "equal_installments", 3, "monthly", date(2027, 1, 31))
    assert [a for _, a in rows] == [D("33333.33"), D("33333.33"), D("33333.34")]
    assert rows[1][0] == date(2027, 2, 28) and rows[2][0] == date(2027, 3, 31)


def test_single_payment() -> None:
    assert schedules.new_loan_schedule(D(40000), D(2400), "single_payment", 1, "weekly", date(2027, 5, 20)) == \
        [(date(2027, 5, 20), D("42400.00"))]


# ----------------------------------------------------------------- UT-05 gap
@pytest.mark.parametrize(("case", "items", "args", "request_amt", "gap", "rmg"), [
    ("D1", [(D(100), D(1500))], (D(10000), D(20000), D(30000), D(0)), D(200000), "150000.00", "50000.00"),
    ("D2", [(D(1), D(70000))], (D(3000), D(5000), D(8000), D(0)), D(80000), "70000.00", "10000.00"),
    ("D3", [(D(1), D(18000)), (D(1), D(12000)), (D(1), D(22000))], (D(0), D(3000), D(15000), D(0)),
     D(40000), "40000.00", "0.00"),
])
def test_funding_gap_golden(case, items, args, request_amt, gap, rmg) -> None:
    g = funding.funding_gap(items, *args, request_amt)
    assert (str(g.funding_gap), str(g.request_minus_gap)) == (gap, rmg)
    assert str(g.funding_gap) == GOLD[case]["funding_gap"]
    assert g.exceeds is (case != "D3")


def test_negative_gap_is_zero() -> None:
    g = funding.funding_gap([(D(1), D(1000))], D(0), D(0), D(5000), D(0), D(500))
    assert g.funding_gap == D("0.00") and g.request_minus_gap == D("500.00")


# ----------------------------------------------------------------- UT-06 projection
def d1_check(scn: projection.Scenario = projection.BASE) -> dict:
    rows = schedules.new_loan_schedule(D(200000), D(16000), "equal_installments", 12, "weekly",
                                       AS_OF + timedelta(days=7))
    return projection.shop_due_date_checks(AS_OF, base_of(d1_rows()), D(15000), D(10000), D(15000), [], rows, scn)


def test_d1_base_no_shortfall() -> None:
    r = d1_check()
    assert len(r["checks"]) == 12 and r["first_shortfall"] is None and r["beyond_horizon"] == []
    assert r["min_balance_after_payment"] == "21626.22"
    assert r["checks"][0]["date"] == plus(7) and r["checks"][0]["balance_after"] == "21626.22"
    assert r["min_balance_after_payment"] == GOLD["D1"]["base"]["min_balance_after_payment"]


@pytest.mark.parametrize(("scn", "key", "date_off", "bal", "short", "min_bal"), [
    (projection.Scenario("supplier_delay", D("0.65"), 7, AS_OF), "delay_7d", 7, "623.10", "9376.90", None),
    (projection.Scenario("supplier_delay", D("0.65"), 14, AS_OF), "delay_14d", 7, "-2377.35", "12377.35",
     "-16832.08"),
    (projection.Scenario("input_price_rise", D("0.65"), pct=D("0.15")), "input_price_rise_15", 14, "5534.88",
     "4465.12", "-50635.67"),
])
def test_d1_scenario_hooks(scn, key, date_off, bal, short, min_bal) -> None:
    r = d1_check(scn)
    fs = r["first_shortfall"]
    assert fs["date"] == plus(date_off) and fs["balance_after"] == bal and fs["shortfall_vs_reserve"] == short
    if min_bal:
        assert r["min_balance_after_payment"] == min_bal
    assert {k: fs[k] for k in GOLD["D1"][key]["first_shortfall"]} == GOLD["D1"][key]["first_shortfall"]


def test_d2_base_first_shortfall() -> None:
    h_end = schedules.horizon_end(AS_OF)
    debts = [("mfi", schedules.existing_debt_schedule(D(2500), D(60000), "weekly", AS_OF + timedelta(days=3),
                                                     h_end, AS_OF)),
             ("samity", schedules.existing_debt_schedule(D(3000), D(18000), "monthly", AS_OF + timedelta(days=10),
                                                        h_end, AS_OF))]
    new = schedules.new_loan_schedule(D(80000), D(4000), "equal_installments", 12, "weekly", AS_OF + timedelta(days=7))
    r = projection.shop_due_date_checks(AS_OF, base_of(d2_rows()), D(4000), D(2000), D(8000), debts, new)
    assert len(r["checks"]) == 27
    fs = r["first_shortfall"]
    assert fs["date"] == plus(7) and fs["balance_after"] == "-746.97" and fs["shortfall_vs_reserve"] == "2746.97"
    assert r["min_balance_after_payment"] == "-69216.63"
    assert r["min_balance_after_payment"] == GOLD["D2"]["base"]["min_balance_after_payment"]


def test_installment_beyond_horizon_listed() -> None:
    rows = schedules.new_loan_schedule(D(120000), D(0), "equal_installments", 6, "monthly", AS_OF + timedelta(days=7))
    r = projection.shop_due_date_checks(AS_OF, base_of(d1_rows()), D(0), D(0), D(0), [], rows)
    assert [b["installment_no"] for b in r["beyond_horizon"]] == [4, 5, 6]


# ----------------------------------------------------------------- UT-07 crop
D3 = dict(output_low=D(2700), price_low=D(28), output_exp=D(3300), total_planned_costs=D(65000),
          remaining_costs_outside_request=D(8500), start_balance=D(8500), debts_due_by_due=D(6000),
          reserve=D(5000), repayment_total=D(42400), harvest_date=date(2027, 5, 5), due_date=date(2027, 5, 20))


def test_d3_crop_base_and_scenarios() -> None:
    base = crop.crop_check(**D3)
    assert (base["pre_harvest_balance"], base["available_at_due_date"], base["surplus_or_shortfall"]) == \
        (D("0.00"), D("64600.00"), D("22200.00"))
    assert base["covered"] and base["loan_cover_price_per_unit"] == D("19.78")
    assert base["break_even_price_per_unit"] == D("19.70")
    price = crop.crop_check(**D3, price_factor=D("0.85"))
    assert price["available_at_due_date"] == D("53260.00") and price["surplus_or_shortfall"] == D("10860.00")
    yld = crop.crop_check(**D3, yield_factor=D("0.80"))
    assert yld["available_at_due_date"] == D("49480.00") and yld["loan_cover_price_per_unit"] == D("24.72")
    inputs = crop.crop_check(**D3, cost_factor=D("1.15"))
    assert inputs["pre_harvest_shortfall"] == D("1275.00") and inputs["available_at_due_date"] == D("63325.00")
    assert inputs["covered"]
    for ours, key in ((base, "base"), (price, "harvest_price_fall_15"), (yld, "yield_shortfall_20"),
                      (inputs, "input_price_rise_15")):
        oracle = GOLD["D3"][key]
        assert {k: str(v) if not isinstance(v, bool) else v for k, v in ours.items()} == oracle


def test_crop_due_before_harvest_insufficient() -> None:
    r = crop.crop_check(**{**D3, "due_date": date(2027, 5, 1)})
    assert r == {"status": "insufficient_information", "reason": "repayment_due_before_expected_harvest"}


def test_crop_household_reduces_cash() -> None:
    """Our extension: a farm profile's declared household money is not free.
    With zero household the result is exactly the reference."""
    r = crop.crop_check(**D3, household_to_harvest=D(1000), household_after_harvest=D(500))
    assert r["pre_harvest_shortfall"] == D("1000.00")
    assert r["available_at_due_date"] == D("63100.00")
    assert r["loan_cover_price_per_unit"] == money((D(42400) + 6000 + 5000 + 8500 + 1500 - 8500) / 2700)


# ----------------------------------------------------------------- UT-10 rounding
def test_round_half_up() -> None:
    assert money(D("0.005")) == D("0.01") and money(D("2.675")) == D("2.68") and money(D("-0.005")) == D("-0.01")
