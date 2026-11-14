from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from .common import InModel, MoneyOut, NonNegativeMoneyIn, PositiveMoneyIn
from .season import PriceSource, Quantity

PurposeCategory = Literal["inventory", "farm_inputs", "equipment", "other"]
ScheduleType = Literal["equal_installments", "single_payment"]
Frequency = Literal["weekly", "monthly"]


def _len(min_len: int, max_len: int, key: str):
    def check(v: str | None) -> str | None:
        if v is None:
            return None
        if not min_len <= len(v) <= max_len:
            raise ValueError(key)
        return v
    return AfterValidator(check)


def _blank_none(max_len: int, key: str):
    def check(v: str | None) -> str | None:
        if not v:
            return None
        if len(v) > max_len:
            raise ValueError(key)
        return v
    return AfterValidator(check)


PurposeText = Annotated[str, _len(2, 500, "fin.err.purpose_text")]
LongNote = Annotated[str | None, _blank_none(500, "err.field.too_long")]
ItemName = Annotated[str, _len(1, 120, "fin.err.item_name")]
UnitText = Annotated[str, _len(1, 20, "season.err.unit")]
NoteText = Annotated[str | None, _blank_none(200, "err.field.too_long")]


class FinancingCreate(InModel):
    requested_amount: PositiveMoneyIn
    purpose_text: PurposeText
    purpose_category: PurposeCategory
    desired_start_date: date | None = None
    season_id: uuid.UUID | None = None


class FinancingPatch(InModel):
    """Wizard autosave (SCR-O11): any subset; only fields that are sent change."""

    requested_amount: PositiveMoneyIn | None = None
    purpose_text: PurposeText | None = None
    purpose_category: PurposeCategory | None = None
    desired_start_date: date | None = None
    season_id: uuid.UUID | None = None
    associated_expenses: NonNegativeMoneyIn | None = None
    liquidity_buffer: NonNegativeMoneyIn | None = None
    buffer_justification: LongNote = None
    cash_safely_available: NonNegativeMoneyIn | None = None
    committed_financing: NonNegativeMoneyIn | None = None
    current_cash_balance: NonNegativeMoneyIn | None = None
    minimum_cash_reserve: NonNegativeMoneyIn | None = None
    schedule_type: ScheduleType | None = None
    installment_count: Annotated[int, Field(ge=1, le=60)] | None = None
    installment_frequency: Frequency | None = None
    first_due_date: date | None = None
    interest_fees_total: NonNegativeMoneyIn | None = None
    interest_fees_unknown: bool | None = None
    over_request_explanation: LongNote = None


class ItemCreate(InModel):
    """Either a manual item, or `copy_from_season_cost_item_id` (FR-FIN-08)."""

    copy_from_season_cost_item_id: uuid.UUID | None = None
    item_name: ItemName | None = None
    quantity: Quantity | None = None
    unit: UnitText | None = None
    unit_price: NonNegativeMoneyIn | None = None
    price_source_type: PriceSource | None = None
    price_date: date | None = None
    price_source_note: NoteText = None


class ItemPatch(InModel):
    item_name: ItemName | None = None
    quantity: Quantity | None = None
    unit: UnitText | None = None
    unit_price: NonNegativeMoneyIn | None = None
    price_source_type: PriceSource | None = None
    price_date: date | None = None
    price_source_note: NoteText = None
    confirmed: Literal[True] | None = None


class ItemOut(BaseModel):
    id: uuid.UUID
    item_name: str
    quantity: str
    unit: str
    unit_price: MoneyOut | None  # null while an AI proposal has no owner price yet
    line_total: MoneyOut
    price_source_type: str
    price_date: date | None
    price_source_note: str | None
    ai_proposed: bool
    confirmed: bool
    source_season_cost_item_id: uuid.UUID | None


class InstallmentOut(BaseModel):
    due_date: date
    amount: MoneyOut


class PreviewOut(BaseModel):
    """Live display of what the owner has entered so far; the assessment
    recomputes everything on the server."""

    items_total: MoneyOut
    funding_gap: MoneyOut
    request_minus_gap: MoneyOut
    gap_inputs_complete: bool
    installments: list[InstallmentOut]
    repayment_total: MoneyOut | None


class AssessmentRef(BaseModel):
    id: uuid.UUID
    status: str
    is_stale: bool
    created_at: datetime


class FinancingOut(BaseModel):
    id: uuid.UUID
    season_id: uuid.UUID | None
    status: str
    requested_amount: MoneyOut
    purpose_text: str
    purpose_category: str
    desired_start_date: date | None
    associated_expenses: MoneyOut | None
    liquidity_buffer: MoneyOut | None
    buffer_justification: str | None
    cash_safely_available: MoneyOut | None
    committed_financing: MoneyOut | None
    current_cash_balance: MoneyOut | None
    minimum_cash_reserve: MoneyOut | None
    schedule_type: str | None
    installment_count: int | None
    installment_frequency: str | None
    first_due_date: date | None
    interest_fees_total: MoneyOut | None
    interest_fees_unknown: bool
    over_request_explanation: str | None
    items: list[ItemOut]
    preview: PreviewOut
    latest_assessment: AssessmentRef | None
    label_key: str = "fin.proposal_banner"
    created_at: datetime
    updated_at: datetime


class FinancingList(BaseModel):
    items: list[FinancingOut]
    total: int
