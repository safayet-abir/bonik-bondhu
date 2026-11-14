"""/profiles/{pid}/transactions and /summary (API spec §4.4)."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status

from ..core.deps import OwnedProfile, OwnerUser
from ..db import DbSession
from ..schemas.ledger import SummaryOut, TransactionCreate, TransactionList, TransactionOut, TxnType, VoidIn
from ..services import ledger_service, summary_service

router = APIRouter(prefix="/profiles/{pid}", tags=["ledger"])


@router.get("/transactions", response_model=TransactionList)
def list_transactions(
    profile: OwnedProfile,
    db: DbSession,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    # Repeatable: ?txn_type=sale_cash&txn_type=sale_credit (entry-list filter chips)
    txn_type: Annotated[list[TxnType] | None, Query()] = None,
    status_: Annotated[Literal["confirmed", "voided"] | None, Query(alias="status")] = None,
    season_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionList:
    rows, total = ledger_service.list_transactions(
        db, profile, from_=from_, to=to, txn_type=txn_type, status=status_,
        season_id=season_id, supplier_id=supplier_id, limit=limit, offset=offset)
    return TransactionList(items=ledger_service.outs(db, profile, rows), total=total)


@router.post("/transactions", status_code=status.HTTP_201_CREATED, response_model=TransactionOut)
def create_transaction(
    data: TransactionCreate, profile: OwnedProfile, user: OwnerUser, db: DbSession, response: Response
) -> TransactionOut:
    txn, created = ledger_service.create(db, user, profile, data)
    if not created:
        response.status_code = status.HTTP_200_OK  # idempotent replay (FR-LED-10)
    return ledger_service.outs(db, profile, [txn])[0]


@router.get("/transactions/{tid}", response_model=TransactionOut)
def get_transaction(tid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> TransactionOut:
    return ledger_service.outs(db, profile, [ledger_service.get(db, profile, tid)])[0]


@router.post("/transactions/{tid}/void", response_model=TransactionOut)
def void_transaction(tid: uuid.UUID, body: VoidIn, profile: OwnedProfile, db: DbSession) -> TransactionOut:
    return ledger_service.outs(db, profile, [ledger_service.void(db, profile, tid, body.reason)])[0]


@router.get("/summary", response_model=SummaryOut, response_model_by_alias=True)
def get_summary(
    profile: OwnedProfile,
    db: DbSession,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
) -> SummaryOut:
    return summary_service.summary(db, profile, from_, to)
