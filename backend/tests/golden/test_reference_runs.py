"""P0-T06: the reference oracle reproduces every golden number in
TESTING_AND_ACCEPTANCE.md §4 (as_of = 2026-12-01). The production engine
(P1+) will be tested against the same values."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from . import reference_calculations as ref

AS_OF = date(2026, 12, 1)


@pytest.fixture(scope="module")
def golden() -> dict:
    return ref.golden_cases(AS_OF)


def d(offset: int) -> str:
    return (AS_OF + timedelta(days=offset)).isoformat()


def test_e1_accounting_fixture(golden: dict) -> None:
    assert golden["E1_fixture_summary"] == {
        "cash_net_change": "48000.00",
        "sales_recorded": "7000.00",
        "cash_sales": "5000.00",
        "credit_sales": "2000.00",
        "operating_cash_in": "6500.00",
        "operating_cash_out": "3000.00",
        "net_operating_cash": "3500.00",
        "receivables_outstanding": "500.00",
        "payables_outstanding": "0.00",
        "financing_received": "50000.00",
        "principal_repaid": "4000.00",
        "interest_fees_paid": "500.00",
        "owner_withdrawals": "1000.00",
        "owner_contributions": "0.00",
    }


def test_d1_rahim_store(golden: dict) -> None:
    g = golden["D1"]
    b = g["baseline"]
    assert (b["status"], b["weeks_used"]) == ("ok", 8)
    assert (b["net_weekly_expected"], b["net_weekly_low"], b["net_weekly_high"]) == (
        "32312.50", "25000.00", "41000.00")
    assert (b["collections_weekly_expected"], b["payments_weekly_expected"],
            b["purchases_weekly_expected"]) == ("144312.50", "112000.00", "94000.00")

    c = g["supplier_concentration"]
    assert c["total_purchases"] == "752000.00"
    assert c["shares_pct"] == {"Supplier A": "65.0", "Supplier B": "25.0", "Supplier C": "10.0"}
    assert c["high_dependency_flag"] is True

    assert (g["purpose_items_total"], g["funding_gap"], g["request_minus_gap"]) == (
        "150000.00", "150000.00", "50000.00")
    assert len(g["installments"]) == 12
    assert all(a == "18000.00" for _, a in g["installments"])
    assert (g["installments"][0][0], g["installments"][-1][0]) == (d(7), d(84))

    base = g["base"]
    assert base["any_shortfall"] is False
    assert base["number_of_payment_dates_checked"] == 12
    assert base["min_balance_after_payment"] == "21626.22"

    s7 = g["delay_7d"]["first_shortfall"]
    assert (s7["date"], s7["balance_after"], s7["shortfall_vs_reserve"]) == (d(7), "623.10", "9376.90")
    s14 = g["delay_14d"]
    assert (s14["first_shortfall"]["date"], s14["first_shortfall"]["balance_after"],
            s14["first_shortfall"]["shortfall_vs_reserve"]) == (d(7), "-2377.35", "12377.35")
    assert s14["min_balance_after_payment"] == "-16832.08"
    r15 = g["input_price_rise_15"]
    assert (r15["first_shortfall"]["date"], r15["first_shortfall"]["balance_after"],
            r15["first_shortfall"]["shortfall_vs_reserve"]) == (d(14), "5534.88", "4465.12")
    assert r15["min_balance_after_payment"] == "-50635.67"
    assert g["expected_status"] == "ready_for_lender_review"


def test_d2_karim_variety_store(golden: dict) -> None:
    g = golden["D2"]
    b = g["baseline"]
    assert (b["status"], b["weeks_used"]) == ("ok", 6)
    assert (b["net_weekly_expected"], b["net_weekly_low"], b["net_weekly_high"]) == (
        "8666.67", "6000.00", "11000.00")
    assert (g["funding_gap"], g["request_minus_gap"]) == ("70000.00", "10000.00")
    base = g["base"]
    assert base["number_of_payment_dates_checked"] == 27
    fs = base["first_shortfall"]
    assert (fs["date"], fs["balance_after"], fs["shortfall_vs_reserve"]) == (d(7), "-746.97", "2746.97")
    assert base["min_balance_after_payment"] == "-69216.63"
    assert g["expected_status"] == "not_affordable_base_case"


def test_d3_rahim_rice_farm(golden: dict) -> None:
    g = golden["D3"]
    assert g["area_acres_from_150_decimal"] == "1.5"
    assert (g["funding_gap"], g["request_minus_gap"]) == ("40000.00", "0.00")
    base = g["base"]
    assert base["pre_harvest_balance"] == "0.00"  # start 8,500 − remaining 8,500
    assert (base["available_at_due_date"], base["surplus_or_shortfall"], base["covered"]) == (
        "64600.00", "22200.00", True)
    assert (base["break_even_price_per_unit"], base["loan_cover_price_per_unit"]) == ("19.70", "19.78")
    pf = g["harvest_price_fall_15"]
    assert (pf["available_at_due_date"], pf["surplus_or_shortfall"], pf["covered"]) == (
        "53260.00", "10860.00", True)
    ys = g["yield_shortfall_20"]
    assert (ys["available_at_due_date"], ys["surplus_or_shortfall"], ys["loan_cover_price_per_unit"]) == (
        "49480.00", "7080.00", "24.72")
    ir = g["input_price_rise_15"]
    assert (ir["pre_harvest_shortfall"], ir["available_at_due_date"], ir["covered"]) == (
        "1275.00", "63325.00", True)
    assert g["expected_status"] == "ready_for_lender_review"


def test_d4_selina_tailoring(golden: dict) -> None:
    g = golden["D4"]
    assert (g["baseline_status"], g["weeks_used"]) == ("insufficient_history", 2)
    assert g["expected_missing"] == [
        "debts_not_declared", "household_withdrawal_not_declared", "purpose_items_missing",
        "gap_inputs_missing", "terms_incomplete", "forecast_insufficient_history"]


def test_land_units(golden: dict) -> None:
    u = golden["land_units"]
    assert ref.to_acres(150, "decimal") == ref.D("1.5")
    assert ref.to_acres(21780, "sq_ft") == ref.D("0.5")
    assert ref.to_acres(2, "bigha", 33) == ref.D("0.66")
    assert u["1_acre_in_decimal"] == "100"
    with pytest.raises(ValueError):
        ref.to_acres(2, "bigha")


def test_rounding_rules() -> None:
    assert ref.money(ref.D("0.005")) == ref.D("0.01")  # ROUND_HALF_UP (UT-10)
    rows = ref.new_loan_schedule(100000, 0, "equal_installments", 3, "weekly", AS_OF)
    assert [str(a) for _, a in rows] == ["33333.33", "33333.33", "33333.34"]  # UT-03
    feb = ref.new_loan_schedule(3000, 0, "equal_installments", 2, "monthly", date(2027, 1, 31))
    assert feb[1][0] == date(2027, 2, 28)
