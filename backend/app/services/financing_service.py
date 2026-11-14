"""Financing requests, purpose items and the live preview (FR-FIN-01..09;
API spec §4.10). Terms are the owner's proposal — never a lender offer."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.clock import today, utcnow
from ..core.errors import AppError, field_error, not_found
from ..engine.funding import funding_gap
from ..engine.money import ZERO, money
from ..engine.schedules import new_loan_schedule
from ..models import (
    BusinessProfile, FarmingSeason, FinancialAssessment, FinancingRequest, FinancingRequestItem, SeasonCostItem,
)
from ..schemas.financing import (
    AssessmentRef, FinancingCreate, FinancingOut, FinancingPatch, InstallmentOut, ItemCreate, ItemOut, ItemPatch,
    PreviewOut,
)
from .profile_service import bump_data_version

PATCHABLE = (
    "requested_amount", "purpose_text", "purpose_category", "desired_start_date", "season_id",
    "associated_expenses", "liquidity_buffer", "buffer_justification", "cash_safely_available",
    "committed_financing", "current_cash_balance", "minimum_cash_reserve", "schedule_type",
    "installment_count", "installment_frequency", "first_due_date", "interest_fees_total",
    "interest_fees_unknown", "over_request_explanation",
)
NOT_NULL = {"requested_amount", "purpose_text", "purpose_category", "interest_fees_unknown"}
GAP_INPUTS = ("associated_expenses", "liquidity_buffer", "cash_safely_available", "committed_financing")


# --------------------------------------------------------------------------- requests
def _check_season(db: Session, profile: BusinessProfile, season_id: uuid.UUID | None) -> None:
    if season_id is None:
        return
    if profile.activity_type != "crop_farm":
        raise field_error("season_id", "entry.err.season_farm_only")
    if db.scalar(select(FarmingSeason.id).where(FarmingSeason.profile_id == profile.id,
                                                FarmingSeason.id == season_id)) is None:
        raise not_found()


def list_requests(db: Session, profile: BusinessProfile) -> list[FinancingRequest]:
    return list(db.scalars(select(FinancingRequest).where(
        FinancingRequest.profile_id == profile.id, FinancingRequest.status == "draft")
        .order_by(FinancingRequest.created_at.desc())))


def get(db: Session, profile: BusinessProfile, rid: uuid.UUID) -> FinancingRequest:
    r = db.scalar(select(FinancingRequest).where(FinancingRequest.profile_id == profile.id,
                                                 FinancingRequest.id == rid))
    if r is None or r.status != "draft":
        raise not_found()
    return r


def create(db: Session, profile: BusinessProfile, data: FinancingCreate) -> FinancingRequest:
    _check_season(db, profile, data.season_id)
    r = FinancingRequest(profile_id=profile.id, status="draft", interest_fees_unknown=False, **dict(data))
    db.add(r)
    bump_data_version(profile)
    db.flush()
    db.refresh(r)
    return r


def update(db: Session, profile: BusinessProfile, rid: uuid.UUID, patch: FinancingPatch) -> FinancingRequest:
    r = get(db, profile, rid)
    sent = patch.model_fields_set & set(PATCHABLE)
    if "season_id" in sent:
        _check_season(db, profile, patch.season_id)
    if "first_due_date" in sent and patch.first_due_date is not None and patch.first_due_date < today():
        raise field_error("first_due_date", "fin.err.first_due_past")
    for name in sent:
        value = getattr(patch, name)
        if value is None and name in NOT_NULL:
            continue
        setattr(r, name, value)
    # "I don't know the interest/fees" and an amount exclude each other (FR-FIN-07).
    # An explicit "I don't know" in this request wins over an amount sent with it.
    if "interest_fees_unknown" in sent and patch.interest_fees_unknown:
        r.interest_fees_total = None
    elif "interest_fees_total" in sent and r.interest_fees_total is not None:
        r.interest_fees_unknown = False
    if r.interest_fees_unknown:
        r.interest_fees_total = None
    if r.schedule_type == "single_payment":
        r.installment_count = 1
        r.installment_frequency = None
    elif r.schedule_type == "equal_installments" and r.installment_frequency is None:
        raise field_error("installment_frequency", "fin.err.frequency_required")
    r.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    return r


# --------------------------------------------------------------------------- items
def list_items(db: Session, profile: BusinessProfile, r: FinancingRequest) -> list[FinancingRequestItem]:
    return list(db.scalars(select(FinancingRequestItem).where(
        FinancingRequestItem.profile_id == profile.id, FinancingRequestItem.financing_request_id == r.id)
        .order_by(FinancingRequestItem.created_at, FinancingRequestItem.id)))


def counted_items(items: list[FinancingRequestItem]) -> list[FinancingRequestItem]:
    """Only owner-confirmed items with a price count (FR-FIN-03)."""
    return [i for i in items if i.confirmed and i.line_total > 0]


def _owned_item(db: Session, profile: BusinessProfile, r: FinancingRequest, iid: uuid.UUID) -> FinancingRequestItem:
    item = db.scalar(select(FinancingRequestItem).where(
        FinancingRequestItem.profile_id == profile.id, FinancingRequestItem.financing_request_id == r.id,
        FinancingRequestItem.id == iid))
    if item is None:
        raise not_found()
    return item


def add_item(db: Session, profile: BusinessProfile, rid: uuid.UUID, data: ItemCreate) -> FinancingRequestItem:
    r = get(db, profile, rid)
    if data.copy_from_season_cost_item_id is not None:
        item = _copy_cost_item(db, profile, r, data.copy_from_season_cost_item_id)
    else:
        for name in ("item_name", "quantity", "unit", "unit_price"):
            if getattr(data, name) is None:
                raise field_error(name, "err.field.missing")
        item = FinancingRequestItem(
            profile_id=profile.id, financing_request_id=r.id, item_name=data.item_name, quantity=data.quantity,
            unit=data.unit, unit_price=data.unit_price, price_source_type=data.price_source_type or "owner_estimate",
            price_date=data.price_date, price_source_note=data.price_source_note, ai_proposed=False, confirmed=True,
        )
    if item.price_date is not None and item.price_date > today():
        raise field_error("price_date", "entry.err.future_date")
    db.add(item)
    r.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    db.refresh(item)
    return item


def _copy_cost_item(db: Session, profile: BusinessProfile, r: FinancingRequest,
                    cid: uuid.UUID) -> FinancingRequestItem:
    """FR-FIN-08: copy a planned season cost into the request (editable after)."""
    if r.season_id is None:
        raise field_error("copy_from_season_cost_item_id", "fin.err.no_season")
    ci = db.scalar(select(SeasonCostItem).where(SeasonCostItem.profile_id == profile.id,
                                                SeasonCostItem.season_id == r.season_id, SeasonCostItem.id == cid))
    if ci is None:
        raise not_found()
    dup = db.scalar(select(FinancingRequestItem.id).where(
        FinancingRequestItem.profile_id == profile.id, FinancingRequestItem.financing_request_id == r.id,
        FinancingRequestItem.source_season_cost_item_id == ci.id))
    if dup is not None:
        raise AppError("CONFLICT", 409, "fin.err.item_already_copied")
    return FinancingRequestItem(
        profile_id=profile.id, financing_request_id=r.id, item_name=ci.item_name[:120], quantity=ci.quantity,
        unit=ci.unit, unit_price=ci.unit_cost, price_source_type=ci.price_source_type,
        price_source_note=ci.price_source_note, ai_proposed=False, confirmed=True, source_season_cost_item_id=ci.id,
    )


def update_item(db: Session, profile: BusinessProfile, rid: uuid.UUID, iid: uuid.UUID,
                patch: ItemPatch) -> FinancingRequestItem:
    r = get(db, profile, rid)
    item = _owned_item(db, profile, r, iid)
    for name in patch.model_fields_set - {"confirmed"}:
        value = getattr(patch, name)
        if value is None and name not in ("price_date", "price_source_note"):
            continue
        setattr(item, name, value)
    if item.price_date is not None and item.price_date > today():
        raise field_error("price_date", "entry.err.future_date")
    if patch.confirmed:
        # An AI suggestion only counts after the owner supplies a price (AI never fills prices).
        if item.unit_price <= 0:
            raise field_error("unit_price", "fin.err.price_required")
        item.confirmed = True
    r.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    db.refresh(item)
    return item


def delete_item(db: Session, profile: BusinessProfile, rid: uuid.UUID, iid: uuid.UUID) -> None:
    r = get(db, profile, rid)
    db.delete(_owned_item(db, profile, r, iid))
    r.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()


# --------------------------------------------------------------------------- schedule + preview
def terms_complete(r: FinancingRequest, as_of: date) -> bool:
    if r.schedule_type is None or r.first_due_date is None or r.first_due_date < as_of:
        return False
    if r.schedule_type == "equal_installments" and (r.installment_count is None or r.installment_frequency is None):
        return False
    if r.minimum_cash_reserve is None:
        return False
    return r.interest_fees_total is not None or r.interest_fees_unknown


def new_schedule(r: FinancingRequest) -> list[tuple[date, Decimal]]:
    """Owner-proposed repayment rows; unknown interest/fees count as 0 (+ flag)."""
    if r.schedule_type is None or r.first_due_date is None:
        return []
    if r.schedule_type == "equal_installments" and (r.installment_count is None or r.installment_frequency is None):
        return []
    return new_loan_schedule(r.requested_amount, r.interest_fees_total or ZERO, r.schedule_type,
                             r.installment_count or 1, r.installment_frequency or "monthly", r.first_due_date)


def gap_inputs_complete(r: FinancingRequest) -> bool:
    return all(getattr(r, n) is not None for n in GAP_INPUTS)


def preview(r: FinancingRequest, items: list[FinancingRequestItem]) -> PreviewOut:
    g = funding_gap([(i.quantity, i.unit_price) for i in counted_items(items)],
                    *(getattr(r, n) or ZERO for n in GAP_INPUTS), r.requested_amount)
    rows = new_schedule(r)
    return PreviewOut(
        items_total=g.items_total, funding_gap=g.funding_gap, request_minus_gap=g.request_minus_gap,
        gap_inputs_complete=gap_inputs_complete(r),
        installments=[InstallmentOut(due_date=d, amount=a) for d, a in rows],
        repayment_total=money(sum((a for _, a in rows), ZERO)) if rows else None,
    )


def item_out(i: FinancingRequestItem) -> ItemOut:
    return ItemOut(
        id=i.id, item_name=i.item_name, quantity=format(i.quantity.normalize(), "f"), unit=i.unit,
        unit_price=None if (i.ai_proposed and not i.confirmed and i.unit_price == 0) else i.unit_price,
        line_total=i.line_total, price_source_type=i.price_source_type, price_date=i.price_date,
        price_source_note=i.price_source_note, ai_proposed=i.ai_proposed, confirmed=i.confirmed,
        source_season_cost_item_id=i.source_season_cost_item_id,
    )


def _latest_assessment(db: Session, profile: BusinessProfile, r: FinancingRequest) -> AssessmentRef | None:
    a = db.scalar(select(FinancialAssessment).where(
        FinancialAssessment.profile_id == profile.id, FinancialAssessment.financing_request_id == r.id)
        .order_by(FinancialAssessment.created_at.desc(), FinancialAssessment.id).limit(1))
    if a is None:
        return None
    return AssessmentRef(id=a.id, status=a.status, is_stale=a.profile_data_version != profile.data_version,
                         created_at=a.created_at)


def request_out(db: Session, profile: BusinessProfile, r: FinancingRequest) -> FinancingOut:
    items = list_items(db, profile, r)
    return FinancingOut(
        id=r.id, season_id=r.season_id, status=r.status, requested_amount=r.requested_amount,
        purpose_text=r.purpose_text, purpose_category=r.purpose_category, desired_start_date=r.desired_start_date,
        associated_expenses=r.associated_expenses, liquidity_buffer=r.liquidity_buffer,
        buffer_justification=r.buffer_justification, cash_safely_available=r.cash_safely_available,
        committed_financing=r.committed_financing, current_cash_balance=r.current_cash_balance,
        minimum_cash_reserve=r.minimum_cash_reserve, schedule_type=r.schedule_type,
        installment_count=r.installment_count, installment_frequency=r.installment_frequency,
        first_due_date=r.first_due_date, interest_fees_total=r.interest_fees_total,
        interest_fees_unknown=r.interest_fees_unknown, over_request_explanation=r.over_request_explanation,
        items=[item_out(i) for i in items], preview=preview(r, items),
        latest_assessment=_latest_assessment(db, profile, r), created_at=r.created_at, updated_at=r.updated_at,
    )
