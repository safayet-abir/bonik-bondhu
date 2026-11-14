from __future__ import annotations

import re
import uuid
from typing import Literal

from pydantic import BaseModel, ValidationInfo, field_validator

from ..core.security import normalize_phone, password_problem
from .common import InModel

_EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(InModel):
    full_name: str
    phone: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not 2 <= len(v) <= 100:
            raise ValueError("auth.err.full_name")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        phone = normalize_phone(v)
        if phone is None:
            raise ValueError("auth.err.phone_invalid")
        return phone

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.lower()
        if len(v) > 254 or not _EMAIL_RX.match(v):
            raise ValueError("auth.err.email_invalid")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str, info: ValidationInfo) -> str:
        problem = password_problem(v, info.data.get("phone"))
        if problem:
            raise ValueError(problem)
        return v


class LoginIn(InModel):
    phone: str
    password: str

    @field_validator("password")
    @classmethod
    def _bounded(cls, v: str) -> str:
        return v[:256]  # never hash unbounded input


class LenderOrgOut(BaseModel):
    id: uuid.UUID
    name: str
    is_demo: bool


class LenderInfoOut(BaseModel):
    organization: LenderOrgOut
    designation: str | None


class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str
    email: str
    role: str
    preferred_language: str
    is_demo: bool


class MeOut(UserOut):
    lender: LenderInfoOut | None = None


class MePatch(InModel):
    preferred_language: Literal["bn", "en"] | None = None
    full_name: str | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is not None and not 2 <= len(v) <= 100:
            raise ValueError("auth.err.full_name")
        return v
