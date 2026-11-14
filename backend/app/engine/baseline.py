"""Forecast baseline (F3; Architecture §5.1; SUG-07). Pure functions
mirroring reference_calculations.weekly_baseline — no DB, no clock.

Weekly blocks are complete 7-day windows ending yesterday:
block k (k = 1..window) covers [as_of − 7k, as_of − 7k + 6].
A block without any confirmed operating record is MISSING, not zero
(weekly recorders are not penalised, S1 F5)."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from .money import ZERO, money

COLLECTION_TYPES = frozenset({"sale_cash", "receivable_collection"})
PAYMENT_TYPES = frozenset({"purchase_cash", "payable_payment", "operating_expense"})
PURCHASE_TYPES = frozenset({"purchase_cash", "payable_payment"})
RECORD_TYPES = COLLECTION_TYPES | PAYMENT_TYPES  # "operating" types = has_records
HORIZONS = (7, 30, 60, 90)
METHOD_VERSION = "weekly-baseline-v1"


@dataclass
class WeekBlock:
    start: date
    end: date
    collections: Decimal = ZERO
    payments: Decimal = ZERO
    purchases: Decimal = ZERO
    has_records: bool = False


@dataclass(frozen=True)
class Baseline:
    """Unrounded values: the projection divides them by 7, so rounding
    happens only when they are shown or stored (SUG-06)."""

    status: str  # ok | insufficient_history
    weeks_used: int
    net_weekly_expected: Decimal = ZERO
    net_weekly_low: Decimal = ZERO
    net_weekly_high: Decimal = ZERO
    collections_weekly_expected: Decimal = ZERO
    payments_weekly_expected: Decimal = ZERO
    purchases_weekly_expected: Decimal = ZERO
    blocks: tuple[WeekBlock, ...] = field(default=(), compare=False)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def weekly_blocks(as_of: date, entries: Iterable[tuple[date, str, Decimal]], window_weeks: int = 8) -> list[WeekBlock]:
    """Aggregate confirmed (value_date, txn_type, amount) rows into blocks,
    oldest first. Rows outside the window or of non-operating types are ignored."""
    blocks = {k: WeekBlock(as_of - timedelta(days=7 * k), as_of - timedelta(days=7 * k - 6))
              for k in range(1, window_weeks + 1)}
    for value_date, txn_type, amount in entries:
        if txn_type not in RECORD_TYPES:
            continue
        days_ago = (as_of - value_date).days
        if days_ago < 1:
            continue
        k = (days_ago + 6) // 7
        b = blocks.get(k)
        if b is None:
            continue
        b.has_records = True
        if txn_type in COLLECTION_TYPES:
            b.collections += amount
        else:
            b.payments += amount
            if txn_type in PURCHASE_TYPES:
                b.purchases += amount
    return [blocks[k] for k in range(window_weeks, 0, -1)]


def weekly_baseline(blocks: Sequence[WeekBlock], window_weeks: int = 8, min_weeks: int = 4) -> Baseline:
    used = [b for b in blocks[-window_weeks:] if b.has_records]
    if len(used) < min_weeks:
        return Baseline("insufficient_history", len(used), blocks=tuple(blocks))
    nets = [b.collections - b.payments for b in used]
    n = Decimal(len(used))
    return Baseline(
        status="ok",
        weeks_used=len(used),
        net_weekly_expected=sum(nets, ZERO) / n,
        net_weekly_low=min(nets),
        net_weekly_high=max(nets),
        collections_weekly_expected=sum((b.collections for b in used), ZERO) / n,
        payments_weekly_expected=sum((b.payments for b in used), ZERO) / n,
        purchases_weekly_expected=sum((b.purchases for b in used), ZERO) / n,
        blocks=tuple(blocks),
    )


def horizons(baseline: Baseline, as_of: date, debt_rows: Iterable[tuple[date, Decimal]]) -> dict[str, dict[str, str]]:
    """FR-FC-04: cumulative low / expected net cash for 7/30/60/90 days and
    the known scheduled debt payments due in [as_of, as_of + h − 1]."""
    if not baseline.ok:
        return {}
    rows = list(debt_rows)
    out: dict[str, dict[str, str]] = {}
    for h in HORIZONS:
        end = as_of + timedelta(days=h - 1)
        debt = sum((a for d, a in rows if as_of <= d <= end), ZERO)
        out[str(h)] = {
            "low": f"{money(baseline.net_weekly_low / 7 * h):.2f}",
            "expected": f"{money(baseline.net_weekly_expected / 7 * h):.2f}",
            "known_debt_service": f"{money(debt):.2f}",
        }
    return out
