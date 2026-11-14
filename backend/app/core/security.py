"""Passwords (Argon2id, SUG-02), session tokens (SUG-03), phone and password
rules (SUG-24, SUG-25)."""
from __future__ import annotations

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # library defaults = Argon2id
# Verified against when the phone is unknown, so response time does not reveal
# whether an account exists (TRD §5 "Dummy verify").
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_PHONE_RX = re.compile(r"^(?:\+?88)?(01[3-9]\d{8})$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-time verify. With password_hash=None runs a dummy verify and
    returns False."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    """32 random bytes, base64url. Only its SHA-256 is stored."""
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_phone(raw: str) -> str | None:
    """'01712345678', '+8801712345678', '8801712345678', Bangla digits,
    spaces or dashes -> '+8801712345678'. Returns None if invalid."""
    s = raw.translate(_BN_DIGITS)
    s = re.sub(r"[\s\-()]", "", s)
    m = _PHONE_RX.match(s)
    return f"+88{m.group(1)}" if m else None


def password_problem(password: str, phone_e164: str | None) -> str | None:
    """SUG-25: 8–128 chars, not only digits, not equal to the phone number.
    Returns an i18n key, or None if acceptable."""
    if not 8 <= len(password) <= 128:
        return "auth.err.password_length"
    if password.isdigit():
        return "auth.err.password_digits"
    if phone_e164:
        local = phone_e164.removeprefix("+88")
        digits_only = password.translate(_BN_DIGITS).lstrip("+")
        if digits_only in {local, phone_e164.lstrip("+"), local.removeprefix("0")}:
            return "auth.err.password_phone"
    return None
