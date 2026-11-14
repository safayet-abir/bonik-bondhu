"""Lender case list (SCR-L01). P1 only needs the list so a lender lands on a
real screen; requests, case files and review events arrive in P5."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..core.deps import LenderContext
from ..models import BusinessProfile, Consent

CaseFilter = Literal["pending", "active", "closed"]


class ApplicantOut(BaseModel):
    display_name: str
    activity_type: str
    is_demo: bool


class CaseOut(BaseModel):
    consent_id: uuid.UUID
    applicant: ApplicantOut | None
    status: str
    is_expired: bool
    valid_until: datetime | None


class CaseList(BaseModel):
    items: list[CaseOut]
    total: int


def list_cases(db: Session, lender: LenderContext, status: CaseFilter | None) -> CaseList:
    now = utcnow()
    conds = [Consent.lender_organization_id == lender.organization.id]
    active = and_(Consent.status == "approved", Consent.valid_until > now)
    if status == "pending":
        conds.append(Consent.status == "requested")
    elif status == "active":
        conds.append(active)
    elif status == "closed":
        conds.append(or_(Consent.status.in_(("declined", "revoked")),
                         and_(Consent.status == "approved", Consent.valid_until <= now)))
    rows = db.execute(
        select(Consent, BusinessProfile)
        .join(BusinessProfile, BusinessProfile.id == Consent.profile_id)
        .where(*conds)
        .order_by(Consent.created_at.desc())
    ).all()
    items = []
    for consent, profile in rows:
        expired = consent.status == "approved" and consent.valid_until is not None and consent.valid_until <= now
        # Applicant identity is hidden until the owner approves (API spec §4.15).
        applicant = (
            ApplicantOut(display_name=profile.display_name, activity_type=profile.activity_type,
                         is_demo=profile.is_demo)
            if consent.status == "approved" else None
        )
        items.append(CaseOut(consent_id=consent.id, applicant=applicant, status=consent.status,
                             is_expired=expired, valid_until=consent.valid_until))
    return CaseList(items=items, total=len(items))
