from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class DebtFacility(Base):
    """Obligations declared by the owner (DB doc §5.7). Labelled "declared
    by owner"; official credit checks happen at the lender (FR-DEBT-04)."""

    __tablename__ = "debt_facilities"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    season_id: Mapped[uuid.UUID | None]
    lender_type: Mapped[str]
    lender_label: Mapped[str]
    original_principal: Mapped[Decimal]
    outstanding_balance: Mapped[Decimal]
    outstanding_as_of: Mapped[date]
    installment_amount: Mapped[Decimal | None]
    installment_frequency: Mapped[str]  # weekly | monthly | single
    next_due_date: Mapped[date | None]
    is_overdue: Mapped[bool] = mapped_column(default=False)
    overdue_amount: Mapped[Decimal] = mapped_column(default=Decimal(0))
    interest_fee_note: Mapped[str | None]
    evidence_state: Mapped[str] = mapped_column(default="declared")
    document_id: Mapped[uuid.UUID | None]
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()
