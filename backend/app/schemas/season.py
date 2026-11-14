from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, PlainSerializer

from ..core.clock import today
from ..engine.money import parse_amount
from .common import InModel, MoneyOut, NonNegativeMoneyIn, OptText, PositiveMoneyIn

SeasonName = Literal["aman", "boro", "aus", "winter_vegetables", "other"]
AreaUnit = Literal["acre", "decimal", "sq_ft", "bigha"]
CostCategory = Literal["seed", "fertilizer", "pesticide", "irrigation", "labour", "land_lease", "transport", "other"]
PriceSource = Literal["supplier_quote", "own_purchase_history", "reference_market_price", "public_listing", "owner_estimate"]


def _positive_decimal(places: int, max_value: Decimal):
    quantum = Decimal(1).scaleb(-places)

    def parse(v: object) -> Decimal:
        try:
            d = parse_amount(v)
        except ValueError as exc:
            raise ValueError("err.field.amount_invalid") from exc
        if d <= 0:
            raise ValueError("season.err.positive")
        if d != d.quantize(quantum):
            raise ValueError("season.err.decimals")
        if d > max_value:
            raise ValueError("entry.err.amount_too_large")
        return d
    return parse


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f")


Area = Annotated[Decimal, BeforeValidator(_positive_decimal(4, Decimal("99999999.9999"))),
                 PlainSerializer(_plain, return_type=str)]
BighaFactor = Annotated[Decimal, BeforeValidator(_positive_decimal(3, Decimal("99999.999"))),
                        PlainSerializer(_plain, return_type=str)]
Quantity = Annotated[Decimal, BeforeValidator(_positive_decimal(3, Decimal("99999999999.999"))),
                     PlainSerializer(_plain, return_type=str)]


def _text(min_len: int, max_len: int, key: str):
    def check(v: str) -> str:
        if not min_len <= len(v) <= max_len:
            raise ValueError(key)
        return v
    return AfterValidator(check)


CropName = Annotated[str, _text(1, 60, "season.err.crop_name")]
ItemName = Annotated[str, _text(1, 80, "season.err.item_name")]
UnitText = Annotated[str, _text(1, 20, "season.err.unit")]


class _SeasonFields(InModel):
    variety: OptText = None
    season_label: OptText = None
    decimals_per_bigha: BighaFactor | None = None
    expected_output_low: PositiveMoneyIn | None = None
    expected_output_expected: PositiveMoneyIn | None = None
    expected_output_high: PositiveMoneyIn | None = None
    expected_price_low: PositiveMoneyIn | None = None
    expected_price_expected: PositiveMoneyIn | None = None
    expected_price_high: PositiveMoneyIn | None = None


class SeasonCreate(_SeasonFields):
    crop_name: CropName
    season_name: SeasonName
    area_value: Area
    area_unit: AreaUnit
    sowing_date: date
    expected_harvest_date: date


class SeasonPatch(_SeasonFields):
    crop_name: CropName | None = None
    season_name: SeasonName | None = None
    area_value: Area | None = None
    area_unit: AreaUnit | None = None
    sowing_date: date | None = None
    expected_harvest_date: date | None = None
    status: Literal["planned", "growing", "closed"] | None = None


def _not_future(v: date) -> date:
    if v > today() + timedelta(days=1):
        raise ValueError("entry.err.future_date")
    return v


class HarvestIn(InModel):
    actual_harvest_date: Annotated[date, AfterValidator(_not_future)]
    actual_output: NonNegativeMoneyIn


class CostItemCreate(InModel):
    category: CostCategory
    item_name: ItemName
    quantity: Quantity
    unit: UnitText
    unit_cost: NonNegativeMoneyIn
    planned_date: date | None = None
    price_source_type: PriceSource = "owner_estimate"
    price_source_note: OptText = None


class CostItemPatch(InModel):
    category: CostCategory | None = None
    item_name: ItemName | None = None
    quantity: Quantity | None = None
    unit: UnitText | None = None
    unit_cost: NonNegativeMoneyIn | None = None
    planned_date: date | None = None
    price_source_type: PriceSource | None = None
    price_source_note: OptText = None


class CostItemOut(BaseModel):
    id: uuid.UUID
    season_id: uuid.UUID
    category: str
    item_name: str
    quantity: str
    unit: str
    unit_cost: MoneyOut
    total_cost: MoneyOut
    planned_date: date | None
    price_source_type: str
    price_source_note: str | None
    paid_total: MoneyOut


class IncomeRangeOut(BaseModel):
    low: MoneyOut
    expected: MoneyOut
    high: MoneyOut


class SeasonOut(BaseModel):
    id: uuid.UUID
    crop_name: str
    variety: str | None
    season_name: str
    season_label: str | None
    area_value: str
    area_unit: str
    decimals_per_bigha: str | None
    area_acres: str
    sowing_date: date
    expected_harvest_date: date
    output_unit: str
    expected_output_low: MoneyOut | None
    expected_output_expected: MoneyOut | None
    expected_output_high: MoneyOut | None
    expected_price_low: MoneyOut | None
    expected_price_expected: MoneyOut | None
    expected_price_high: MoneyOut | None
    status: str
    actual_harvest_date: date | None
    actual_output: MoneyOut | None
    income_range: IncomeRangeOut | None
    created_at: datetime


class SeasonList(BaseModel):
    items: list[SeasonOut]
    total: int


class SeasonDetail(SeasonOut):
    cost_items: list[CostItemOut]


class LoanCoverBasis(BaseModel):
    financing_request_id: uuid.UUID
    repayment_total: MoneyOut


class SeasonSummaryOut(BaseModel):
    season: SeasonOut
    planned_cost_total: MoneyOut
    paid_cost_total: MoneyOut
    actual_sales_total: MoneyOut
    income_range: IncomeRangeOut | None
    break_even_price_per_kg: MoneyOut | None
    loan_cover_price_per_kg: MoneyOut | None = None   # P3 (needs a financing request)
    loan_cover_basis: LoanCoverBasis | None = None
    labels: list[str]
