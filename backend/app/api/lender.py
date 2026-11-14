"""/lender/* (API spec §4.15; endpoints #55–58). Lender officers only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, status

from ..core.deps import Lender
from ..db import DbSession
from ..services import lender_service
from ..services.lender_service import AccessRequestIn, CaseFilter, CaseList, EventIn

router = APIRouter(prefix="/lender", tags=["lender"])


@router.post("/access-requests", status_code=status.HTTP_202_ACCEPTED)
def access_request(data: AccessRequestIn, lender: Lender, db: DbSession, request: Request) -> dict:
    """Always the same 202 body, valid code or not (FR-CON-01, SEC-13)."""
    return lender_service.access_request(db, lender, data, request)


@router.get("/cases", response_model=CaseList)
def cases(lender: Lender, db: DbSession, status: CaseFilter | None = None) -> CaseList:
    return lender_service.list_cases(db, lender, status)


@router.get("/cases/{cid}")
def case_file(cid: uuid.UUID, lender: Lender, db: DbSession, request: Request) -> dict:
    return lender_service.case_file(db, lender, cid, request)


@router.post("/cases/{cid}/events", status_code=status.HTTP_201_CREATED)
def add_event(cid: uuid.UUID, data: EventIn, lender: Lender, db: DbSession, request: Request) -> dict:
    return lender_service.add_event(db, lender, cid, data, request)
