from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """Append-only (DB trigger rejects UPDATE/DELETE). Never store
    passwords, tokens or raw IPs here."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_user_id: Mapped[uuid.UUID | None]
    actor_role: Mapped[str | None]
    action: Mapped[str]
    outcome: Mapped[str]  # success | denied | failure
    entity_type: Mapped[str | None]
    entity_id: Mapped[uuid.UUID | None]
    profile_id: Mapped[uuid.UUID | None]
    lender_organization_id: Mapped[uuid.UUID | None]
    ip_sha256: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
