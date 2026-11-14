"""/profiles/{pid}/debts (API spec §4.7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from ..core.deps import OwnedProfile
from ..db import DbSession
from ..schemas.debt import DebtCreate, DebtList, DebtOut, DebtPatch, DeclareNoneOut
from ..services import debt_service

router = APIRouter(prefix="/profiles/{pid}/debts", tags=["debts"])


@router.get("", response_model=DebtList)
def list_debts(profile: OwnedProfile, db: DbSession) -> DebtList:
    rows = debt_service.list_debts(db, profile)
    return DebtList(items=[debt_service.debt_out(d) for d in rows], total=len(rows),
                    no_debt_declared=profile.no_debt_declared_at is not None)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DebtOut)
def create_debt(data: DebtCreate, profile: OwnedProfile, db: DbSession) -> DebtOut:
    return debt_service.debt_out(debt_service.create(db, profile, data))


@router.post("/declare-none", response_model=DeclareNoneOut)
def declare_none(profile: OwnedProfile, db: DbSession) -> DeclareNoneOut:
    debt_service.declare_none(db, profile)
    return DeclareNoneOut(no_debt_declared=True)


@router.patch("/{did}", response_model=DebtOut)
def update_debt(did: uuid.UUID, patch: DebtPatch, profile: OwnedProfile, db: DbSession) -> DebtOut:
    return debt_service.debt_out(debt_service.update(db, profile, did, patch))
