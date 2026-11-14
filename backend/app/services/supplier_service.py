"""Suppliers (FR-SUP-01/02). Concentration (FR-SUP-03..06) arrives in P4."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import not_found
from ..engine.money import money_str
from ..models import BusinessProfile, Supplier
from ..schemas.supplier import SupplierCreate, SupplierOut, SupplierPatch
from .profile_service import bump_data_version


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


def supplier_out(s: Supplier) -> SupplierOut:
    share = s.declared_purchase_share_pct
    return SupplierOut(
        id=s.id, display_name=s.display_name, goods_supplied=s.goods_supplied,
        district=s.district, upazila=s.upazila,
        declared_purchase_share_pct=money_str(share) if share is not None else None,
        is_active=s.is_active,
    )
