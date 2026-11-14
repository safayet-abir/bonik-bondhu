"""Single source of "now" so tests can move the clock (session expiry,
consent expiry). Business dates use Asia/Dhaka; timestamps are UTC (TRD §11)."""
from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

DHAKA = ZoneInfo("Asia/Dhaka")

_override: datetime | None = None


def utcnow() -> datetime:
    return _override if _override is not None else datetime.now(UTC)


def today() -> date:
    """Business date in Bangladesh."""
    return utcnow().astimezone(DHAKA).date()


def set_now(value: datetime | None) -> None:
    """Test hook: freeze the clock at `value` (aware datetime) or reset with None."""
    global _override
    if value is not None and value.tzinfo is None:
        raise ValueError("set_now needs a timezone-aware datetime")
    _override = value
