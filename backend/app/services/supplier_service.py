"""Suppliers (FR-SUP-01/02) and supplier concentration (FR-SUP-03..06, P4-T01)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.errors import not_found
from ..engine import concentration as conc
from ..engine.money import ZERO, money_str
from ..models import BusinessProfile, Supplier, Transaction
from ..schemas.supplier import ConcentrationOut, ConcentrationRow, SupplierCreate, SupplierOut, SupplierPatch
from .profile_service import bump_data_version

WINDOW_DAYS = 56  # 8 complete weeks, the same window as the forecast baseline
LINKED_TYPES = ("purchase_cash", "payable_payment")
MIN_LINKED = 2    # Architecture §5.5: fewer linked purchases -> owner-reported shares
SPARSE_LINKED = 4  # below this, a "low" dependency is not evidence of low risk (FR-SUP-06)


def list_suppliers(db: Session, profile: BusinessProfile, *, include_inactive: bool = True) -> list[Supplier]:
    q = select(Supplier).where(Supplier.profile_id == profile.id)
    if not include_inactive:
        q = q.where(Supplier.is_active.is_(True))
    return list(db.scalars(q.order_by(Supplier.created_at)))


def get(db: Session, profile: BusinessProfile, sid: uuid.UUID) -> Supplier:
    s = db.scalar(select(Supplier).where(Supplier.profile_id == profile.id, Supplier.id == sid))
    if s is None:
        raise not_found()
    return s


def create(db: Session, profile: BusinessProfile, data: SupplierCreate) -> Supplier:
    s = Supplier(profile_id=profile.id, **dict(data))
    db.add(s)
    db.flush()
    bump_data_version(profile)
    return s


def update(db: Session, profile: BusinessProfile, sid: uuid.UUID, patch: SupplierPatch) -> Supplier:
    s = get(db, profile, sid)
    for name in patch.model_fields_set:
        value = getattr(patch, name)
        if name in ("display_name", "is_active") and value is None:
            continue  # required columns cannot be cleared
        setattr(s, name, value)
    bump_data_version(profile)
    db.flush()
    return s


@dataclass
class SupplierConcentration:
    basis: str                     # linked_purchases | owner_reported | none
    window_start: date
    window_end: date
    linked_count: int
    result: conc.Concentration[uuid.UUID]
    amounts: dict[uuid.UUID, Decimal]
    suppliers: dict[uuid.UUID, Supplier]
    note_key: str | None

    @property
    def top_supplier(self) -> Supplier | None:
        return self.suppliers.get(self.result.top) if self.result.top else None

    def share_of(self, sid: uuid.UUID) -> Decimal | None:
        return self.result.shares.get(sid)


def concentration(db: Session, profile: BusinessProfile, as_of: date) -> SupplierConcentration:
    """Window = the 56 days before as_of. Linked purchase payments
    (purchase_cash + payable_payment with a supplier) decide the shares when
    there are at least two; otherwise the owner's declared shares are used
    and labelled owner-reported; otherwise there is no basis. Sparse data is
    never presented as low risk (FR-SUP-06)."""
    threshold = get_settings().HIGH_DEPENDENCY_SHARE
    start, end = as_of - timedelta(days=WINDOW_DAYS), as_of - timedelta(days=1)
    suppliers = {s.id: s for s in list_suppliers(db, profile)}
    rows = db.execute(
        select(Transaction.supplier_id, func.sum(Transaction.amount), func.count())
        .where(Transaction.profile_id == profile.id, Transaction.status == "confirmed",
               Transaction.txn_type.in_(LINKED_TYPES), Transaction.supplier_id.is_not(None),
               Transaction.value_date >= start, Transaction.value_date <= end)
        .group_by(Transaction.supplier_id)).all()
    amounts = {sid: total for sid, total, _ in rows}
    linked = sum(n for _, _, n in rows)
    if linked >= MIN_LINKED:
        basis, result = "linked_purchases", conc.from_amounts(amounts, threshold)
    else:
        declared = {s.id: s.declared_purchase_share_pct for s in suppliers.values()
                    if s.is_active and s.declared_purchase_share_pct}
        if declared:
            basis, result = "owner_reported", conc.from_declared(declared, threshold)
        else:
            basis, result = "none", conc.from_amounts({}, threshold)
    if not suppliers:
        note = "supplier.add_prompt"
    elif not result.high_dependency and (basis != "linked_purchases" or linked < SPARSE_LINKED):
        note = "supplier.sparse"
    else:
        note = None
    return SupplierConcentration(basis, start, end, linked, result, amounts if basis == "linked_purchases" else {},
                                 suppliers, note)


def concentration_out(c: SupplierConcentration) -> ConcentrationOut:
    threshold = get_settings().HIGH_DEPENDENCY_SHARE
    order = sorted(c.result.shares, key=lambda k: -c.result.shares[k])
    return ConcentrationOut(
        window_days=WINDOW_DAYS, window_start=c.window_start, window_end=c.window_end, basis=c.basis,
        linked_purchase_count=c.linked_count,
        total_purchases=c.result.total if c.basis == "linked_purchases" else None,
        suppliers=[ConcentrationRow(supplier_id=sid, display_name=c.suppliers[sid].display_name,
                                    amount=c.amounts.get(sid), share_pct=str(conc.pct(c.result.shares[sid])))
                   for sid in order if sid in c.suppliers],
        top_share_pct=str(conc.pct(c.result.top_share)) if c.result.top else None,
        high_dependency=c.result.high_dependency, threshold_pct=str(conc.pct(threshold)), note_key=c.note_key,
    )


def supplier_out(s: Supplier) -> SupplierOut:
    share = s.declared_purchase_share_pct
    return SupplierOut(
        id=s.id, display_name=s.display_name, goods_supplied=s.goods_supplied,
        district=s.district, upazila=s.upazila,
        declared_purchase_share_pct=money_str(share) if share is not None else None,
        is_active=s.is_active,
    )
