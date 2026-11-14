from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Computed, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk

Area = Numeric(12, 4)


class FarmingSeason(Base):
    """One crop season on a crop_farm profile (DB doc §5.5; DEC-05)."""

    __tablename__ = "farming_seasons"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    crop_name: Mapped[str]
    variety: Mapped[str | None]
    season_name: Mapped[str]
    season_label: Mapped[str | None]
    area_value: Mapped[Decimal] = mapped_column(Area)
    area_unit: Mapped[str]
    decimals_per_bigha: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    area_acres: Mapped[Decimal] = mapped_column(Area)
    sowing_date: Mapped[date]
    expected_harvest_date: Mapped[date]
    output_unit: Mapped[str] = mapped_column(default="kg")
    expected_output_low: Mapped[Decimal | None]
    expected_output_expected: Mapped[Decimal | None]
    expected_output_high: Mapped[Decimal | None]
    expected_price_low: Mapped[Decimal | None]
    expected_price_expected: Mapped[Decimal | None]
    expected_price_high: Mapped[Decimal | None]
    status: Mapped[str] = mapped_column(default="planned")
    actual_harvest_date: Mapped[date | None]
    actual_output: Mapped[Decimal | None]
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class SeasonCostItem(Base):
    """Planned season cost. `total_cost` is GENERATED in the DB — never written."""

    __tablename__ = "season_cost_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID]
    season_id: Mapped[uuid.UUID]
    category: Mapped[str]
    item_name: Mapped[str]
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit: Mapped[str]
    unit_cost: Mapped[Decimal]
    total_cost: Mapped[Decimal] = mapped_column(Computed("round(quantity * unit_cost, 2)", persisted=True))
    planned_date: Mapped[date | None]
    price_source_type: Mapped[str] = mapped_column(default="owner_estimate")
    price_source_note: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_col()
