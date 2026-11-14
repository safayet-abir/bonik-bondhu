from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class Transaction(Base):
    """The single ledger for shops and farms (DB doc §5.11). Never hard-deleted."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    txn_type: Mapped[str]
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(CHAR(3), default="BDT")
    value_date: Mapped[date]
    settlement_date: Mapped[date | None]
    category: Mapped[str | None]
    note: Mapped[str | None]
    supplier_id: Mapped[uuid.UUID | None]
    debt_facility_id: Mapped[uuid.UUID | None]
    season_id: Mapped[uuid.UUID | None]
    season_cost_item_id: Mapped[uuid.UUID | None]
    document_id: Mapped[uuid.UUID | None]
    entry_method: Mapped[str] = mapped_column(default="manual")
    evidence_state: Mapped[str] = mapped_column(default="declared")
    status: Mapped[str] = mapped_column(default="confirmed")
    duplicate_confirmed: Mapped[bool] = mapped_column(default=False)
    void_reason: Mapped[str | None]
    voided_at: Mapped[datetime | None]
    client_request_id: Mapped[uuid.UUID | None]
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at_col()
