from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, field_validator

from .common import InModel, MoneyOut, NonNegativeMoneyIn


def _short_text(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if len(v) > 80:
        raise ValueError("err.field.too_long")
    return v


class _ProgressiveFields(InModel):
    """Optional at creation; requested only when financing/sharing (FR-PROF-06)."""

    business_category: str | None = None
    district: str | None = None
    upazila: str | None = None
    market_area: str | None = None
    household_withdrawal_monthly: NonNegativeMoneyIn | None = None

    @field_validator("business_category", "district", "upazila", "market_area")
    @classmethod
    def _text(cls, v: str | None) -> str | None:
        return _short_text(v)


def _display_name(v: str) -> str:
    if not 2 <= len(v) <= 80:
        raise ValueError("profile.err.name")
    return v


class ProfileCreate(_ProgressiveFields):
    display_name: str
    activity_type: Literal["shop", "crop_farm"]

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _display_name(v)


class ProfilePatch(_ProgressiveFields):
    display_name: str | None = None

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return None if v is None else _display_name(v)


class ProfileOut(BaseModel):
    id: uuid.UUID
    activity_type: str
    display_name: str
    business_category: str | None
    district: str | None
    upazila: str | None
    market_area: str | None
    household_withdrawal_monthly: MoneyOut | None
    household_declared: bool
    no_debt_declared: bool
    share_code: str
    is_demo: bool
    financing_fields_complete: bool


class ProfileList(BaseModel):
    items: list[ProfileOut]


class ShareCodeOut(BaseModel):
    share_code: str
