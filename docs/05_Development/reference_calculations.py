"""
Bonik Bondhu MVP - reference calculations (specification oracle)
=================================================================

PURPOSE
    This file is NOT the production backend. It is an executable specification
    of the deterministic money rules used in the MVP, so that the backend
    team (or a coding AI) can compare their implementation against known
    expected outputs (see TESTING_AND_ACCEPTANCE.md, section "Golden cases").

SOURCE BASIS (see DECISIONS_ASSUMPTIONS_AND_BACKLOG.md for full register)
    - Accounting rules ............ S1 sec.4 F2; S1 Appendix A1/A4
    - Cash / capacity equations ... S1 Appendix A2
    - Funding gap ................. S1 sec.4 F7; S1 Appendix A2
    - Forecast baseline/horizon ... S1 sec.4 F3; MP sec.6 F3
    - Low-income case test ........ S1 sec.5.1 (stage 1)
    - Supplier/price scenarios .... S1 sec.6 L2 (7/14-day delay, 15% price rise)
    - Parameter VALUES marked SUG-xx are proposals outside current sources and
      need team approval (MP sec.23 rule 3). They are configurable constants.

Run:  python3 -I reference_calculations.py
Only the Python standard library is used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
import calendar
import json

getcontext().prec = 28
D = Decimal
CENT = D("0.01")


def money(x: Decimal) -> Decimal:
    """Round to paisa, half-up (SUG-06)."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Configurable parameters (all SUG-xx: pending approval)
# ---------------------------------------------------------------------------
HISTORY_WEEKS = 8            # SUG-07: look-back window (complete 7-day blocks)
MIN_WEEKS_WITH_RECORDS = 4   # SUG-07: below this -> "insufficient_history"
HORIZON_DAYS = 90            # S1 F3 lists 7/30/60/90-day horizons; 90 is max
DAYS_PER_YEAR = D(365)       # SUG-08: monthly -> daily = monthly*12/365
HIGH_DEPENDENCY_SHARE = D("0.50")  # SUG-10
CROP_PRICE_FALL = D("0.15")  # SUG-12
CROP_YIELD_SHORTFALL = D("0.20")  # SUG-12
INPUT_PRICE_RISE = D("0.15")  # S1 L2 example scenario "15% input price rise"


# ---------------------------------------------------------------------------
# 1. Accounting: transaction types and their effects (S1 F2, Appendix A4)
# ---------------------------------------------------------------------------
# effect columns: cash, sales_recorded, operating_cash, receivable, payable
TXN_EFFECTS = {
    "sale_cash":                 (+1, +1, +1, 0, 0),
    "sale_credit":               (0, +1, 0, +1, 0),   # baki: receivable, NOT cash
    "receivable_collection":     (+1, 0, +1, -1, 0),
    "purchase_cash":             (-1, 0, -1, 0, 0),
    "purchase_credit":           (0, 0, 0, 0, +1),
    "payable_payment":           (-1, 0, -1, 0, -1),
    "operating_expense":         (-1, 0, -1, 0, 0),
    "loan_received":             (+1, 0, 0, 0, 0),    # financing cash, NOT sales
    "loan_principal_repayment":  (-1, 0, 0, 0, 0),    # reduces debt, NOT expense
    "loan_interest_fee_payment": (-1, 0, 0, 0, 0),    # tracked separately
    "owner_withdrawal":          (-1, 0, 0, 0, 0),    # household, NOT operating
    "owner_contribution":        (+1, 0, 0, 0, 0),    # owner money, NOT income
}
PURCHASE_TYPES = {"purchase_cash", "payable_payment"}


def summarize(transactions: list[dict]) -> dict:
    """Money summary for confirmed, non-voided transactions of ONE profile."""
    out = {k: D(0) for k in (
        "cash_net_change", "sales_recorded", "cash_sales", "credit_sales",
        "operating_cash_in", "operating_cash_out", "net_operating_cash",
        "receivables_outstanding", "payables_outstanding",
        "financing_received", "principal_repaid", "interest_fees_paid",
        "owner_withdrawals", "owner_contributions")}
    for t in transactions:
        if t.get("status", "confirmed") != "confirmed":
            continue
        a = D(str(t["amount"]))
        ty = t["txn_type"]
        cash, sales, op, recv, pay = TXN_EFFECTS[ty]
        out["cash_net_change"] += cash * a
        out["sales_recorded"] += sales * a
        if ty == "sale_cash":
            out["cash_sales"] += a
        if ty == "sale_credit":
            out["credit_sales"] += a
        if op > 0:
            out["operating_cash_in"] += a
        if op < 0:
            out["operating_cash_out"] += a
        out["receivables_outstanding"] += recv * a
        out["payables_outstanding"] += pay * a
        if ty == "loan_received":
            out["financing_received"] += a
        if ty == "loan_principal_repayment":
            out["principal_repaid"] += a
        if ty == "loan_interest_fee_payment":
            out["interest_fees_paid"] += a
        if ty == "owner_withdrawal":
            out["owner_withdrawals"] += a
        if ty == "owner_contribution":
            out["owner_contributions"] += a
    out["net_operating_cash"] = out["operating_cash_in"] - out["operating_cash_out"]
    return {k: money(v) for k, v in out.items()}


# ---------------------------------------------------------------------------
# 2. Forecast baseline (S1 F3, MP F3: rolling averages; SUG-07 parameters)
# ---------------------------------------------------------------------------
@dataclass
class Baseline:
    status: str                      # "ok" | "insufficient_history"
    weeks_used: int
    net_weekly_expected: Decimal = D(0)
    net_weekly_low: Decimal = D(0)
    net_weekly_high: Decimal = D(0)
    collections_weekly_expected: Decimal = D(0)
    payments_weekly_expected: Decimal = D(0)
    purchases_weekly_expected: Decimal = D(0)


def weekly_baseline(weeks: list[dict]) -> Baseline:
    """weeks: list of complete 7-day blocks (oldest..newest) within the
    look-back window. Each dict: collections, payments, purchases, has_records.
    Blocks without any confirmed operating record are treated as MISSING,
    not as zero (S1 F5: weekly recorders must not be penalised)."""
    used = [w for w in weeks[-HISTORY_WEEKS:] if w["has_records"]]
    if len(used) < MIN_WEEKS_WITH_RECORDS:
        return Baseline("insufficient_history", len(used))
    nets = [D(str(w["collections"])) - D(str(w["payments"])) for w in used]
    n = D(len(used))
    return Baseline(
        status="ok",
        weeks_used=len(used),
        net_weekly_expected=sum(nets) / n,
        net_weekly_low=min(nets),
        net_weekly_high=max(nets),
        collections_weekly_expected=sum(D(str(w["collections"])) for w in used) / n,
        payments_weekly_expected=sum(D(str(w["payments"])) for w in used) / n,
        purchases_weekly_expected=sum(D(str(w["purchases"])) for w in used) / n,
    )


# ---------------------------------------------------------------------------
# 3. Schedules
# ---------------------------------------------------------------------------
def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def step(d: date, freq: str, k: int) -> date:
    if freq == "weekly":
        return d + timedelta(days=7 * k)
    if freq == "monthly":
        return add_months(d, k)
    raise ValueError(freq)


def new_loan_schedule(principal, interest_fees, schedule_type, n, freq, first_due):
    """DEC-28: 'equal_installments' or 'single_payment'. Terms are USER-ENTERED
    proposals, not lender offers (S1 sec.14 item 6)."""
    total = D(str(principal)) + D(str(interest_fees))
    if schedule_type == "single_payment":
        return [(first_due, money(total))]
    each = money(total / D(n))
    rows = [(step(first_due, freq, k), each) for k in range(n)]
    diff = total - each * D(n)  # last installment absorbs rounding
    rows[-1] = (rows[-1][0], money(rows[-1][1] + diff))
    return rows


def existing_debt_schedule(installment, outstanding, freq, next_due, horizon_end):
    """Declared debts -> dated installments until outstanding is exhausted.
    Scheduled contractual payments are known items, not ML guesses (S1 F3)."""
    rows, remaining, k = [], D(str(outstanding)), 0
    inst = D(str(installment))
    while remaining > 0:
        d = next_due if freq == "single" else step(next_due, freq, k)
        if d > horizon_end:
            break
        pay = min(inst, remaining) if freq != "single" else remaining
        rows.append((d, money(pay)))
        remaining -= pay
        k += 1
        if freq == "single":
            break
    return rows


# ---------------------------------------------------------------------------
# 4. Shop affordability: daily projection, checked at every due date
#    S1 Appendix A2: capacity = projected available cash before debt service
#    - required reserve - existing scheduled debt service; "test every new
#    schedule at its actual due dates". Low-income case per S1 sec.5.1.
# ---------------------------------------------------------------------------
@dataclass
class Scenario:
    kind: str = "base"            # base | supplier_delay | input_price_rise
    share: Decimal = D(0)         # supplier share (0..1)
    days: int = 0                 # delay length (7 or 14 per S1 L2)
    start: date | None = None
    pct: Decimal = D(0)           # price rise


def shop_due_date_checks(as_of, baseline: Baseline, start_balance, reserve,
                         household_monthly, existing_debts, new_rows,
                         scenario: Scenario = Scenario()):
    horizon_end = as_of + timedelta(days=HORIZON_DAYS - 1)
    daily_net_low = baseline.net_weekly_low / D(7)
    daily_net_exp = baseline.net_weekly_expected / D(7)
    daily_purch_exp = baseline.purchases_weekly_expected / D(7)
    household_daily = D(str(household_monthly)) * D(12) / DAYS_PER_YEAR

    outflows: dict[date, list] = {}
    for label, rows in existing_debts:
        for d, amt in rows:
            outflows.setdefault(d, []).append(("existing:" + label, amt))
    beyond = []
    for i, (d, amt) in enumerate(new_rows, 1):
        if d > horizon_end:
            beyond.append({"installment_no": i, "due_date": d.isoformat()})
        else:
            outflows.setdefault(d, []).append((f"new:{i}", amt))

    bal = D(str(start_balance))
    checks, first_shortfall = [], None
    d = as_of
    while d <= horizon_end:
        delta = daily_net_low - household_daily
        if scenario.kind == "supplier_delay" and scenario.start and \
                scenario.start <= d < scenario.start + timedelta(days=scenario.days):
            delta -= scenario.share * daily_net_exp          # SUG-09
        if scenario.kind == "input_price_rise":
            delta -= scenario.pct * scenario.share * daily_purch_exp  # SUG-09
        bal += delta
        if d in outflows:
            for label, amt in outflows[d]:
                bal -= amt
            new_here = [a for (l, a) in outflows[d] if l.startswith("new:")]
            short = D(str(reserve)) - bal if bal < D(str(reserve)) else D(0)
            row = {"date": d.isoformat(),
                   "paid": str(money(sum(a for _, a in outflows[d]))),
                   "new_installment": str(money(sum(new_here))) if new_here else "0.00",
                   "balance_after": str(money(bal)),
                   "shortfall_vs_reserve": str(money(short))}
            checks.append(row)
            if short > 0 and first_shortfall is None:
                first_shortfall = row
        d += timedelta(days=1)
    min_bal = min((D(c["balance_after"]) for c in checks), default=D(str(start_balance)))
    return {"checks": checks, "first_shortfall": first_shortfall,
            "beyond_horizon": beyond, "min_balance_after_payment": str(money(min_bal)),
            "any_shortfall": first_shortfall is not None}


# ---------------------------------------------------------------------------
# 5. Funding gap (S1 F7 + Appendix A2)
# ---------------------------------------------------------------------------
def funding_gap(purchase_items, associated_expenses, buffer, cash_safely_available,
                committed_financing):
    items = sum(D(str(q)) * D(str(p)) for q, p in purchase_items)
    gap = items + D(str(associated_expenses)) + D(str(buffer)) \
        - D(str(cash_safely_available)) - D(str(committed_financing))
    return money(items), money(max(D(0), gap))


# ---------------------------------------------------------------------------
# 6. Crop season check (S1 sec.5 crop row + sec.5.1 season journey)
# ---------------------------------------------------------------------------
def crop_check(output_low, price_low, output_exp, total_planned_costs,
               remaining_costs_outside_request, start_balance, debts_due_by_due,
               reserve, repayment_total, harvest_date, due_date,
               price_factor=D(1), yield_factor=D(1), cost_factor=D(1)):
    if harvest_date > due_date:
        return {"status": "insufficient_information",
                "reason": "repayment_due_before_expected_harvest"}
    income_low = D(str(output_low)) * yield_factor * D(str(price_low)) * price_factor
    remaining = D(str(remaining_costs_outside_request)) * cost_factor
    pre_harvest = D(str(start_balance)) - remaining
    available = pre_harvest + income_low - D(str(debts_due_by_due)) - D(str(reserve))
    required = D(str(repayment_total)) + D(str(debts_due_by_due)) + D(str(reserve)) \
        + remaining - D(str(start_balance))
    return {
        "income_low": str(money(income_low)),
        "pre_harvest_balance": str(money(pre_harvest)),
        "pre_harvest_shortfall": str(money(-pre_harvest)) if pre_harvest < 0 else "0.00",
        "available_at_due_date": str(money(available)),
        "repayment_due": str(money(D(str(repayment_total)))),
        "covered": available >= D(str(repayment_total)),
        "surplus_or_shortfall": str(money(available - D(str(repayment_total)))),
        # SUG-13: loan-cover price uses LOW output (S1 sec.5.1 "even the low case")
        "loan_cover_price_per_unit": str(money(required / (D(str(output_low)) * yield_factor))),
        "break_even_price_per_unit": str(money(D(str(total_planned_costs)) / D(str(output_exp)))),
    }


# ---------------------------------------------------------------------------
# 7. Supplier concentration (S1 L2 Stage 1)
# ---------------------------------------------------------------------------
def concentration(purchases_by_supplier: dict[str, Decimal]):
    total = sum(D(str(v)) for v in purchases_by_supplier.values())
    shares = {k: (D(str(v)) / total) for k, v in purchases_by_supplier.items()}
    top = max(shares, key=shares.get)
    return {"total_purchases": str(money(total)),
            "shares_pct": {k: str((v * 100).quantize(D("0.1"))) for k, v in shares.items()},
            "top_supplier": top,
            "top_share_pct": str((shares[top] * 100).quantize(D("0.1"))),
            "high_dependency_flag": shares[top] >= HIGH_DEPENDENCY_SHARE}


# ---------------------------------------------------------------------------
# 8. Land units (MP sec.4B; SUG-14)
# ---------------------------------------------------------------------------
SQFT_PER_ACRE = D(43560)
DECIMAL_PER_ACRE = D(100)


def to_acres(value, unit, decimals_per_bigha=None):
    v = D(str(value))
    if unit == "acre":
        return v
    if unit == "decimal":
        return v / DECIMAL_PER_ACRE
    if unit == "sq_ft":
        return v / SQFT_PER_ACRE
    if unit == "bigha":
        if decimals_per_bigha is None:
            raise ValueError("bigha requires a user-entered local factor")
        return v * D(str(decimals_per_bigha)) / DECIMAL_PER_ACRE
    raise ValueError(unit)


# ---------------------------------------------------------------------------
# GOLDEN DEMO CASES (all data FICTIONAL, labelled DEMO; MP sec.18)
# ---------------------------------------------------------------------------
def golden_cases(as_of: date) -> dict:
    res = {"as_of": as_of.isoformat()}

    # ---- D1 Rahim Store (DEMO): irregular sales, 65% supplier, request > gap
    d1_weeks = []
    coll = [152000, 128500, 171000, 140500, 118000, 162000, 149500, 133000]
    pay = [118000, 101000, 130000, 110000, 93000, 124000, 116000, 104000]
    for c, p in zip(coll, pay):
        d1_weeks.append({"collections": c, "payments": p, "purchases": p - 18000,
                         "has_records": True})
    b1 = weekly_baseline(d1_weeks)
    items_total, gap1 = funding_gap([(100, 1500)], 10000, 20000, 30000, 0)
    rows1 = new_loan_schedule(200000, 16000, "equal_installments", 12, "weekly",
                              as_of + timedelta(days=7))
    start1 = D(45000) - D(30000)
    conc1 = concentration({"Supplier A": 488800, "Supplier B": 188000, "Supplier C": 75200})
    share1 = D("0.65")
    base1 = shop_due_date_checks(as_of, b1, start1, 10000, 15000, [], rows1)
    delay7 = shop_due_date_checks(as_of, b1, start1, 10000, 15000, [], rows1,
                                  Scenario("supplier_delay", share1, 7, as_of))
    delay14 = shop_due_date_checks(as_of, b1, start1, 10000, 15000, [], rows1,
                                   Scenario("supplier_delay", share1, 14, as_of))
    rise15 = shop_due_date_checks(as_of, b1, start1, 10000, 15000, [], rows1,
                                  Scenario("input_price_rise", share1, pct=INPUT_PRICE_RISE))
    res["D1"] = {
        "baseline": {k: str(money(v)) if isinstance(v, Decimal) else v
                     for k, v in b1.__dict__.items()},
        "purpose_items_total": str(items_total), "funding_gap": str(gap1),
        "request_minus_gap": str(money(D(200000) - gap1)),
        "installments": [(d.isoformat(), str(a)) for d, a in rows1],
        "supplier_concentration": conc1,
        "base": summarize_check(base1), "delay_7d": summarize_check(delay7),
        "delay_14d": summarize_check(delay14), "input_price_rise_15": summarize_check(rise15),
        "expected_status": status_from(b1, base1, [], True),
    }

    # ---- D2 Karim Variety Store (DEMO): existing MFI + samity debt -> stress
    nets2 = [9000, 7500, 11000, 6000, 8500, 10000]
    d2_weeks = [{"collections": 30000 + n, "payments": 30000, "purchases": 24000,
                 "has_records": True} for n in nets2]
    d2_weeks = [{"collections": 0, "payments": 0, "purchases": 0, "has_records": False}] * 2 + d2_weeks
    b2 = weekly_baseline(d2_weeks)
    horizon_end = as_of + timedelta(days=HORIZON_DAYS - 1)
    debts2 = [("mfi_weekly", existing_debt_schedule(2500, 60000, "weekly", as_of + timedelta(days=3), horizon_end)),
              ("samity_monthly", existing_debt_schedule(3000, 18000, "monthly", as_of + timedelta(days=10), horizon_end))]
    items2, gap2 = funding_gap([(1, 70000)], 3000, 5000, 8000, 0)
    rows2 = new_loan_schedule(80000, 4000, "equal_installments", 12, "weekly", as_of + timedelta(days=7))
    base2 = shop_due_date_checks(as_of, b2, 12000 - 8000, 2000, 8000, debts2, rows2)
    res["D2"] = {
        "baseline": {k: str(money(v)) if isinstance(v, Decimal) else v for k, v in b2.__dict__.items()},
        "funding_gap": str(gap2), "request_minus_gap": str(money(D(80000) - gap2)),
        "base": summarize_check(base2),
        "expected_status": status_from(b2, base2, [], True),
    }

    # ---- D3 Rahim Rice Farm (DEMO, same user as D1): Boro rice, harvest-aligned
    harvest, due = date(2027, 5, 5), date(2027, 5, 20)
    items3, gap3 = funding_gap([(1, 18000), (1, 12000), (1, 22000)], 0, 3000, 15000, 0)
    common = dict(output_low=2700, price_low=28, output_exp=3300, total_planned_costs=65000,
                  remaining_costs_outside_request=8500, start_balance=23500 - 15000,
                  debts_due_by_due=6000, reserve=5000, repayment_total=42400,
                  harvest_date=harvest, due_date=due)
    res["D3"] = {
        "area_acres_from_150_decimal": str(to_acres(150, "decimal")),
        "income_range": {"low": "75600.00", "expected": "105600.00", "high": "131250.00"},
        "funding_gap": str(gap3), "request_minus_gap": str(money(D(40000) - gap3)),
        "base": crop_check(**common),
        "harvest_price_fall_15": crop_check(**common, price_factor=D(1) - CROP_PRICE_FALL),
        "yield_shortfall_20": crop_check(**common, yield_factor=D(1) - CROP_YIELD_SHORTFALL),
        "input_price_rise_15": crop_check(**common, cost_factor=D(1) + INPUT_PRICE_RISE),
        "expected_status": "ready_for_lender_review",
    }

    # ---- D4 Selina Tailoring (DEMO): insufficient information
    d4_weeks = [{"collections": 0, "payments": 0, "purchases": 0, "has_records": False}] * 6 + \
               [{"collections": 9000, "payments": 5000, "purchases": 3000, "has_records": True}] * 2
    b4 = weekly_baseline(d4_weeks)
    res["D4"] = {"baseline_status": b4.status, "weeks_used": b4.weeks_used,
                 "expected_status": "insufficient_information",
                 "expected_missing": ["debts_not_declared", "household_withdrawal_not_declared",
                                      "purpose_items_missing", "gap_inputs_missing",
                                      "terms_incomplete", "forecast_insufficient_history"]}

    # ---- E1 accounting fixture (S1 Appendix A4 negative cases)
    fx = [
        {"txn_type": "sale_cash", "amount": 5000},
        {"txn_type": "sale_credit", "amount": 2000},          # not cash
        {"txn_type": "loan_received", "amount": 50000},       # not sales
        {"txn_type": "purchase_cash", "amount": 3000},
        {"txn_type": "loan_principal_repayment", "amount": 4000},  # not expense
        {"txn_type": "loan_interest_fee_payment", "amount": 500},
        {"txn_type": "receivable_collection", "amount": 1500},
        {"txn_type": "owner_withdrawal", "amount": 1000},
        {"txn_type": "sale_cash", "amount": 7000, "status": "voided"},  # ignored
    ]
    res["E1_fixture_summary"] = {k: str(v) for k, v in summarize(fx).items()}
    res["land_units"] = {"1_acre_in_decimal": "100", "150_decimal_acres": str(to_acres(150, "decimal")),
                         "21780_sqft_acres": str(to_acres(21780, "sq_ft")),
                         "2_bigha_at_33_decimal_acres": str(to_acres(2, "bigha", 33))}
    return res


def summarize_check(r):
    return {"any_shortfall": r["any_shortfall"],
            "first_shortfall": r["first_shortfall"],
            "min_balance_after_payment": r["min_balance_after_payment"],
            "beyond_horizon": r["beyond_horizon"],
            "number_of_payment_dates_checked": len(r["checks"])}


def status_from(baseline, base_check, missing, complete):
    if baseline.status != "ok" or missing or not complete or base_check["beyond_horizon"]:
        return "insufficient_information"
    if base_check["any_shortfall"]:
        return "not_affordable_base_case"
    return "ready_for_lender_review"


if __name__ == "__main__":
    print(json.dumps(golden_cases(date(2026, 12, 1)), indent=2, default=str))
