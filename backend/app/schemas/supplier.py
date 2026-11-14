from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator

from ..engine.money import parse_amount
from .common import InModel, OptText


def _share(v: object) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        d = parse_amount(v)
    except ValueError as exc:
        raise ValueError("err.field.amount_invalid") from exc
    if not Decimal(0) <= d <= Decimal(100) or d != d.quantize(Decimal("0.01")):
        raise ValueError("supplier.err.share")
    return d


def _name(v: str | None) -> str | None:
    if v is not None and not 1 <= len(v) <= 80:
        raise ValueError("supplier.err.name")
    return v


SupplierName = Annotated[str, AfterValidator(_name)]
SharePct = Annotated[Decimal | None, BeforeValidator(_share)]


class SupplierCreate(InModel):
    display_name: SupplierName
    goods_supplied: OptText = None
    district: OptText = None
    upazila: OptText = None
    declared_purchase_share_pct: SharePct = None


class SupplierPatch(InModel):
    display_name: SupplierName | None = None
    goods_supplied: OptText = None
    district: OptText = None
    upazila: OptText = None
    declared_purchase_share_pct: SharePct = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    display_name: str
    goods_supplied: str | None
    district: str | None
    upazila: str | None
    declared_purchase_share_pct: str | None
    is_active: bool


class SupplierList(BaseModel):
    items: list[SupplierOut]
    total: int
