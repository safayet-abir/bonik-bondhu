"""Shared Pydantic types. Money is serialised as a 2-decimal string and
parsed from numbers or strings with Bangla/Latin digits (API spec §1).

Validators raise ValueError("<i18n key>") so the 422 envelope carries a
translatable key per field."""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

from ..engine.money import MAX_AMOUNT, money_str, parse_amount


def _parse_money(v: object) -> Decimal:
    try:
        return parse_amount(v)
    except ValueError as exc:
        raise ValueError("err.field.amount_invalid") from exc


def _check_cents(d: Decimal) -> Decimal:
    if d != d.quantize(Decimal("0.01")):
        raise ValueError("entry.err.amount_decimals")
    if d > MAX_AMOUNT:
        raise ValueError("entry.err.amount_too_large")
    return d


def _positive(d: Decimal) -> Decimal:
    if d <= 0:
        raise ValueError("entry.err.amount")
    return _check_cents(d)


def _non_negative(d: Decimal) -> Decimal:
    if d < 0:
        raise ValueError("err.field.amount_negative")
    return _check_cents(d)


_out = PlainSerializer(money_str, return_type=str)

MoneyOut = Annotated[Decimal, _out]
PositiveMoneyIn = Annotated[Decimal, BeforeValidator(lambda v: _positive(_parse_money(v))), _out]
NonNegativeMoneyIn = Annotated[Decimal, BeforeValidator(lambda v: _non_negative(_parse_money(v))), _out]


class InModel(BaseModel):
    """Request bodies: unknown fields are ignored (e.g. a client-sent `role`
    can never escalate privileges — SEC-15), strings are stripped."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
