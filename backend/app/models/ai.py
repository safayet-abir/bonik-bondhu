from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class Document(Base):
    """Uploaded receipt photo (FR-EXT-01): re-encoded, EXIF-free, stored under
    a random name in UPLOAD_DIR; served only to its owner."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str]
    mime_type: Mapped[str]
    size_bytes: Mapped[int]
    sha256: Mapped[str]
    purpose: Mapped[str] = mapped_column(default="receipt")
    created_at: Mapped[datetime] = created_at_col()


class ExtractionDraft(Base):
    """AI proposal for a receipt (FR-EXT-02) — never a transaction until the owner confirms."""

    __tablename__ = "extraction_drafts"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_profiles.id"))
    document_id: Mapped[uuid.UUID]
    status: Mapped[str] = mapped_column(default="pending")
    provider: Mapped[str]
    model: Mapped[str | None]
    proposed: Mapped[dict] = mapped_column(JSONB, default=dict)
    confirmed_transaction_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created_at_col()
    resolved_at: Mapped[datetime | None]


class AiInteraction(Base):
    """Metadata of one AI call (SUG-22): never prompt or reply text."""

    __tablename__ = "ai_interactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("business_profiles.id"))
    feature: Mapped[str]
    provider: Mapped[str]
    model: Mapped[str | None]
    status: Mapped[str]
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]
    tools_called: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    grounding_check: Mapped[str] = mapped_column(default="not_applicable")
    created_at: Mapped[datetime] = created_at_col()
