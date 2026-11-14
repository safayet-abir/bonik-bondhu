from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at_col, uuid_pk


class LenderOrganization(Base):
    __tablename__ = "lender_organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(unique=True)
    org_type: Mapped[str]
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at_col()


class LenderOfficer(Base):
    __tablename__ = "lender_officers"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_organizations.id"))
    designation: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_col()
