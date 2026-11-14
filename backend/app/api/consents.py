"""/profiles/{pid}/consents (API spec §4.14; endpoints #49–54). Owner only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..core.deps import OwnedProfile, OwnerUser
from ..db import DbSession
from ..services import consent_service, snapshot_service
from ..services.consent_service import ApproveIn

router = APIRouter(prefix="/profiles/{pid}/consents", tags=["consents"])


class ApproveBody(BaseModel):
    approved_sections: list[str] = Field(min_length=1)
    financing_request_id: uuid.UUID
    valid_days: int = 14


def _report(rep) -> dict:
    return {"version": rep.version, "snapshot_sha256": rep.snapshot_sha256}


@router.get("")
def list_consents(profile: OwnedProfile, db: DbSession) -> dict:
    rows = consent_service.list_consents(db, profile)
    return {"items": [consent_service.consent_row(db, c) for c in rows], "total": len(rows),
            "allowed_sections": list(snapshot_service.allowed_sections(profile)),
            "required_sections": list(snapshot_service.REQUIRED), "valid_days": list(consent_service.VALID_DAYS)}


@router.post("/{cid}/approve")
def approve(cid: uuid.UUID, body: ApproveBody, profile: OwnedProfile, user: OwnerUser, db: DbSession,
            request: Request) -> dict:
    rep = consent_service.approve(db, user, profile, cid, ApproveIn(**dict(body)), request)
    c = consent_service.get(db, profile, cid)
    return {**consent_service.consent_row(db, c), "report": _report(rep)}


@router.post("/{cid}/decline")
def decline(cid: uuid.UUID, profile: OwnedProfile, user: OwnerUser, db: DbSession, request: Request) -> dict:
    return consent_service.consent_row(db, consent_service.decline(db, user, profile, cid, request))


@router.post("/{cid}/revoke")
def revoke(cid: uuid.UUID, profile: OwnedProfile, user: OwnerUser, db: DbSession, request: Request) -> dict:
    return consent_service.consent_row(db, consent_service.revoke(db, user, profile, cid, request))


@router.post("/{cid}/reshare")
def reshare(cid: uuid.UUID, profile: OwnedProfile, user: OwnerUser, db: DbSession, request: Request) -> dict:
    rep = consent_service.reshare(db, user, profile, cid, request)
    return {**_report(rep), "consent": consent_service.consent_row(db, consent_service.get(db, profile, cid))}


@router.get("/{cid}/activity")
def activity(cid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> dict:
    """Reads, information requests and the decision — lender notes never."""
    return consent_service.activity(db, consent_service.get(db, profile, cid))
