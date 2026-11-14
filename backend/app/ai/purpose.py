"""Financing purpose text -> item list (F7; AI doc §5). The AI never
supplies prices: price or amount fields in its output are dropped (AI-08);
the owner adds the price and its source, then confirms each item."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from .grounding import BN_DIGITS

PROMPT = (Path(__file__).parent / "prompts" / "purpose_v1.txt").read_text(encoding="utf-8")
MAX_ITEMS = 20


class _Item(BaseModel):
    model_config = ConfigDict(extra="ignore")  # unit_price, amount … are thrown away
    item_name: str
    quantity: str | float | int | None = None
    unit: str | None = None


class PurposeJSON(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[_Item]


def items(raw: dict) -> list[dict]:
    """[{item_name, quantity: Decimal, unit}] — ValueError when the output does not fit."""
    try:
        parsed = PurposeJSON.model_validate(raw)
    except ValidationError as exc:
        raise ValueError("schema") from exc
    out = []
    for i in parsed.items[:MAX_ITEMS]:
        name = i.item_name.strip()[:120]
        if not name:
            continue
        try:
            q = Decimal(str(i.quantity).translate(BN_DIGITS).replace(",", "")).quantize(Decimal("0.001"))
            if not Decimal("0") < q <= Decimal("99999999999"):
                q = Decimal(1)
        except (InvalidOperation, ValueError):
            q = Decimal(1)  # unknown quantity: 1, the owner edits it
        out.append({"item_name": name, "quantity": q, "unit": (i.unit or "").strip()[:20] or "pcs"})
    return out
