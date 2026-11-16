"""Repayment Fit Finder (Plan Ultra F1; SUG-56). Pure candidate generation and ranking.

A schedule *search*, not an optimiser and not machine learning: every candidate is judged by the same
affordability check the assessment uses (the caller passes it in as `check`), so an option shown here is
one the assessment accepts. The total to repay is the same for every candidate (principal + the interest
and fees the owner entered); a real lender may price a longer term differently. The owner picks, and it
stays their own proposal — not a lender offer (DEC-28)."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .schedules import HORIZON_DAYS, Row, add_months, new_loan_schedule

Candidate = tuple[str, int, str, date]  # schedule_type, installments, frequency, first_due
# check(rows) -> (fits, margin, shortfall): margin = money left above the reserve at the tightest point
Check = Callable[[Sequence[Row]], tuple[bool, Decimal, Decimal]]


@dataclass(frozen=True)
class Result:
    candidate: Candidate
    rows: tuple[Row, ...]
    fits: bool
    margin: Decimal
    shortfall: Decimal

    @property
    def last_due(self) -> date:
        return self.rows[-1][0]

    @property
    def largest_installment(self) -> Decimal:
        return max(a for _, a in self.rows)


def shop_candidates(as_of: date) -> list[Candidate]:
    """Schedules that end inside the 90-day forecast horizon (DEC-33)."""
    end = as_of + timedelta(days=HORIZON_DAYS - 1)
    out: list[Candidate] = []
    for start in (7, 14, 30):
        first = as_of + timedelta(days=start)
        out += [("equal_installments", n, "weekly", first) for n in range(2, 13)
                if first + timedelta(days=7 * (n - 1)) <= end]
        out += [("equal_installments", n, "monthly", first) for n in (2, 3) if add_months(first, n - 1) <= end]
    out += [("single_payment", 1, "monthly", as_of + timedelta(days=d)) for d in (30, 60, HORIZON_DAYS - 1)]
    return out


def farm_candidates(as_of: date, harvest: date) -> list[Candidate]:
    """Farm income arrives at harvest, so every payment is on or after it (SUG-13)."""
    base = max(harvest, as_of)
    out: list[Candidate] = [("single_payment", 1, "monthly", base + timedelta(days=d)) for d in (7, 15, 30, 45)]
    out += [("equal_installments", n, "monthly", base + timedelta(days=d)) for d in (7, 15) for n in (2, 3)]
    return out


def search(principal: Decimal, interest_fees: Decimal, candidates: Sequence[Candidate], check: Check) -> list[Result]:
    results = []
    for c in candidates:
        rows = tuple(new_loan_schedule(principal, interest_fees, c[0], c[1], c[2], c[3]))
        fits, margin, shortfall = check(rows)
        results.append(Result(c, rows, fits, margin, shortfall))
    return results


def pick(results: Sequence[Result]) -> tuple[list[tuple[str, Result]], Result | None]:
    """Up to three different fitting schedules — safest, fastest, smallest installment — and, when nothing
    fits, the candidate that comes closest (smallest shortfall)."""
    ok = [r for r in results if r.fits]
    if not ok:
        return [], min(results, key=lambda r: (r.shortfall, r.last_due), default=None)
    choices = [
        ("safest", max(ok, key=lambda r: (r.margin, -r.last_due.toordinal()))),
        ("fastest", min(ok, key=lambda r: (r.last_due, -r.margin))),
        ("smallest_installment", min(ok, key=lambda r: (r.largest_installment, -r.margin))),
    ]
    seen: set[Candidate] = set()
    out = []
    for label, r in choices:
        if r.candidate not in seen:
            seen.add(r.candidate)
            out.append((label, r))
    return out, None
