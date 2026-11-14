"""Funding gap (F7; S1 Appendix A2; Architecture §5.3). Pure functions
mirroring reference_calculations.funding_gap."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .money import ZERO, money


@dataclass(frozen=True)
class Gap:
    items_total: Decimal
    funding_gap: Decimal
    request_minus_gap: Decimal

    @property
    def exceeds(self) -> bool:
        """SUG-11: 0 % tolerance — any amount above the gap is flagged."""
        return self.request_minus_gap > 0


def items_total(items: Iterable[tuple[Decimal, Decimal]]) -> Decimal:
    """Σ quantity × unit price over CONFIRMED items only (caller filters)."""
    return money(sum((q * p for q, p in items), ZERO))


def funding_gap(items: Iterable[tuple[Decimal, Decimal]], associated_expenses: Decimal, liquidity_buffer: Decimal,
                cash_safely_available: Decimal, committed_financing: Decimal, requested_amount: Decimal) -> Gap:
    total = items_total(items)
    gap = total + associated_expenses + liquidity_buffer - cash_safely_available - committed_financing
    gap = money(max(ZERO, gap))
    return Gap(items_total=total, funding_gap=gap, request_minus_gap=money(requested_amount - gap))
