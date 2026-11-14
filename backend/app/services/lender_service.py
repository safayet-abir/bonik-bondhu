"""Lender portal (API spec §4.15; FR-CON-01, FR-LEN-01..07; P5-T01/T04/T05).

* An access request always gets the same 202 — a share code is a locator,
  not a key, and validity is never revealed (SEC-13).
* Case reads go through `get_authorized_consent`: other organisation → 404,
  not approved → 403 CONSENT_REQUIRED, revoked → 403 CONSENT_REVOKED,
  expired → 403 CONSENT_EXPIRED. Every read and every denial is audited.
* The lender sees only the stored snapshot (DEC-31) and records a DEMO
  decision; Bonik Bondhu never lends or approves."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from fastapi import Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..core.clock import utcnow
from ..core.deps import LenderContext
from ..core.errors import AppError
from ..core.rate_limit import SlidingWindowLimiter
from ..models import (
    AuditLog, BusinessProfile, Consent, FinancialAssessment, FinancingRequest, LenderReview, LenderReviewEvent, User,
)
from . import consent_service, snapshot_service

CaseFilter = Literal["pending", "active", "closed"]
access_request_limiter = SlidingWindowLimiter(limit=20, window_seconds=3600)  # 20/hour/officer (SUG-05 family)
GENERIC = {"message_key": "lender.request_sent_if_valid"}


# --------------------------------------------------------------------------- schemas
class AccessRequestIn(BaseModel):
    share_code: str = Field(max_length=40)
    requested_sections: list[str] = Field(min_length=1)
    message: str | None = Field(default=None, max_length=500)

    @field_validator("requested_sections")
    @classmethod
    def _sections(cls, v: list[str]) -> list[str]:
        if not set(v) <= set(snapshot_service.SECTIONS):
            raise ValueError("consent.err.section_not_allowed")
        return [s for s in snapshot_service.SECTIONS if s in set(v)]

    @field_validator("message")
    @classmethod
    def _msg(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class EventIn(BaseModel):
    event_type: Literal["status_change", "note", "info_request", "decision"]
    status: Literal["under_review", "info_requested"] | None = None
    decision: Literal["proceed", "decline", "refer"] | None = None
    body: str | None = Field(default=None, max_length=1000)


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
    requested_sections: list[str]
    created_at: datetime
    assessment_status: str | None = None
    requested_amount: str | None = None
    review_status: str | None = None
    decision: str | None = None
    last_read_at: datetime | None = None


class CaseList(BaseModel):
    items: list[CaseOut]
    total: int


def normalize_code(code: str) -> str:
    return re.sub(r"[\s\-]", "", code or "").upper()


# --------------------------------------------------------------------------- access request
def access_request(db: Session, lender: LenderContext, data: AccessRequestIn, request: Request | None = None) -> dict:
    access_request_limiter.hit(str(lender.user.id))
    code = normalize_code(data.share_code)
    profile = db.scalar(select(BusinessProfile).where(BusinessProfile.share_code == code,
                                                      BusinessProfile.archived_at.is_(None))) if code else None
    common = dict(request=request, actor_user_id=lender.user.id, actor_role="lender_officer",
                  lender_organization_id=lender.organization.id)
    if profile is None:
        audit(db, "consent.request", "denied", metadata={"reason": "invalid_code"}, **common)
        return GENERIC
    open_req = db.scalar(select(Consent.id).where(Consent.profile_id == profile.id,
                                                  Consent.lender_organization_id == lender.organization.id,
                                                  Consent.status == "requested"))
    if open_req:
        audit(db, "consent.request", "denied", entity_type="consent", entity_id=open_req, profile_id=profile.id,
              metadata={"reason": "already_open"}, **common)
        return GENERIC
    c = Consent(profile_id=profile.id, lender_organization_id=lender.organization.id,
                requested_by_user_id=lender.user.id, requested_sections=data.requested_sections,
                request_message=data.message, status="requested")
    db.add(c)
    db.flush()
    audit(db, "consent.request", entity_type="consent", entity_id=c.id, profile_id=profile.id,
          metadata={"sections": data.requested_sections}, **common)
    return GENERIC


# --------------------------------------------------------------------------- guard
def get_authorized_consent(db: Session, lender: LenderContext, cid: uuid.UUID,
                           request: Request | None = None) -> Consent:
    c = db.get(Consent, cid)
    common = dict(request=request, actor_user_id=lender.user.id, actor_role="lender_officer",
                  entity_type="consent", entity_id=cid, lender_organization_id=lender.organization.id)

    def deny(code: str, status: int, key: str, reason: str) -> AppError:
        audit(db, "consent.read_denied", "denied", profile_id=c.profile_id if c else None,
              metadata={"reason": reason}, **common)
        return AppError(code, status, key, commit=True)

    if c is None or c.lender_organization_id != lender.organization.id:
        raise deny("NOT_FOUND", 404, "err.not_found", "not_found_or_other_org")
    if c.status in ("requested", "declined"):
        raise deny("CONSENT_REQUIRED", 403, "lender.err.consent_required", c.status)
    if c.status == "revoked":
        raise deny("CONSENT_REVOKED", 403, "lender.err.consent_revoked", "revoked")
    if consent_service.is_expired(c):
        raise deny("CONSENT_EXPIRED", 403, "lender.err.consent_expired", "expired")
    return c


# --------------------------------------------------------------------------- case list / file
def _last_read(db: Session, lender: LenderContext, cid: uuid.UUID) -> datetime | None:
    return db.scalar(select(func.max(AuditLog.occurred_at)).where(
        AuditLog.action == "consent.read", AuditLog.outcome == "success", AuditLog.entity_id == cid,
        AuditLog.lender_organization_id == lender.organization.id))


def list_cases(db: Session, lender: LenderContext, status: CaseFilter | None) -> CaseList:
    now = utcnow()
    conds = [Consent.lender_organization_id == lender.organization.id]
    if status == "pending":
        conds.append(Consent.status == "requested")
    elif status == "active":
        conds.append(and_(Consent.status == "approved", Consent.valid_until > now))
    elif status == "closed":
        conds.append(or_(Consent.status.in_(("declined", "revoked")),
                         and_(Consent.status == "approved", Consent.valid_until <= now)))
    rows = db.execute(select(Consent, BusinessProfile).join(BusinessProfile, BusinessProfile.id == Consent.profile_id)
                      .where(*conds).order_by(Consent.created_at.desc())).all()
    items = []
    for c, profile in rows:
        shared = c.status in ("approved", "revoked")  # the owner did share this case at some point
        a = db.get(FinancialAssessment, c.assessment_id) if c.assessment_id and shared else None
        r = db.get(FinancingRequest, c.financing_request_id) if c.financing_request_id and shared else None
        rv = consent_service.review(db, c)
        items.append(CaseOut(
            consent_id=c.id, status=c.status, is_expired=consent_service.is_expired(c), valid_until=c.valid_until,
            requested_sections=list(c.requested_sections), created_at=c.created_at,
            # Applicant identity is hidden until the owner approves (API spec §4.15).
            applicant=ApplicantOut(display_name=profile.display_name, activity_type=profile.activity_type,
                                   is_demo=profile.is_demo) if shared else None,
            assessment_status=a.status if a else None,
            requested_amount=f"{r.requested_amount:.2f}" if r else None,
            review_status=rv.status if rv else None, decision=rv.decision if rv else None,
            last_read_at=_last_read(db, lender, c.id),
        ))
    return CaseList(items=items, total=len(items))


def _event_out(e: LenderReviewEvent, names: dict) -> dict:
    return {"id": str(e.id), "event_type": e.event_type, "body": e.body, "visible_to_owner": e.visible_to_owner,
            "officer": names.get(e.officer_user_id), "at": e.created_at.isoformat()}


def _review_out(db: Session, rv: LenderReview) -> dict:
    events = list(db.scalars(select(LenderReviewEvent).where(LenderReviewEvent.review_id == rv.id)
                             .order_by(LenderReviewEvent.created_at, LenderReviewEvent.id)))
    ids = {e.officer_user_id for e in events} | ({rv.decided_by} if rv.decided_by else set())
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    return {"status": rv.status, "decision": rv.decision, "decision_reason": rv.decision_reason,
            "decided_by": names.get(rv.decided_by) if rv.decided_by else None,
            "decided_at": rv.decided_at.isoformat() if rv.decided_at else None,
            "events": [_event_out(e, names) for e in events]}


def case_file(db: Session, lender: LenderContext, cid: uuid.UUID, request: Request | None = None) -> dict:
    c = get_authorized_consent(db, lender, cid, request)
    rep = consent_service.latest_report(db, c)
    rv = consent_service.review(db, c)
    audit(db, "consent.read", request=request, actor_user_id=lender.user.id, actor_role="lender_officer",
          entity_type="consent", entity_id=c.id, profile_id=c.profile_id,
          lender_organization_id=lender.organization.id, metadata={"version": rep.version if rep else None})
    return {
        "consent": {"id": str(c.id), "approved_sections": list(c.approved_sections or []),
                    "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                    "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                    "version": rep.version if rep else None,
                    "snapshot_sha256": rep.snapshot_sha256 if rep else None,
                    "shared_at": rep.created_at.isoformat() if rep else None,
                    "hash_verified": snapshot_service.verify_snapshot(rep.snapshot, rep.snapshot_sha256) if rep else False},
        "organization": {"name": lender.organization.name, "is_demo": lender.organization.is_demo},
        "snapshot": rep.snapshot if rep else None,
        "review": _review_out(db, rv) if rv else None,
        "cib_notice_key": "debt.cib",
        "banner_key": "lender.decision_banner" if rv and rv.decision else None,
    }


# --------------------------------------------------------------------------- events
def _field(name: str, key: str) -> AppError:
    return AppError("VALIDATION_ERROR", 422, "err.validation", fields={name: key})


def add_event(db: Session, lender: LenderContext, cid: uuid.UUID, data: EventIn, request: Request | None = None) -> dict:
    c = get_authorized_consent(db, lender, cid, request)
    rv = consent_service.review(db, c)
    if rv is None:  # cannot happen for an approved consent, but never write without a review row
        rv = LenderReview(consent_id=c.id, organization_id=c.lender_organization_id, status="under_review")
        db.add(rv)
        db.flush()
    body = (data.body or "").strip()
    now = utcnow()
    if data.event_type == "status_change":
        if data.status is None:
            raise _field("status", "lender.err.status")
        if rv.decision:
            raise AppError("CONFLICT", 409, "lender.err.decision_recorded")
        rv.status = data.status
        body = body or f"status: {data.status}"
    elif data.event_type == "decision":
        if data.decision is None:
            raise _field("decision", "lender.err.decision")
        if len(body) < 5:
            raise _field("body", "lender.err.reason")
        rv.status, rv.decision, rv.decision_reason = "decision_recorded", data.decision, body
        rv.decided_by, rv.decided_at = lender.user.id, now
        body = f"{data.decision}: {body}"
    else:
        if not body:
            raise _field("body", "lender.err.body")
        if data.event_type == "info_request" and not rv.decision:
            rv.status = "info_requested"
    rv.updated_at = now
    event = LenderReviewEvent(review_id=rv.id, officer_user_id=lender.user.id, event_type=data.event_type,
                              body=body[:1000], visible_to_owner=data.event_type in ("info_request", "decision"))
    db.add(event)
    db.flush()
    audit(db, "lender.decision" if data.event_type == "decision" else "lender.event", request=request,
          actor_user_id=lender.user.id, actor_role="lender_officer", entity_type="consent", entity_id=c.id,
          profile_id=c.profile_id, lender_organization_id=lender.organization.id,
          metadata={"event_type": data.event_type, **({"decision": data.decision} if data.decision else {})})
    out = {"review": {"status": rv.status, "decision": rv.decision},
           "event": _event_out(event, {lender.user.id: lender.user.full_name})}
    if data.event_type == "decision":
        out["banner_key"] = "lender.decision_banner"
    return out
