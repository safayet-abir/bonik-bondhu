"""Declared obligations (FR-DEBT-01..04). Everything here is "declared by
owner"; official credit checks are done by the lender outside Bonik Bondhu."""
from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.clock import today, utcnow
from ..core.errors import AppError, field_error, not_found
from ..engine.schedules import dates_outdated, existing_debt_schedule, horizon_end
from ..models import BusinessProfile, DebtFacility, FarmingSeason
from ..schemas.debt import DebtCreate, DebtOut, DebtPatch, Installment
from .profile_service import bump_data_version

EDITABLE = (
    "lender_type", "lender_label", "original_principal", "outstanding_balance", "outstanding_as_of",
    "installment_amount", "installment_frequency", "next_due_date", "is_overdue", "overdue_amount",
    "season_id", "interest_fee_note", "status",
)
REQUIRED = {"lender_type", "lender_label", "original_principal", "outstanding_balance",
            "outstanding_as_of", "installment_frequency", "is_overdue", "status"}


def _validate(db: Session, profile: BusinessProfile, d: DebtFacility) -> None:
    """Rules on the merged row (create and PATCH), mirroring schema CHECKs
    with field-level keys."""
    if d.installment_frequency != "single" and d.installment_amount is None:
        raise field_error("installment_amount", "debt.err.installment_required")
    if d.status == "active" and d.outstanding_balance > 0 and d.next_due_date is None:
        raise field_error("next_due_date", "debt.err.next_due_required")
    if d.outstanding_as_of > today() + timedelta(days=1):
        raise field_error("outstanding_as_of", "entry.err.future_date")
    if not d.is_overdue:
        d.overdue_amount = Decimal(0)
    elif d.overdue_amount > d.outstanding_balance:
        raise field_error("overdue_amount", "debt.err.overdue_amount")
    if d.season_id is not None:
        if profile.activity_type != "crop_farm":
            raise field_error("season_id", "entry.err.season_farm_only")
        if db.scalar(select(FarmingSeason.id).where(
                FarmingSeason.profile_id == profile.id, FarmingSeason.id == d.season_id)) is None:
            raise not_found()


def active_count(db: Session, profile: BusinessProfile) -> int:
    return db.scalar(select(func.count()).select_from(DebtFacility).where(
        DebtFacility.profile_id == profile.id, DebtFacility.status == "active")) or 0


def list_debts(db: Session, profile: BusinessProfile) -> list[DebtFacility]:
    return list(db.scalars(
        select(DebtFacility).where(DebtFacility.profile_id == profile.id)
        .order_by(DebtFacility.status, DebtFacility.created_at)
    ))


def get(db: Session, profile: BusinessProfile, did: uuid.UUID) -> DebtFacility:
    d = db.scalar(select(DebtFacility).where(DebtFacility.profile_id == profile.id, DebtFacility.id == did))
    if d is None:
        raise not_found()
    return d


def create(db: Session, profile: BusinessProfile, data: DebtCreate) -> DebtFacility:
    values = dict(data)  # raw Decimals (model_dump would serialise money to strings)
    values["outstanding_as_of"] = values["outstanding_as_of"] or today()
    values["overdue_amount"] = values["overdue_amount"] or Decimal(0)
    if values["installment_frequency"] == "single":
        values["installment_amount"] = None  # whole outstanding once
    d = DebtFacility(profile_id=profile.id, status="active", **values)
    _validate(db, profile, d)
    db.add(d)
    # A declared debt replaces an earlier "I have no current loans" (FR-DEBT-02).
    profile.no_debt_declared_at = None
    bump_data_version(profile)
    db.flush()
    return d


def update(db: Session, profile: BusinessProfile, did: uuid.UUID, patch: DebtPatch) -> DebtFacility:
    d = get(db, profile, did)
    for name in patch.model_fields_set & set(EDITABLE):
        value = getattr(patch, name)
        if value is None and name in REQUIRED:
            continue
        if name == "overdue_amount" and value is None:
            value = Decimal(0)
        setattr(d, name, value)
    if d.installment_frequency == "single":
        d.installment_amount = None
    _validate(db, profile, d)
    d.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    return d


def declare_none(db: Session, profile: BusinessProfile) -> None:
    if active_count(db, profile) > 0:
        raise AppError("CONFLICT", 409, "debt.err.active_exists")
    profile.no_debt_declared_at = utcnow()
    bump_data_version(profile)


def schedule(d: DebtFacility, as_of=None):
    """Dated installments inside the 90-day horizon (FR-DEBT-03)."""
    as_of = as_of or today()
    if d.status != "active":
        return []
    return existing_debt_schedule(d.installment_amount, d.outstanding_balance, d.installment_frequency,
                                  d.next_due_date, horizon_end(as_of), as_of)


def debt_out(d: DebtFacility) -> DebtOut:
    as_of = today()
    return DebtOut(
        id=d.id, lender_type=d.lender_type, lender_label=d.lender_label,
        original_principal=d.original_principal, outstanding_balance=d.outstanding_balance,
        outstanding_as_of=d.outstanding_as_of, installment_amount=d.installment_amount,
        installment_frequency=d.installment_frequency, next_due_date=d.next_due_date,
        is_overdue=d.is_overdue, overdue_amount=d.overdue_amount, season_id=d.season_id,
        interest_fee_note=d.interest_fee_note, evidence_state=d.evidence_state, status=d.status,
        next_installments=[Installment(due_date=dt, amount=a) for dt, a in schedule(d, as_of)[:3]],
        dates_outdated=d.status == "active" and d.outstanding_balance > 0 and dates_outdated(d.next_due_date, as_of),
        created_at=d.created_at,
    )
