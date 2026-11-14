"""Supplier concentration (S1 L2 Stage 1; Architecture §5.5; SUG-10). Pure
functions mirroring reference_calculations.concentration. Shares are kept
unrounded for the dependency test; percentages are rounded only for display."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Generic, TypeVar

from .money import ZERO

K = TypeVar("K")
PCT_STEP = Decimal("0.1")
SHARE_STEP = Decimal("0.0001")  # scenario share precision (65% -> 0.6500)


@dataclass(frozen=True)
class Concentration(Generic[K]):
    total: Decimal | None          # None when shares are owner-reported
    shares: dict[K, Decimal]       # 0..1, unrounded
    top: K | None
    top_share: Decimal
    high_dependency: bool


def pct(share: Decimal) -> Decimal:
    """0.65 -> 65.0 (display, ROUND_HALF_UP)."""
    return (share * 100).quantize(PCT_STEP, rounding=ROUND_HALF_UP)


def scenario_share(share: Decimal) -> Decimal:
    return share.quantize(SHARE_STEP, rounding=ROUND_HALF_UP)


def _summarize(shares: dict[K, Decimal], total: Decimal | None, threshold: Decimal) -> Concentration[K]:
    if not shares:
        return Concentration(total, {}, None, ZERO, False)
    top = max(shares, key=lambda k: shares[k])  # ties: first inserted wins (stable)
    return Concentration(total, shares, top, shares[top], shares[top] >= threshold)


def from_amounts(amounts: Mapping[K, Decimal], threshold: Decimal) -> Concentration[K]:
    """Linked purchases: share = supplier total ÷ total of all linked purchases."""
    total = sum(amounts.values(), ZERO)
    if total <= 0:
        return _summarize({}, ZERO, threshold)
    return _summarize({k: v / total for k, v in amounts.items() if v > 0}, total, threshold)


def from_declared(declared_pct: Mapping[K, Decimal], threshold: Decimal) -> Concentration[K]:
    """Owner-reported shares (% of purchases), used as stated — never
    normalised, because the owner may not list every supplier."""
    return _summarize({k: v / 100 for k, v in declared_pct.items() if v > 0}, None, threshold)
