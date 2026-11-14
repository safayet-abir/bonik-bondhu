"""Owner side of consent (FR-CON-02..09; API spec §4.14; P5-T02).

The owner always decides: a lender request does nothing until approved,
approval is per section and per time window (7/14/30 days, SUG-21), and
revoking stops access immediately. Every change is audited."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..core.clock import utcnow
from ..core.errors import AppError, not_found
from ..models import (
    AuditLog, BusinessProfile, Consent, FinancialAssessment, LenderOrganization, LenderReview, LenderReviewEvent,
    SharedReport, User,
)
from . import financing_service, snapshot_service

VALID_DAYS = (7, 14, 30)  # SUG-21


def is_expired(c: Consent) -> bool:
    return c.status == "approved" and c.valid_until is not None and c.valid_until <= utcnow()


def _state_error() -> AppError:
    return AppError("CONSENT_STATE_INVALID", 409, "consent.err.state")


def get(db: Session, profile: BusinessProfile, cid: uuid.UUID) -> Consent:
    c = db.scalar(select(Consent).where(Consent.profile_id == profile.id, Consent.id == cid))
    if c is None:
        raise not_found()
    return c


def latest_report(db: Session, c: Consent) -> SharedReport | None:
    return db.scalar(select(SharedReport).where(SharedReport.consent_id == c.id)
                     .order_by(SharedReport.version.desc()).limit(1))


def review(db: Session, c: Consent) -> LenderReview | None:
    return db.scalar(select(LenderReview).where(LenderReview.consent_id == c.id))


def _usable_assessment(db: Session, profile: BusinessProfile, rid: uuid.UUID) -> tuple:
    r = financing_service.get(db, profile, rid)
    a = db.scalar(select(FinancialAssessment).where(
        FinancialAssessment.profile_id == profile.id, FinancialAssessment.financing_request_id == r.id)
        .order_by(FinancialAssessment.created_at.desc(), FinancialAssessment.id).limit(1))
    if a is None or a.profile_data_version != profile.data_version:
        raise AppError("ASSESSMENT_STALE", 409, "consent.err.assessment_stale")
    return r, a


def _snapshot(db: Session, profile: BusinessProfile, c: Consent, r, a, version: int) -> SharedReport:
    snap = snapshot_service.build(db, profile, list(c.approved_sections or []), r, a)
    rep = SharedReport(consent_id=c.id, version=version, snapshot=snap, snapshot_sha256=snapshot_service.sha256(snap))
    db.add(rep)
    db.flush()
    return rep


@dataclass
class ApproveIn:
    approved_sections: list[str]
    financing_request_id: uuid.UUID
    valid_days: int = 14


def approve(db: Session, user: User, profile: BusinessProfile, cid: uuid.UUID, data: ApproveIn,
            request: Request | None = None) -> SharedReport:
    c = get(db, profile, cid)
    if c.status != "requested":
        raise _state_error()
    allowed = snapshot_service.allowed_sections(profile)
    sections = [s for s in snapshot_service.SECTIONS if s in set(data.approved_sections)]
    if set(data.approved_sections) - set(allowed):
        raise AppError("VALIDATION_ERROR", 422, "err.validation",
                       fields={"approved_sections": "consent.err.section_not_allowed"})
    if any(req not in sections for req in snapshot_service.REQUIRED):
        raise AppError("VALIDATION_ERROR", 422, "err.validation",
                       fields={"approved_sections": "consent.err.sections_required"})
    if data.valid_days not in VALID_DAYS:
        raise AppError("VALIDATION_ERROR", 422, "err.validation", fields={"valid_days": "consent.err.valid_days"})
    r, a = _usable_assessment(db, profile, data.financing_request_id)
    now = utcnow()
    c.status, c.approved_sections, c.financing_request_id, c.assessment_id = "approved", sections, r.id, a.id
    c.approved_at, c.valid_until = now, now + timedelta(days=data.valid_days)
    db.flush()
    rep = _snapshot(db, profile, c, r, a, 1)
    db.add(LenderReview(consent_id=c.id, organization_id=c.lender_organization_id, status="under_review"))
    audit(db, "consent.approve", request=request, actor_user_id=user.id, actor_role="owner", entity_type="consent",
          entity_id=c.id, profile_id=profile.id, lender_organization_id=c.lender_organization_id,
          metadata={"sections": sections, "valid_days": data.valid_days, "version": 1})
    db.flush()
    return rep


def decline(db: Session, user: User, profile: BusinessProfile, cid: uuid.UUID, request: Request | None = None) -> Consent:
    c = get(db, profile, cid)
    if c.status != "requested":
        raise _state_error()
    c.status, c.declined_at = "declined", utcnow()
    audit(db, "consent.decline", request=request, actor_user_id=user.id, actor_role="owner", entity_type="consent",
          entity_id=c.id, profile_id=profile.id, lender_organization_id=c.lender_organization_id)
    db.flush()
    return c


def revoke(db: Session, user: User, profile: BusinessProfile, cid: uuid.UUID, request: Request | None = None) -> Consent:
    c = get(db, profile, cid)
    if c.status != "approved":
        raise _state_error()
    c.status, c.revoked_at = "revoked", utcnow()
    audit(db, "consent.revoke", request=request, actor_user_id=user.id, actor_role="owner", entity_type="consent",
          entity_id=c.id, profile_id=profile.id, lender_organization_id=c.lender_organization_id)
    db.flush()
    return c


def reshare(db: Session, user: User, profile: BusinessProfile, cid: uuid.UUID,
            request: Request | None = None) -> SharedReport:
    """FR-CON-09: a new snapshot version from the latest non-stale assessment
    of the same request. Sections and validity stay as approved."""
    c = get(db, profile, cid)
    if c.status != "approved" or is_expired(c):
        raise _state_error()
    r, a = _usable_assessment(db, profile, c.financing_request_id)
    prev = latest_report(db, c)
    version = (prev.version if prev else 0) + 1
    c.assessment_id = a.id
    rep = _snapshot(db, profile, c, r, a, version)
    audit(db, "consent.reshare", request=request, actor_user_id=user.id, actor_role="owner", entity_type="consent",
          entity_id=c.id, profile_id=profile.id, lender_organization_id=c.lender_organization_id,
          metadata={"version": version})
    db.flush()
    return rep


# --------------------------------------------------------------------------- read models
def reads(db: Session, c: Consent) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(
        AuditLog.action == "consent.read", AuditLog.outcome == "success", AuditLog.entity_type == "consent",
        AuditLog.entity_id == c.id).order_by(AuditLog.occurred_at.desc())))


def owner_events(db: Session, c: Consent) -> list[LenderReviewEvent]:
    rv = review(db, c)
    if rv is None:
        return []
    return list(db.scalars(select(LenderReviewEvent).where(
        LenderReviewEvent.review_id == rv.id, LenderReviewEvent.visible_to_owner.is_(True))
        .order_by(LenderReviewEvent.created_at)))


def consent_row(db: Session, c: Consent) -> dict:
    org = db.get(LenderOrganization, c.lender_organization_id)
    officer = db.get(User, c.requested_by_user_id)
    rep = latest_report(db, c)
    rv = review(db, c)
    info = [e for e in owner_events(db, c) if e.event_type == "info_request"]
    read_count = db.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == "consent.read", AuditLog.outcome == "success", AuditLog.entity_id == c.id)) or 0
    return {
        "id": str(c.id), "status": c.status, "is_expired": is_expired(c),
        "lender_organization": {"name": org.name, "is_demo": org.is_demo},
        "requested_by": officer.full_name if officer else None,
        "requested_sections": list(c.requested_sections), "request_message": c.request_message,
        "approved_sections": list(c.approved_sections) if c.approved_sections else None,
        "financing_request_id": str(c.financing_request_id) if c.financing_request_id else None,
        "valid_until": c.valid_until.isoformat() if c.valid_until else None,
        "created_at": c.created_at.isoformat(),
        "latest_report": {"version": rep.version, "snapshot_sha256": rep.snapshot_sha256,
                          "created_at": rep.created_at.isoformat()} if rep else None,
        "read_count": read_count, "open_info_requests": len(info) if rv and rv.status == "info_requested" else 0,
        "review_status": rv.status if rv else None,
        "decision": {"decision": rv.decision, "reason": rv.decision_reason,
                     "at": rv.decided_at.isoformat()} if rv and rv.decision else None,
    }


def activity(db: Session, c: Consent) -> dict:
    org = db.get(LenderOrganization, c.lender_organization_id)
    rv = review(db, c)
    return {
        "reads": [{"at": r.occurred_at.isoformat(), "organization": org.name} for r in reads(db, c)],
        "info_requests": [{"at": e.created_at.isoformat(), "body": e.body}
                          for e in owner_events(db, c) if e.event_type == "info_request"],
        "decision": {"decision": rv.decision, "reason": rv.decision_reason, "at": rv.decided_at.isoformat(),
                     "organization": org.name} if rv and rv.decision else None,
    }


def list_consents(db: Session, profile: BusinessProfile) -> list[Consent]:
    return list(db.scalars(select(Consent).where(Consent.profile_id == profile.id)
                           .order_by(Consent.created_at.desc())))
