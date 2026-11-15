"""Receipt photo -> draft fields (F1; AI doc §3). Validates and normalises
the model's JSON; the draft never becomes a transaction until the owner
confirms (FR-EXT-02/03)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from .grounding import BN_DIGITS

PROMPT_NAME = "receipt_v2"  # v2 (15 Nov 2026, after E2): seller-vs-sale rule, d/m/y dates
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_NAME}.txt").read_text(encoding="utf-8")
OLD_DATE_DAYS = 365  # an older date is possible but usually a misread year: shown as "unsure"
TXN_TYPES = ("sale_cash", "sale_credit", "purchase_cash", "purchase_credit", "payable_payment",
             "operating_expense", "unknown")
MAX_AMOUNT = Decimal("99999999999.99")


class _Field(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | float | int | None = None
    confidence: float = 0.0


class ReceiptJSON(BaseModel):
    model_config = ConfigDict(extra="forbid")  # AI doc §2: reject extra fields
    txn_type: _Field
    amount: _Field
    value_date: _Field
    supplier_name: _Field | None = None
    note: _Field | None = None


def _conf(f: _Field | None) -> float:
    return round(min(max(float(f.confidence), 0.0), 1.0), 2) if f else 0.0


def _text(f: _Field | None, limit: int) -> dict:
    v = str(f.value).strip()[:limit] if f is not None and f.value not in (None, "") else None
    return {"value": v or None, "confidence": _conf(f) if v else 0.0}


def proposed(raw: dict, today: date) -> dict:
    """Clean draft fields; ValueError when the output does not fit the schema (AI-02).
    Unusable single values become null with confidence 0 for the owner to fill."""
    try:
        r = ReceiptJSON.model_validate(raw)
    except ValidationError as exc:
        raise ValueError("schema") from exc
    kind = str(r.txn_type.value or "unknown")
    known = kind in TXN_TYPES
    amount = None
    try:
        a = Decimal(str(r.amount.value).translate(BN_DIGITS).replace(",", "").replace("Tk", "")
                    .replace("৳", "").strip())
        if 0 < a <= MAX_AMOUNT:
            amount = f"{a.quantize(Decimal('0.01'))}"
    except (InvalidOperation, ValueError):
        pass
    value_date, date_conf = None, _conf(r.value_date)
    try:
        d = date.fromisoformat(str(r.value_date.value).translate(BN_DIGITS).strip())
        if d <= today + timedelta(days=1):
            value_date = d.isoformat()
            if d < today - timedelta(days=OLD_DATE_DAYS):
                date_conf = min(date_conf, 0.5)
    except ValueError:
        pass
    return {
        "txn_type": {"value": kind if known else "unknown", "confidence": _conf(r.txn_type) if known else 0.0},
        "amount": {"value": amount, "confidence": _conf(r.amount) if amount else 0.0},
        "value_date": {"value": value_date, "confidence": date_conf if value_date else 0.0},
        "supplier_name": _text(r.supplier_name, 120),
        "note": _text(r.note, 300),
    }
