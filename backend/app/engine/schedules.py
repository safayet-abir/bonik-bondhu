"""Repayment schedules (Architecture §5; reference_calculations §3).
Pure functions: no DB, no clock — dates are passed in."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from .money import ZERO, money

Row = tuple[date, Decimal]
HORIZON_DAYS = 90  # S1 F3 horizons 7/30/60/90; the check window is [as_of, as_of+89]


def horizon_end(as_of: date) -> date:
    return as_of + timedelta(days=HORIZON_DAYS - 1)


def add_months(d: date, n: int) -> date:
    """Calendar month step, clamped to month end (31 Jan + 1 -> 28/29 Feb)."""
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


def new_loan_schedule(principal: Decimal, interest_fees: Decimal, schedule_type: str,
                      n: int, freq: str, first_due: date) -> list[Row]:
    """DEC-28 owner-proposed terms. Equal installments: money(total/n) each,
    the LAST installment absorbs the rounding difference."""
    total = principal + interest_fees
    if schedule_type == "single_payment":
        return [(first_due, money(total))]
    each = money(total / Decimal(n))
    rows = [(step(first_due, freq, k), each) for k in range(n)]
    diff = total - each * Decimal(n)
    rows[-1] = (rows[-1][0], money(rows[-1][1] + diff))
    return rows


def existing_debt_schedule(installment: Decimal | None, outstanding: Decimal, freq: str,
                           next_due: date | None, horizon_end: date,
                           as_of: date | None = None) -> list[Row]:
    """Declared debt -> dated installments from `next_due` until the
    outstanding balance is used up (last = min(installment, remaining));
    `single` = the whole outstanding once; stops at `horizon_end`.

    Dates before `as_of` are skipped (owner has not updated the debt; the
    caller flags `existing_debt_dates_outdated`). Skipped dates do NOT use up
    the outstanding balance, so the remaining payments still fall inside the
    horizon — the cautious reading."""
    rows: list[Row] = []
    remaining = outstanding
    if next_due is None or remaining <= 0:
        return rows
    if freq == "single":
        if next_due <= horizon_end and (as_of is None or next_due >= as_of):
            rows.append((next_due, money(remaining)))
        return rows
    if installment is None or installment <= 0:
        raise ValueError("installment required")
    k = 0
    while remaining > ZERO:
        d = step(next_due, freq, k)
        k += 1
        if d > horizon_end:
            break
        if as_of is not None and d < as_of:
            continue
        pay = min(installment, remaining)
        rows.append((d, money(pay)))
        remaining -= pay
    return rows


def dates_outdated(next_due: date | None, as_of: date) -> bool:
    """True when a declared debt's next due date is already in the past."""
    return next_due is not None and next_due < as_of
