from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core.clock import today
from .common import InModel, MoneyOut, PositiveMoneyIn

TxnType = Literal[
    "sale_cash", "sale_credit", "receivable_collection",
    "purchase_cash", "purchase_credit", "payable_payment", "operating_expense",
    "loan_received", "loan_principal_repayment", "loan_interest_fee_payment",
    "owner_withdrawal", "owner_contribution",
]


class TransactionCreate(InModel):
    txn_type: TxnType
    amount: PositiveMoneyIn
    value_date: date
    settlement_date: date | None = None
    category: str | None = Field(default=None, max_length=50)
    note: str | None = None
    supplier_id: uuid.UUID | None = None
    debt_facility_id: uuid.UUID | None = None
    season_id: uuid.UUID | None = None
    season_cost_item_id: uuid.UUID | None = None
    client_request_id: uuid.UUID | None = None
    confirm_duplicate: bool = False
    # An uploaded photo of this profile kept as evidence when entering by hand (FR-EXT-04 manual path)
    document_id: uuid.UUID | None = None

    @field_validator("value_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > today() + timedelta(days=1):  # FR-LED-04
            raise ValueError("entry.err.future_date")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 300:
            raise ValueError("entry.err.note_length")
        return v or None


class VoidIn(InModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        if not 3 <= len(v) <= 200:  # FR-LED-06
            raise ValueError("entry.err.void_reason")
        return v


class SupplierRef(BaseModel):
    id: uuid.UUID
    display_name: str


class TransactionOut(BaseModel):
    id: uuid.UUID
    txn_type: str
    amount: MoneyOut
    value_date: date
    settlement_date: date | None
    category: str | None
    note: str | None
    supplier: SupplierRef | None = None
    debt_facility_id: uuid.UUID | None = None
    season_id: uuid.UUID | None
    season_cost_item_id: uuid.UUID | None = None
    document_id: uuid.UUID | None
    entry_method: str
    evidence_state: str
    status: str
    duplicate_confirmed: bool = False
    void_reason: str | None
    voided_at: datetime | None = None
    created_at: datetime


class TransactionList(BaseModel):
    items: list[TransactionOut]
    total: int


class EvidenceMix(BaseModel):
    declared_pct: str
    document_attached_pct: str


class RecordCoverage(BaseModel):
    weeks_with_records: int
    window_weeks: int


class SummaryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: date = Field(serialization_alias="from")
    to: date
    has_data: bool
    sales_recorded: MoneyOut
    cash_sales: MoneyOut
    credit_sales: MoneyOut
    operating_cash_in: MoneyOut
    operating_cash_out: MoneyOut
    net_operating_cash: MoneyOut
    receivables_outstanding: MoneyOut
    payables_outstanding: MoneyOut
    financing_received: MoneyOut
    principal_repaid: MoneyOut
    interest_fees_paid: MoneyOut
    owner_withdrawals: MoneyOut
    owner_contributions: MoneyOut
    cash_net_change: MoneyOut
    evidence_mix: EvidenceMix
    record_coverage: RecordCoverage
