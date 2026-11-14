from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class Supplier(Base):
    """L2 Stage 1 suppliers (DB doc §5.4). Names never leave the owner's
    view: lenders see "Supplier 1/2/3", the LLM never sees them."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    display_name: Mapped[str]
    goods_supplied: Mapped[str | None]
    district: Mapped[str | None]
    upazila: Mapped[str | None]
    declared_purchase_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at_col()
