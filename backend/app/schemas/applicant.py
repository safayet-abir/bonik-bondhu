from __future__ import annotations

import re
from datetime import date

from pydantic import ConfigDict, StrictInt, field_validator

from ..core.clock import today
from .common import InModel

FIELDS = ("full_legal_name", "date_of_birth", "nid_number", "address", "nominee_name", "nominee_relation",
          "trade_licence", "years_in_business")
REQUIRED = tuple(f for f in FIELDS if f != "trade_licence")


class ApplicantIn(InModel):
    """Partial upsert. Omitted sensitive fields retain their saved value; null clears it."""

    model_config = ConfigDict(extra="forbid")

    full_legal_name: str | None = None
    date_of_birth: date | None = None
    nid_number: str | None = None
    address: str | None = None
    nominee_name: str | None = None
    nominee_relation: str | None = None
    trade_licence: str | None = None
    years_in_business: StrictInt | None = None

    @field_validator("full_legal_name", "address", "nominee_name", "nominee_relation", "trade_licence")
    @classmethod
    def _text(cls, value, info):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        limits = {"full_legal_name": (2, 120), "address": (2, 300), "nominee_name": (2, 120),
                  "nominee_relation": (2, 80), "trade_licence": (1, 100)}
        low, high = limits[info.field_name]
        if not low <= len(value) <= high:
            raise ValueError("applicant.err." + info.field_name)
        return value

    @field_validator("nid_number")
    @classmethod
    def _nid(cls, value):
        if value is None:
            return None
        value = value.strip().translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
        if not re.fullmatch(r"(?:[0-9]{10}|[0-9]{13}|[0-9]{17})", value):
            raise ValueError("applicant.err.nid_number")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def _birth(cls, value):
        if value is not None and not date(1900, 1, 1) <= value <= today():
            raise ValueError("applicant.err.date_of_birth")
        return value

    @field_validator("years_in_business")
    @classmethod
    def _years(cls, value):
        if value is not None and not 0 <= value <= 80:
            raise ValueError("applicant.err.years_in_business")
        return value
