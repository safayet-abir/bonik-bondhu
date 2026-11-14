"""Grounding check (SUG-23, FR-ADV-03) and forbidden phrases (FR-ADV-05).

Every number in an advisor reply must appear in this turn's tool output,
the user's own message or today's date; small whole numbers 1–31 (day and
week counts) are always allowed. Bangla digits, thousands commas and
"Tk"/"৳" are normalised, and 18000 == 18,000 == 18000.00."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
SMALL = frozenset(Decimal(i) for i in range(1, 32))
_FORBIDDEN = re.compile(r"\bapproved\b|\beligib\w*|credit score|probability of default|\bguaranteed?\b|"
                        r"অনুমোদিত|যোগ্য|ক্রেডিট স্কোর", re.IGNORECASE)


def numbers(text: str) -> set[Decimal]:
    out: set[Decimal] = set()
    for m in _NUM.finditer((text or "").translate(BN_DIGITS)):
        try:
            out.add(Decimal(m.group().replace(",", "")))
        except InvalidOperation:
            continue
    return out


def grounded(reply: str, sources: list[str]) -> bool:
    allowed = set(SMALL).union(*(numbers(s) for s in sources))
    return numbers(reply) <= allowed


def has_forbidden(text: str) -> bool:
    return bool(_FORBIDDEN.search(text or ""))
