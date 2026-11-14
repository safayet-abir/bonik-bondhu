"""Shop affordability: daily low-case projection checked at every due date
(S1 Appendix A2, §5.1; DEC-29/33/35–37; Architecture §5.2). Pure function
mirroring reference_calculations.shop_due_date_checks, including the
scenario hooks used by P4 (SUG-09). Scenarios never change the status
(DEC-30) — the caller decides what a result means."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .baseline import Baseline
from .money import ZERO, money
from .schedules import HORIZON_DAYS

DAYS_PER_YEAR = Decimal(365)  # SUG-08: monthly -> daily = monthly × 12 / 365


@dataclass(frozen=True)
class Scenario:
    kind: str = "base"            # base | supplier_delay | input_price_rise
    share: Decimal = ZERO         # supplier share (0..1)
    days: int = 0                 # delay length (7 or 14, S1 L2)
    start: date | None = None
    pct: Decimal = ZERO           # price rise (0.15)


BASE = Scenario()


def household_daily(household_monthly: Decimal) -> Decimal:
    return household_monthly * 12 / DAYS_PER_YEAR


def _s(x: Decimal) -> str:
    return f"{money(x):.2f}"


def shop_due_date_checks(as_of: date, baseline: Baseline, start_balance: Decimal, reserve: Decimal,
                         household_monthly: Decimal,
                         existing_debts: Sequence[tuple[str, Sequence[tuple[date, Decimal]]]],
                         new_rows: Sequence[tuple[date, Decimal]], scenario: Scenario = BASE) -> dict:
    """Walk day by day over [as_of, as_of + 89]: add the low-case daily net
    minus household money, subtract every outflow due that day, and compare
    the balance after payment with the owner's minimum reserve."""
    horizon_end = as_of + timedelta(days=HORIZON_DAYS - 1)
    daily_low = baseline.net_weekly_low / 7
    daily_exp = baseline.net_weekly_expected / 7
    daily_purch = baseline.purchases_weekly_expected / 7
    hh = household_daily(household_monthly)

    outflows: dict[date, list[tuple[str, Decimal]]] = {}
    for label, rows in existing_debts:
        for d, amt in rows:
            outflows.setdefault(d, []).append(("existing:" + label, amt))
    beyond = []
    for i, (d, amt) in enumerate(new_rows, 1):
        if d > horizon_end:
            beyond.append({"installment_no": i, "due_date": d.isoformat(), "amount": _s(amt)})
        else:
            outflows.setdefault(d, []).append((f"new:{i}", amt))

    bal = start_balance
    checks: list[dict] = []
    first_shortfall = None
    d = as_of
    while d <= horizon_end:
        delta = daily_low - hh
        if (scenario.kind == "supplier_delay" and scenario.start is not None
                and scenario.start <= d < scenario.start + timedelta(days=scenario.days)):
            delta -= scenario.share * daily_exp
        if scenario.kind == "input_price_rise":
            delta -= scenario.pct * scenario.share * daily_purch
        bal += delta
        if d in outflows:
            today_out = outflows[d]
            for _, amt in today_out:
                bal -= amt
            new_here = [a for label, a in today_out if label.startswith("new:")]
            short = reserve - bal if bal < reserve else ZERO
            row = {
                "date": d.isoformat(),
                "paid": _s(sum((a for _, a in today_out), ZERO)),
                "new_installment": _s(sum(new_here, ZERO)),
                "existing_paid": _s(sum((a for label, a in today_out if not label.startswith("new:")), ZERO)),
                "balance_after": _s(bal),
                "shortfall_vs_reserve": _s(short),
            }
            checks.append(row)
            if short > 0 and first_shortfall is None:
                first_shortfall = row
        d += timedelta(days=1)
    min_bal = min((Decimal(c["balance_after"]) for c in checks), default=start_balance)
    return {
        "checks": checks,
        "first_shortfall": first_shortfall,
        "beyond_horizon": beyond,
        "min_balance_after_payment": _s(min_bal),
        "any_shortfall": first_shortfall is not None,
    }
