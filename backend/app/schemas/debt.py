from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel

from .common import InModel, MoneyOut, NonNegativeMoneyIn, OptText, PositiveMoneyIn

LenderType = Literal["bank", "mfi", "ngo", "samity", "mohajon", "supplier_credit", "dealer_credit", "other"]
Frequency = Literal["weekly", "monthly", "single"]


def _label(v: str | None) -> str | None:
    if v is not None and not 1 <= len(v) <= 80:
        raise ValueError("debt.err.label")
    return v


Label = Annotated[str, AfterValidator(_label)]


class DebtCreate(InModel):
    lender_type: LenderType
    lender_label: Label
    original_principal: PositiveMoneyIn
    outstanding_balance: NonNegativeMoneyIn
    outstanding_as_of: date | None = None  # default: today
    installment_amount: PositiveMoneyIn | None = None
    installment_frequency: Frequency
    next_due_date: date | None = None
    is_overdue: bool = False
    overdue_amount: NonNegativeMoneyIn | None = None
    season_id: uuid.UUID | None = None
    interest_fee_note: OptText = None


class DebtPatch(InModel):
    lender_type: LenderType | None = None
    lender_label: Label | None = None
    original_principal: PositiveMoneyIn | None = None
    outstanding_balance: NonNegativeMoneyIn | None = None
    outstanding_as_of: date | None = None
    installment_amount: PositiveMoneyIn | None = None
    installment_frequency: Frequency | None = None
    next_due_date: date | None = None
    is_overdue: bool | None = None
    overdue_amount: NonNegativeMoneyIn | None = None
    season_id: uuid.UUID | None = None
    interest_fee_note: OptText = None
    status: Literal["active", "closed"] | None = None


class Installment(BaseModel):
    due_date: date
    amount: MoneyOut


class DebtOut(BaseModel):
    id: uuid.UUID
    lender_type: str
    lender_label: str
    original_principal: MoneyOut
    outstanding_balance: MoneyOut
    outstanding_as_of: date
    installment_amount: MoneyOut | None
    installment_frequency: str
    next_due_date: date | None
    is_overdue: bool
    overdue_amount: MoneyOut
    season_id: uuid.UUID | None
    interest_fee_note: str | None
    evidence_state: str
    status: str
    next_installments: list[Installment]
    dates_outdated: bool
    created_at: datetime


class DebtList(BaseModel):
    items: list[DebtOut]
    total: int
    no_debt_declared: bool


class DeclareNoneOut(BaseModel):
    no_debt_declared: bool
