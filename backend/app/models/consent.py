from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class Consent(Base):
    """Request/approve/decline/revoke lifecycle (DB doc §5.18). "Expired" is
    computed from valid_until, never stored. Full workflow arrives in P5."""

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
