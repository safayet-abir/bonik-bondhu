"""Ledger entries (FR-LED). P1 vertical slice: cash sales and operating
expenses only; P2-T01 enables all 12 types with supplier/debt/season links,
P2-T02 duplicate warnings, P2-T03 voiding."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import AppError, field_error
from ..models import BusinessProfile, Transaction, User
from ..schemas.ledger import TransactionCreate, TransactionOut
from .profile_service import bump_data_version

ENABLED_TYPES = frozenset({"sale_cash", "operating_expense"})  # P1-T07
LINK_FIELDS = ("supplier_id", "debt_facility_id", "season_id", "season_cost_item_id")


def create(db: Session, user: User, profile: BusinessProfile, data: TransactionCreate) -> tuple[Transaction, bool]:
    """Returns (transaction, created). Same client_request_id -> the existing
    row and created=False (idempotent, FR-LED-10)."""
    if data.client_request_id is not None:
        existing = db.scalar(select(Transaction).where(
            Transaction.profile_id == profile.id,
            Transaction.client_request_id == data.client_request_id,
        ))
        if existing is not None:
            return existing, False

    if data.txn_type not in ENABLED_TYPES:
        raise field_error("txn_type", "entry.err.type_unavailable")
    for name in LINK_FIELDS:
        if getattr(data, name) is not None:
            raise field_error(name, "entry.err.link_unavailable")
    if data.settlement_date is not None and data.settlement_date < data.value_date:
        raise field_error("settlement_date", "entry.err.settlement_date")

    txn = Transaction(
        profile_id=profile.id,
        txn_type=data.txn_type,
        amount=data.amount,
        value_date=data.value_date,
        settlement_date=data.settlement_date,
        category=data.category,
        note=data.note,
        client_request_id=data.client_request_id,
        created_by=user.id,
    )
    db.add(txn)
    db.flush()
    bump_data_version(profile)
    return txn, True


def get(db: Session, profile: BusinessProfile, tid: uuid.UUID) -> Transaction:
    txn = db.scalar(select(Transaction).where(Transaction.profile_id == profile.id, Transaction.id == tid))
    if txn is None:
        raise AppError("NOT_FOUND", 404, "err.not_found")
    return txn


def list_transactions(
    db: Session,
    profile: BusinessProfile,
    *,
    from_: date | None,
    to: date | None,
    txn_type: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Transaction], int]:
    conds = [Transaction.profile_id == profile.id]
    if from_ is not None:
        conds.append(Transaction.value_date >= from_)
    if to is not None:
        conds.append(Transaction.value_date <= to)
    if txn_type is not None:
        conds.append(Transaction.txn_type == txn_type)
    if status is not None:
        conds.append(Transaction.status == status)
    total = db.scalar(select(func.count()).select_from(Transaction).where(*conds)) or 0
    rows = db.scalars(
        select(Transaction).where(*conds)
        .order_by(Transaction.value_date.desc(), Transaction.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows), total


def txn_out(t: Transaction) -> TransactionOut:
    return TransactionOut(
        id=t.id, txn_type=t.txn_type, amount=t.amount, value_date=t.value_date,
        settlement_date=t.settlement_date, category=t.category, note=t.note, supplier=None,
        season_id=t.season_id, document_id=t.document_id, entry_method=t.entry_method,
        evidence_state=t.evidence_state, status=t.status, void_reason=t.void_reason,
        created_at=t.created_at,
    )
