from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class Consent(Base):
    """Request/approve/decline/revoke lifecycle (DB doc §5.18). "Expired" is
    computed from valid_until, never stored."""

    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    lender_organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_organizations.id"))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_officers.user_id"))
    requested_sections: Mapped[list[str]] = mapped_column(ARRAY(Text))
    request_message: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="requested")
    approved_sections: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    financing_request_id: Mapped[uuid.UUID | None]
    assessment_id: Mapped[uuid.UUID | None]
    valid_until: Mapped[datetime | None]
    approved_at: Mapped[datetime | None]
    declined_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_col()


class SharedReport(Base):
    """Immutable snapshot of the approved sections (DEC-19/31). The lender
    reads only this, never live data."""

    __tablename__ = "shared_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consents.id"))
    version: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSONB)
    snapshot_sha256: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = created_at_col()


class LenderReview(Base):
    __tablename__ = "lender_reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consents.id"), unique=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_organizations.id"))
    status: Mapped[str] = mapped_column(default="under_review")
    decision: Mapped[str | None]
    decision_reason: Mapped[str | None]
    decided_by: Mapped[uuid.UUID | None]
    decided_at: Mapped[datetime | None]
    updated_at: Mapped[datetime] = created_at_col()


class LenderReviewEvent(Base):
    """`note` is never shown to the owner; `info_request` always is."""

    __tablename__ = "lender_review_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_reviews.id"))
    officer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_officers.user_id"))
    event_type: Mapped[str]
    body: Mapped[str]
    visible_to_owner: Mapped[bool]
    created_at: Mapped[datetime] = created_at_col()
