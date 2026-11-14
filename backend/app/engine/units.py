"""Land units (MP §4B; SUG-14). Acre is the base unit. Bigha differs by
region, so it has NO default: the farmer enters "1 bigha = N decimal"."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

SQFT_PER_ACRE = Decimal(43560)
DECIMAL_PER_ACRE = Decimal(100)
ACRE_PLACES = Decimal("0.0001")  # farming_seasons.area_acres NUMERIC(12,4)
AREA_UNITS = ("acre", "decimal", "sq_ft", "bigha")


class BighaFactorRequired(ValueError):
    pass


def to_acres(value: Decimal, unit: str, decimals_per_bigha: Decimal | None = None) -> Decimal:
    if unit == "acre":
        return value
    if unit == "decimal":
        return value / DECIMAL_PER_ACRE
    if unit == "sq_ft":
        return value / SQFT_PER_ACRE
    if unit == "bigha":
        if decimals_per_bigha is None or decimals_per_bigha <= 0:
            raise BighaFactorRequired("bigha requires a user-entered local factor")
        return value * decimals_per_bigha / DECIMAL_PER_ACRE
    raise ValueError(unit)


def acres_for_storage(value: Decimal, unit: str, decimals_per_bigha: Decimal | None = None) -> Decimal:
    return to_acres(value, unit, decimals_per_bigha).quantize(ACRE_PLACES, rounding=ROUND_HALF_UP)
