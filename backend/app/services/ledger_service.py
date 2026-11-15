"""Ledger entries (FR-LED-01..07, 10): all 12 types, link rules, duplicate
warning (SUG-28), idempotency and voiding. Entries are never hard-deleted."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..core.errors import AppError, field_error, not_found
from ..engine.accounting import LOAN_LINK_TYPES, SUPPLIER_LINK_TYPES
from ..engine.money import money_str
from ..models import (
    BusinessProfile, DebtFacility, Document, FarmingSeason, SeasonCostItem, Supplier, Transaction, User,
)
from ..schemas.ledger import SupplierRef, TransactionCreate, TransactionOut
from . import document_service
from .profile_service import bump_data_version

# A planned season cost can only be paid by a money-out business entry.
COST_ITEM_LINK_TYPES = frozenset({"purchase_cash", "purchase_credit", "payable_payment", "operating_expense"})


def _owned(db: Session, model, profile: BusinessProfile, oid: uuid.UUID):
    """Child lookups are always scoped by profile: not owned == not found."""
    row = db.scalar(select(model).where(model.profile_id == profile.id, model.id == oid))
    if row is None:
        raise not_found()
    return row


def _check_links(db: Session, profile: BusinessProfile, data: TransactionCreate) -> uuid.UUID | None:
    """Validates links; returns the season id to store (a cost item implies
    its season). Type/link mismatch -> 422; foreign/missing link -> 404."""
    if data.supplier_id is not None:
        if data.txn_type not in SUPPLIER_LINK_TYPES:
            raise field_error("supplier_id", "entry.err.supplier_link_type")
        _owned(db, Supplier, profile, data.supplier_id)
    if data.debt_facility_id is not None:
        if data.txn_type not in LOAN_LINK_TYPES:
            raise field_error("debt_facility_id", "entry.err.debt_link_type")
        _owned(db, DebtFacility, profile, data.debt_facility_id)

    season_id = data.season_id
    if data.season_id is not None or data.season_cost_item_id is not None:
        if profile.activity_type != "crop_farm":
            field = "season_id" if data.season_id is not None else "season_cost_item_id"
            raise field_error(field, "entry.err.season_farm_only")
    if data.season_id is not None:
        _owned(db, FarmingSeason, profile, data.season_id)
    if data.season_cost_item_id is not None:
        if data.txn_type not in COST_ITEM_LINK_TYPES:
            raise field_error("season_cost_item_id", "entry.err.cost_item_link_type")
        item = _owned(db, SeasonCostItem, profile, data.season_cost_item_id)
        if season_id is not None and item.season_id != season_id:
            raise field_error("season_cost_item_id", "entry.err.cost_item_season")
        season_id = item.season_id
    return season_id


def _find_duplicate(db: Session, profile: BusinessProfile, data: TransactionCreate) -> Transaction | None:
    """SUG-28: same profile + type + amount + value_date (+ supplier if set)
    as an existing confirmed entry."""
    conds = [
        Transaction.profile_id == profile.id,
        Transaction.status == "confirmed",
        Transaction.txn_type == data.txn_type,
        Transaction.amount == data.amount,
        Transaction.value_date == data.value_date,
    ]
    if data.supplier_id is not None:
        conds.append(Transaction.supplier_id == data.supplier_id)
    return db.scalar(select(Transaction).where(*conds).order_by(Transaction.created_at).limit(1))


def create(db: Session, user: User, profile: BusinessProfile, data: TransactionCreate, *,
           entry_method: str = "manual", document_id: uuid.UUID | None = None) -> tuple[Transaction, bool]:
    """Returns (transaction, created). Same client_request_id -> the existing
    row and created=False (idempotent, FR-LED-10)."""
    if data.client_request_id is not None:
        existing = db.scalar(select(Transaction).where(
            Transaction.profile_id == profile.id,
            Transaction.client_request_id == data.client_request_id,
        ))
        if existing is not None:
            return existing, False

    if data.settlement_date is not None and data.settlement_date < data.value_date:
        raise field_error("settlement_date", "entry.err.settlement_date")
    season_id = _check_links(db, profile, data)
    if document_id is None and data.document_id is not None:
        document_id = _owned(db, Document, profile, data.document_id).id  # another profile's photo -> 404

    duplicate = _find_duplicate(db, profile, data)
    if duplicate is not None and not data.confirm_duplicate:
        raise AppError("POSSIBLE_DUPLICATE", 409, "entry.duplicate_warning", extra={"existing": {
            "id": str(duplicate.id),
            "txn_type": duplicate.txn_type,
            "amount": money_str(duplicate.amount),
            "value_date": duplicate.value_date.isoformat(),
        }})

    txn = Transaction(
        profile_id=profile.id,
        txn_type=data.txn_type,
        amount=data.amount,
        value_date=data.value_date,
        settlement_date=data.settlement_date,
        category=data.category,
        note=data.note,
        supplier_id=data.supplier_id,
        debt_facility_id=data.debt_facility_id,
        season_id=season_id,
        season_cost_item_id=data.season_cost_item_id,
        document_id=document_id,
        entry_method=entry_method,
        evidence_state="document_attached" if document_id is not None else "declared",
        duplicate_confirmed=duplicate is not None,
        client_request_id=data.client_request_id,
        created_by=user.id,
    )
    db.add(txn)
    db.flush()
    bump_data_version(profile)
    if document_id is not None:
        # shortcut: the file is deleted before the commit; if the commit then failed the owner re-uploads
        document_service.drop_file(db, profile, document_id)
    return txn, True


def get(db: Session, profile: BusinessProfile, tid: uuid.UUID) -> Transaction:
    return _owned(db, Transaction, profile, tid)


def void(db: Session, profile: BusinessProfile, tid: uuid.UUID, reason: str) -> Transaction:
    """FR-LED-06: voided rows stay visible but are excluded from every calculation."""
    txn = get(db, profile, tid)
    if txn.status == "voided":
        raise AppError("CONFLICT", 409, "entry.err.already_voided")
    txn.status = "voided"
    txn.voided_at = utcnow()
    txn.void_reason = reason
    bump_data_version(profile)
    db.flush()
    return txn


def list_transactions(
    db: Session,
    profile: BusinessProfile,
    *,
    from_: date | None,
    to: date | None,
    txn_type: Sequence[str] | None,
    status: str | None,
    season_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Transaction], int]:
    conds = [Transaction.profile_id == profile.id]
    if from_ is not None:
        conds.append(Transaction.value_date >= from_)
    if to is not None:
        conds.append(Transaction.value_date <= to)
    if txn_type:
        conds.append(Transaction.txn_type.in_(list(txn_type)))
    if status is not None:
        conds.append(Transaction.status == status)
    if season_id is not None:
        conds.append(Transaction.season_id == season_id)
    if supplier_id is not None:
        conds.append(Transaction.supplier_id == supplier_id)
    total = db.scalar(select(func.count()).select_from(Transaction).where(*conds)) or 0
    rows = db.scalars(
        select(Transaction).where(*conds)
        .order_by(Transaction.value_date.desc(), Transaction.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows), total


def _supplier_names(db: Session, profile: BusinessProfile, rows: Sequence[Transaction]) -> dict[uuid.UUID, str]:
    ids = {t.supplier_id for t in rows if t.supplier_id is not None}
    if not ids:
        return {}
    return dict(db.execute(
        select(Supplier.id, Supplier.display_name).where(Supplier.profile_id == profile.id, Supplier.id.in_(ids))
    ).all())


def txn_out(t: Transaction, names: dict[uuid.UUID, str] | None = None) -> TransactionOut:
    supplier = None
    if t.supplier_id is not None:
        supplier = SupplierRef(id=t.supplier_id, display_name=(names or {}).get(t.supplier_id, ""))
    return TransactionOut(
        id=t.id, txn_type=t.txn_type, amount=t.amount, value_date=t.value_date,
        settlement_date=t.settlement_date, category=t.category, note=t.note, supplier=supplier,
        debt_facility_id=t.debt_facility_id, season_id=t.season_id,
        season_cost_item_id=t.season_cost_item_id, document_id=t.document_id,
        entry_method=t.entry_method, evidence_state=t.evidence_state, status=t.status,
        duplicate_confirmed=t.duplicate_confirmed, void_reason=t.void_reason, voided_at=t.voided_at,
        created_at=t.created_at,
    )


def outs(db: Session, profile: BusinessProfile, rows: Sequence[Transaction]) -> list[TransactionOut]:
    names = _supplier_names(db, profile, rows)
    return [txn_out(t, names) for t in rows]
