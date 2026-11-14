from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class NewsEvent(Base):
    """Curated news event (L1, DEC-15; DB doc news_events). Headline, link
    and a short team-written summary only — never article text (FR-NEWS-05).
    Imported by the admin CLI; read-only at request time."""

    __tablename__ = "news_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    headline: Mapped[str]
    headline_lang: Mapped[str]
    summary: Mapped[str | None]
    source_name: Mapped[str]
    source_url: Mapped[str | None]
    published_date: Mapped[date]
    event_date: Mapped[date | None]
    event_type: Mapped[str]
    districts: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    upazilas: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    sectors: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    commodities: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    source_count: Mapped[int] = mapped_column(default=1)
    dedup_key: Mapped[str]
    is_demo: Mapped[bool] = mapped_column(default=False)
    curated_by: Mapped[str]
    created_at: Mapped[datetime] = created_at_col()
