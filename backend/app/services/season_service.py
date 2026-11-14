"""Crop seasons, planned cost items, harvest and season summary
(FR-SEA-01..08; DEC-27: actual farm costs/sales are ledger entries linked
to the season). Only reachable through FarmProfile (P2-T11)."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..core.errors import AppError, field_error, not_found
from ..engine.crop import break_even_price, income_range
from ..engine.money import ZERO, money
from ..engine.units import BighaFactorRequired, acres_for_storage
from ..models import BusinessProfile, FarmingSeason, SeasonCostItem, Transaction
from ..schemas.season import (
    CostItemCreate, CostItemOut, CostItemPatch, HarvestIn, IncomeRangeOut, SeasonCreate, SeasonDetail,
    SeasonOut, SeasonPatch, SeasonSummaryOut,
)
from .profile_service import bump_data_version

PAID_TYPES = ("purchase_cash", "payable_payment", "operating_expense")  # cash actually paid out
SALE_TYPES = ("sale_cash", "sale_credit")
OUTPUT = ("expected_output_low", "expected_output_expected", "expected_output_high")
PRICE = ("expected_price_low", "expected_price_expected", "expected_price_high")
SEASON_EDITABLE = (
    "crop_name", "variety", "season_name", "season_label", "area_value", "area_unit", "decimals_per_bigha",
    "sowing_date", "expected_harvest_date", *OUTPUT, *PRICE, "status",
)
SEASON_REQUIRED = {"crop_name", "season_name", "area_value", "area_unit", "sowing_date",
                   "expected_harvest_date", "status"}


# --------------------------------------------------------------------------- seasons
def _validate_season(s: FarmingSeason) -> None:
    if s.area_unit != "bigha":
        s.decimals_per_bigha = None  # factor only means something for bigha
    try:
        s.area_acres = acres_for_storage(s.area_value, s.area_unit, s.decimals_per_bigha)
    except BighaFactorRequired:
        raise AppError("BIGHA_FACTOR_REQUIRED", 422, "season.err.bigha_factor",
                       fields={"decimals_per_bigha": "season.err.bigha_factor"}) from None
    if s.area_acres <= 0:
        raise field_error("area_value", "season.err.positive")
    if s.expected_harvest_date <= s.sowing_date:
        raise field_error("expected_harvest_date", "season.err.harvest_after_sowing")
    for names in (OUTPUT, PRICE):
        vals = [getattr(s, n) for n in names]
        present = [(n, v) for n, v in zip(names, vals, strict=True) if v is not None]
        for (_, a), (n, b) in zip(present, present[1:]):
            if a > b:
                raise field_error(n, "season.err.range_order")  # low ≤ expected ≤ high


def _owned_season(db: Session, profile: BusinessProfile, sid: uuid.UUID) -> FarmingSeason:
    s = db.scalar(select(FarmingSeason).where(FarmingSeason.profile_id == profile.id, FarmingSeason.id == sid))
    if s is None:
        raise not_found()
    return s


def list_seasons(db: Session, profile: BusinessProfile) -> list[FarmingSeason]:
    return list(db.scalars(select(FarmingSeason).where(FarmingSeason.profile_id == profile.id)
                           .order_by(FarmingSeason.sowing_date.desc(), FarmingSeason.created_at.desc())))


def get(db: Session, profile: BusinessProfile, sid: uuid.UUID) -> FarmingSeason:
    return _owned_season(db, profile, sid)


def create(db: Session, profile: BusinessProfile, data: SeasonCreate) -> FarmingSeason:
    s = FarmingSeason(profile_id=profile.id, status="planned", output_unit="kg", **dict(data))
    _validate_season(s)
    db.add(s)
    bump_data_version(profile)
    db.flush()
    return s


def update(db: Session, profile: BusinessProfile, sid: uuid.UUID, patch: SeasonPatch) -> FarmingSeason:
    s = _owned_season(db, profile, sid)
    for name in patch.model_fields_set & set(SEASON_EDITABLE):
        value = getattr(patch, name)
        if value is None and name in SEASON_REQUIRED:
            continue
        if name == "status" and s.status == "harvested":
            continue  # harvest is recorded through its own endpoint and stays recorded
        setattr(s, name, value)
    _validate_season(s)
    s.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    return s


def harvest(db: Session, profile: BusinessProfile, sid: uuid.UUID, data: HarvestIn) -> FarmingSeason:
    s = _owned_season(db, profile, sid)
    if data.actual_harvest_date < s.sowing_date:
        raise field_error("actual_harvest_date", "season.err.harvest_after_sowing")
    s.actual_harvest_date = data.actual_harvest_date
    s.actual_output = data.actual_output
    s.status = "harvested"
    s.updated_at = utcnow()
    bump_data_version(profile)
    db.flush()
    return s


def _income(s: FarmingSeason) -> IncomeRangeOut | None:
    out = tuple(getattr(s, n) for n in OUTPUT)
    price = tuple(getattr(s, n) for n in PRICE)
    if any(v is None for v in (*out, *price)):
        return None
    r = income_range(out, price)
    return IncomeRangeOut(low=r.low, expected=r.expected, high=r.high)


def _plain(d: Decimal | None) -> str | None:
    return None if d is None else format(d.normalize(), "f")


def season_out(s: FarmingSeason) -> SeasonOut:
    return SeasonOut(
        id=s.id, crop_name=s.crop_name, variety=s.variety, season_name=s.season_name,
        season_label=s.season_label, area_value=_plain(s.area_value), area_unit=s.area_unit,
        decimals_per_bigha=_plain(s.decimals_per_bigha), area_acres=f"{s.area_acres:.4f}",
        sowing_date=s.sowing_date, expected_harvest_date=s.expected_harvest_date, output_unit=s.output_unit,
        **{n: getattr(s, n) for n in (*OUTPUT, *PRICE)},
        status=s.status, actual_harvest_date=s.actual_harvest_date, actual_output=s.actual_output,
        income_range=_income(s), created_at=s.created_at,
    )


# --------------------------------------------------------------------------- cost items
def _owned_item(db: Session, profile: BusinessProfile, season: FarmingSeason, iid: uuid.UUID) -> SeasonCostItem:
    item = db.scalar(select(SeasonCostItem).where(
        SeasonCostItem.profile_id == profile.id, SeasonCostItem.season_id == season.id, SeasonCostItem.id == iid))
    if item is None:
        raise not_found()
    return item


def list_items(db: Session, profile: BusinessProfile, season: FarmingSeason) -> list[SeasonCostItem]:
    return list(db.scalars(select(SeasonCostItem).where(
        SeasonCostItem.profile_id == profile.id, SeasonCostItem.season_id == season.id)
        .order_by(SeasonCostItem.created_at)))


def add_item(db: Session, profile: BusinessProfile, sid: uuid.UUID, data: CostItemCreate) -> SeasonCostItem:
    season = _owned_season(db, profile, sid)
    item = SeasonCostItem(profile_id=profile.id, season_id=season.id, **dict(data))
    db.add(item)
    bump_data_version(profile)
    db.flush()
    db.refresh(item)  # read the GENERATED total_cost
    return item


def update_item(db: Session, profile: BusinessProfile, sid: uuid.UUID, iid: uuid.UUID,
                patch: CostItemPatch) -> SeasonCostItem:
    item = _owned_item(db, profile, _owned_season(db, profile, sid), iid)
    for name in patch.model_fields_set:
        value = getattr(patch, name)
        if value is None and name not in ("planned_date", "price_source_note"):
            continue
        setattr(item, name, value)
    bump_data_version(profile)
    db.flush()
    db.refresh(item)
    return item


def delete_item(db: Session, profile: BusinessProfile, sid: uuid.UUID, iid: uuid.UUID) -> None:
    item = _owned_item(db, profile, _owned_season(db, profile, sid), iid)
    used_by_entry = db.scalar(select(Transaction.id).where(
        Transaction.profile_id == profile.id, Transaction.season_cost_item_id == item.id).limit(1))
    used_by_request = db.execute(
        text("SELECT 1 FROM financing_request_items WHERE profile_id = :p AND source_season_cost_item_id = :i LIMIT 1"),
        {"p": profile.id, "i": item.id},
    ).first()
    if used_by_entry is not None or used_by_request is not None:
        raise AppError("CONFLICT", 409, "season.err.cost_item_in_use")
    db.delete(item)
    bump_data_version(profile)
    db.flush()


def _paid_by_item(db: Session, profile: BusinessProfile, items: Sequence[SeasonCostItem]) -> dict[uuid.UUID, Decimal]:
    ids = [i.id for i in items]
    if not ids:
        return {}
    return dict(db.execute(
        select(Transaction.season_cost_item_id, func.sum(Transaction.amount))
        .where(Transaction.profile_id == profile.id, Transaction.status == "confirmed",
               Transaction.txn_type.in_(PAID_TYPES), Transaction.season_cost_item_id.in_(ids))
        .group_by(Transaction.season_cost_item_id)
    ).all())


def item_out(i: SeasonCostItem, paid: dict[uuid.UUID, Decimal] | None = None) -> CostItemOut:
    return CostItemOut(
        id=i.id, season_id=i.season_id, category=i.category, item_name=i.item_name,
        quantity=format(i.quantity.normalize(), "f"), unit=i.unit, unit_cost=i.unit_cost,
        total_cost=i.total_cost, planned_date=i.planned_date, price_source_type=i.price_source_type,
        price_source_note=i.price_source_note, paid_total=(paid or {}).get(i.id, ZERO),
    )


def detail(db: Session, profile: BusinessProfile, sid: uuid.UUID) -> SeasonDetail:
    s = _owned_season(db, profile, sid)
    items = list_items(db, profile, s)
    paid = _paid_by_item(db, profile, items)
    return SeasonDetail(**season_out(s).model_dump(), cost_items=[item_out(i, paid) for i in items])


# --------------------------------------------------------------------------- summary
def summary(db: Session, profile: BusinessProfile, sid: uuid.UUID) -> SeasonSummaryOut:
    """FR-SEA-07 without loan-cover price (needs a financing request, P3)."""
    s = _owned_season(db, profile, sid)
    planned = sum((i.total_cost for i in list_items(db, profile, s)), ZERO)

    def total(types: Sequence[str]) -> Decimal:
        return db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.profile_id == profile.id, Transaction.season_id == s.id,
            Transaction.status == "confirmed", Transaction.txn_type.in_(types))) or ZERO

    break_even = None
    if planned > 0 and s.expected_output_expected:
        break_even = break_even_price(planned, s.expected_output_expected)
    return SeasonSummaryOut(
        season=season_out(s),
        planned_cost_total=money(planned),
        paid_cost_total=money(Decimal(total(PAID_TYPES))),
        actual_sales_total=money(Decimal(total(SALE_TYPES))),
        income_range=_income(s),
        break_even_price_per_kg=break_even,
        labels=["owner_estimates"],
    )
