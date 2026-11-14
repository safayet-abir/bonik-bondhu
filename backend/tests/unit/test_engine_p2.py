"""P2 engine unit tests: UT-04 schedules, UT-09 units, crop arithmetic
(golden D3 numbers, Testing §4.4). Cross-checked against the oracle."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.engine import crop, schedules, units
from tests.golden import reference_calculations as ref

AS_OF = date(2026, 12, 1)
H_END = schedules.horizon_end(AS_OF)


# ---------------------------------------------------------------- UT-04
def test_horizon_is_90_days_inclusive() -> None:
    assert H_END == AS_OF + timedelta(days=89)


def test_weekly_mfi_until_horizon() -> None:  # D2 MFI: 2,500 weekly from +3 -> 13 in horizon
    rows = schedules.existing_debt_schedule(D(2500), D(60000), "weekly", AS_OF + timedelta(days=3), H_END, AS_OF)
    assert len(rows) == 13
    assert rows[0] == (AS_OF + timedelta(days=3), D("2500.00"))
    assert rows[-1][0] == AS_OF + timedelta(days=87)
    assert rows == ref.existing_debt_schedule(2500, 60000, "weekly", AS_OF + timedelta(days=3), H_END)


def test_weekly_outstanding_cap_last_is_remainder() -> None:
    rows = schedules.existing_debt_schedule(D(2500), D(6000), "weekly", AS_OF, H_END, AS_OF)
    assert [a for _, a in rows] == [D("2500.00"), D("2500.00"), D("1000.00")]


def test_monthly_samity_three_in_horizon() -> None:  # D2 samity 3,000 monthly from +10
    rows = schedules.existing_debt_schedule(D(3000), D(30000), "monthly", AS_OF + timedelta(days=10), H_END, AS_OF)
    assert [d for d, _ in rows] == [date(2026, 12, 11), date(2027, 1, 11), date(2027, 2, 11)]


def test_single_is_whole_outstanding_once() -> None:  # D3 dealer credit
    rows = schedules.existing_debt_schedule(None, D(6000), "single", AS_OF + timedelta(days=10), H_END, AS_OF)
    assert rows == [(AS_OF + timedelta(days=10), D("6000.00"))]
    beyond = schedules.existing_debt_schedule(None, D(6000), "single", date(2027, 5, 15), H_END, AS_OF)
    assert beyond == []  # outside the horizon


def test_past_dates_are_skipped_and_flagged() -> None:
    stale = AS_OF - timedelta(days=14)
    rows = schedules.existing_debt_schedule(D(1000), D(3000), "weekly", stale, H_END, AS_OF)
    # -14 and -7 skipped, they do not use up the outstanding balance
    assert [d for d, _ in rows] == [AS_OF, AS_OF + timedelta(days=7), AS_OF + timedelta(days=14)]
    assert schedules.dates_outdated(stale, AS_OF) is True
    assert schedules.dates_outdated(AS_OF, AS_OF) is False
    assert schedules.existing_debt_schedule(None, D(500), "single", stale, H_END, AS_OF) == []


def test_zero_outstanding_has_no_rows() -> None:
    assert schedules.existing_debt_schedule(D(100), D(0), "weekly", AS_OF, H_END, AS_OF) == []


def test_add_months_clamps_month_end() -> None:
    assert schedules.add_months(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert schedules.add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert schedules.add_months(date(2026, 12, 15), 2) == date(2027, 2, 15)


def test_new_loan_schedule_last_absorbs_rounding() -> None:
    rows = schedules.new_loan_schedule(D(100000), D(0), "equal_installments", 3, "monthly", AS_OF)
    assert [a for _, a in rows] == [D("33333.33"), D("33333.33"), D("33333.34")]
    d1 = schedules.new_loan_schedule(D(200000), D(16000), "equal_installments", 12, "weekly",
                                     AS_OF + timedelta(days=7))
    assert len(d1) == 12 and {a for _, a in d1} == {D("18000.00")}
    assert d1[-1][0] == AS_OF + timedelta(days=84)
    assert schedules.new_loan_schedule(D(40000), D(2400), "single_payment", 1, "monthly",
                                       date(2027, 5, 20)) == [(date(2027, 5, 20), D("42400.00"))]


# ---------------------------------------------------------------- UT-09
@pytest.mark.parametrize(("value", "unit", "factor", "acres"), [
    (D(150), "decimal", None, D("1.5")),
    (D(21780), "sq_ft", None, D("0.5")),
    (D(2), "bigha", D(33), D("0.66")),
    (D("1.25"), "acre", None, D("1.25")),
])
def test_to_acres(value, unit, factor, acres) -> None:
    assert units.to_acres(value, unit, factor) == acres
    assert units.to_acres(value, unit, factor) == ref.to_acres(value, unit, factor)


def test_bigha_without_factor_is_an_error() -> None:
    with pytest.raises(units.BighaFactorRequired):
        units.to_acres(D(2), "bigha")


def test_acres_storage_precision() -> None:
    assert units.acres_for_storage(D(1), "sq_ft") == D("0.0000")
    assert units.acres_for_storage(D(150), "decimal") == D("1.5000")


# ---------------------------------------------------------------- crop (D3)
def test_d3_income_range_and_break_even() -> None:
    r = crop.income_range((D(2700), D(3300), D(3750)), (D(28), D(32), D(35)))
    assert (r.low, r.expected, r.high) == (D("75600.00"), D("105600.00"), D("131250.00"))
    assert crop.break_even_price(D(65000), D(3300)) == D("19.70")


def test_d3_crop_check_matches_golden() -> None:
    res = crop.crop_check(D(2700), D(28), D(3300), D(65000), D(8500), D(8500), D(6000), D(5000),
                          D(42400), date(2027, 5, 5), date(2027, 5, 20))
    assert res["pre_harvest_balance"] == D("0.00")
    assert res["available_at_due_date"] == D("64600.00")
    assert res["surplus_or_shortfall"] == D("22200.00") and res["covered"] is True
    assert res["loan_cover_price_per_unit"] == D("19.78")
    late = crop.crop_check(D(2700), D(28), D(3300), D(65000), D(0), D(0), D(0), D(0), D(1),
                           date(2027, 5, 21), date(2027, 5, 20))
    assert late["status"] == "insufficient_information"
