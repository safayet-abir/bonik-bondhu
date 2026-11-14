from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    activity_type: Mapped[str]  # shop | crop_farm
    display_name: Mapped[str]
    business_category: Mapped[str | None]
    district: Mapped[str | None]
    upazila: Mapped[str | None]
    market_area: Mapped[str | None]
    household_withdrawal_monthly: Mapped[Decimal | None]
    household_declared_at: Mapped[datetime | None]
    no_debt_declared_at: Mapped[datetime | None]
    share_code: Mapped[str] = mapped_column(unique=True)
    data_version: Mapped[int] = mapped_column(BigInteger, default=1)
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()
    archived_at: Mapped[datetime | None]
