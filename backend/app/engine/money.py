"""Money arithmetic (SUG-06): Decimal only, ROUND_HALF_UP to paisa, BDT."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext

getcontext().prec = 28

D = Decimal
CENT = Decimal("0.01")
ZERO = Decimal(0)
MAX_AMOUNT = Decimal("99999999999.99")  # NUMERIC(14,2)

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def money(x: Decimal) -> Decimal:
    """Round to paisa, half-up. Quantize only for output/storage."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def money_str(x: Decimal) -> str:
    """API representation: string with exactly 2 decimals, e.g. "150000.00"."""
    return f"{money(x):.2f}"


def parse_amount(value: object) -> Decimal:
    """Accept numbers or strings, Bangla or Latin digits, commas and spaces
    ("১,৫০,০০০", "150000", 150000.5). Raises ValueError on anything else.
    Floats are converted through str() so 0.1 stays 0.1."""
    if isinstance(value, bool):
        raise ValueError("not a number")
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, int | float):
        d = Decimal(str(value))
    elif isinstance(value, str):
        s = value.translate(_BN_DIGITS).replace(",", "").replace(" ", "").strip()
        try:
            d = Decimal(s)
        except InvalidOperation as exc:
            raise ValueError("not a number") from exc
    else:
        raise ValueError("not a number")
    if not d.is_finite():
        raise ValueError("not a number")
    return d
