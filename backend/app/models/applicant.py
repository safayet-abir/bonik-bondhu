from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class ApplicantDetails(Base):
    """Owner-declared information. No AI access; only explicit consent can share it."""

    __tablename__ = "applicant_details"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id", ondelete="CASCADE"), unique=True)
    full_legal_name: Mapped[str | None]
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    nid_number: Mapped[str | None]
    address: Mapped[str | None]
    nominee_name: Mapped[str | None]
    nominee_relation: Mapped[str | None]
    trade_licence: Mapped[str | None]
    years_in_business: Mapped[int | None]
    declared_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()
