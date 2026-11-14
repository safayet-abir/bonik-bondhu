"""/lender/* (API spec §4.15). P1: case list only (P1-T10 role routing);
access requests, case files and review events arrive in P5."""
from __future__ import annotations

from fastapi import APIRouter

from ..core.deps import Lender
from ..db import DbSession
from ..services.lender_service import CaseFilter, CaseList, list_cases

router = APIRouter(prefix="/lender", tags=["lender"])


@router.get("/cases", response_model=CaseList)
def cases(lender: Lender, db: DbSession, status: CaseFilter | None = None) -> CaseList:
    return list_cases(db, lender, status)
