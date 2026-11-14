from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Computed, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class FinancingRequest(Base):
    """Owner's financing need + proposed terms (DB doc §5.9; F7, DEC-11/28).
    Terms are the OWNER's proposal, never a lender offer."""

    __tablename__ = "financing_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    season_id: Mapped[uuid.UUID | None]
    status: Mapped[str] = mapped_column(default="draft")
    requested_amount: Mapped[Decimal]
    purpose_text: Mapped[str]
    purpose_category: Mapped[str]
    desired_start_date: Mapped[date | None]
    associated_expenses: Mapped[Decimal | None]
    liquidity_buffer: Mapped[Decimal | None]
    buffer_justification: Mapped[str | None]
    cash_safely_available: Mapped[Decimal | None]
    committed_financing: Mapped[Decimal | None]
    current_cash_balance: Mapped[Decimal | None]
    minimum_cash_reserve: Mapped[Decimal | None]
    schedule_type: Mapped[str | None]
    installment_count: Mapped[int | None]
    installment_frequency: Mapped[str | None]
    first_due_date: Mapped[date | None]
    interest_fees_total: Mapped[Decimal | None]
    interest_fees_unknown: Mapped[bool] = mapped_column(default=False)
    over_request_explanation: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = created_at_col()


class FinancingRequestItem(Base):
    """Purpose item. `line_total` is GENERATED in the DB — never written.
    Only `confirmed` rows count (AI proposals start unconfirmed, FR-FIN-03)."""

    __tablename__ = "financing_request_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID]
    financing_request_id: Mapped[uuid.UUID]
    item_name: Mapped[str]
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit: Mapped[str]
    unit_price: Mapped[Decimal]
    line_total: Mapped[Decimal] = mapped_column(Computed("round(quantity * unit_price, 2)", persisted=True))
    price_source_type: Mapped[str]
    price_date: Mapped[date | None]
    price_source_note: Mapped[str | None]
    ai_proposed: Mapped[bool] = mapped_column(default=False)
    confirmed: Mapped[bool] = mapped_column(default=True)
    source_season_cost_item_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created_at_col()


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    as_of_date: Mapped[date]
    method_version: Mapped[str]
    status: Mapped[str]
    window_weeks: Mapped[int]
    weeks_with_records: Mapped[int]
    min_weeks_required: Mapped[int]
    net_weekly_expected: Mapped[Decimal | None]
    net_weekly_low: Mapped[Decimal | None]
    net_weekly_high: Mapped[Decimal | None]
    collections_weekly_expected: Mapped[Decimal | None]
    payments_weekly_expected: Mapped[Decimal | None]
    purchases_weekly_expected: Mapped[Decimal | None]
    horizons: Mapped[dict] = mapped_column(JSONB, default=dict)
    assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    profile_data_version: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_col()


class FinancialAssessment(Base):
    __tablename__ = "financial_assessments"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID]
    financing_request_id: Mapped[uuid.UUID]
    forecast_run_id: Mapped[uuid.UUID | None]
    as_of_date: Mapped[date]
    engine_version: Mapped[str]
    status: Mapped[str]
    purpose_items_total: Mapped[Decimal | None]
    funding_gap: Mapped[Decimal | None]
    request_minus_gap: Mapped[Decimal | None]
    missing_items: Mapped[list] = mapped_column(JSONB, default=list)
    flags: Mapped[list] = mapped_column(JSONB, default=list)
    base_result: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[dict] = mapped_column(JSONB, default=dict)
    inputs_sha256: Mapped[str]
    profile_data_version: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_col()


class RiskScenario(Base):
    """What-if results attached to an assessment (P4 fills them; DEC-30:
    they never change the assessment status)."""

    __tablename__ = "risk_scenarios"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID]
    assessment_id: Mapped[uuid.UUID]
    scenario_type: Mapped[str]
    origin: Mapped[str]
    news_event_id: Mapped[uuid.UUID | None]
    supplier_id: Mapped[uuid.UUID | None]
    parameters: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str]
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()
    resolved_at: Mapped[datetime | None]
