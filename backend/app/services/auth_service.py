"""Registration, login with lockout, logout (FR-AUTH-01..07; TRD §5)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.audit import audit, client_ip
from ..core.clock import utcnow
from ..core.errors import AppError
from ..core.rate_limit import auth_ip_limiter
from ..core.security import hash_password, new_session_token, normalize_phone, sha256_hex, verify_password
from ..models import LenderOfficer, LenderOrganization, User, UserSession
from ..schemas.auth import LenderInfoOut, LenderOrgOut, LoginIn, MeOut, MePatch, RegisterIn, UserOut

MAX_FAILED_LOGINS = 5          # SUG-05
LOCK_DURATION = timedelta(minutes=15)


def _invalid_credentials() -> AppError:
    # Same code and message whether or not the phone exists (FR-AUTH-04).
    return AppError("INVALID_CREDENTIALS", 401, "auth.err.invalid", commit=True)


def register(db: Session, data: RegisterIn, request: Request) -> User:
    auth_ip_limiter.hit(client_ip(request) or "unknown")
    if db.scalar(select(User.id).where(User.phone_e164 == data.phone)):
        raise AppError("PHONE_TAKEN", 409, "auth.err.phone_taken", fields={"phone": "auth.err.phone_taken"})
    if db.scalar(select(User.id).where(func.lower(User.email) == data.email)):
        raise AppError("EMAIL_TAKEN", 409, "auth.err.email_taken", fields={"email": "auth.err.email_taken"})
    user = User(
        full_name=data.full_name,
        phone_e164=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
        role="owner",  # self-registration can only ever create owners (FR-AUTH-07)
    )
    db.add(user)
    db.flush()
    audit(db, "auth.register", request=request, actor_user_id=user.id, actor_role="owner",
          entity_type="user", entity_id=user.id)
    return user


@dataclass
class LoginResult:
    user: User
    token: str
    max_age_seconds: int


def login(db: Session, data: LoginIn, request: Request) -> LoginResult:
    auth_ip_limiter.hit(client_ip(request) or "unknown")
    now = utcnow()
    phone = normalize_phone(data.phone)
    user = db.scalar(select(User).where(User.phone_e164 == phone)) if phone else None

    if user is not None and user.locked_until is not None and user.locked_until > now:
        audit(db, "auth.login_failed", "denied", request=request, actor_user_id=user.id,
              metadata={"reason": "locked"})
        retry = int((user.locked_until - now).total_seconds()) + 1
        raise AppError("ACCOUNT_LOCKED", 429, "auth.err.locked",
                       extra={"retry_after_seconds": retry}, commit=True)

    # Always run a hash verification (dummy hash for unknown phones) so the
    # response time does not reveal which phones are registered.
    ok = verify_password(user.password_hash if user else None, data.password)
    if not ok or user is None or not user.is_active:
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = now + LOCK_DURATION
                user.failed_login_count = 0
                audit(db, "auth.locked", "denied", request=request, actor_user_id=user.id)
        audit(db, "auth.login_failed", "failure", request=request,
              actor_user_id=user.id if user else None)
        raise _invalid_credentials()

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    settings = get_settings()
    lifetime = (
        timedelta(days=settings.OWNER_SESSION_DAYS)
        if user.role == "owner"
        else timedelta(hours=settings.LENDER_SESSION_HOURS)
    )
    token = new_session_token()
    db.add(UserSession(user_id=user.id, token_sha256=sha256_hex(token), created_at=now,
                       last_seen_at=now, expires_at=now + lifetime))
    audit(db, "auth.login", request=request, actor_user_id=user.id, actor_role=user.role)
    return LoginResult(user=user, token=token, max_age_seconds=int(lifetime.total_seconds()))


def logout(db: Session, session: UserSession, user: User, request: Request) -> None:
    session.revoked_at = utcnow()
    audit(db, "auth.logout", request=request, actor_user_id=user.id, actor_role=user.role)


def update_me(user: User, patch: MePatch) -> User:
    if patch.preferred_language is not None:
        user.preferred_language = patch.preferred_language
    if patch.full_name is not None:
        user.full_name = patch.full_name
    user.updated_at = utcnow()
    return user


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, full_name=user.full_name, phone=user.phone_e164, email=user.email,
                   role=user.role, preferred_language=user.preferred_language, is_demo=user.is_demo)


def me_out(db: Session, user: User) -> MeOut:
    lender = None
    if user.role == "lender_officer":
        row = db.execute(
            select(LenderOfficer, LenderOrganization)
            .join(LenderOrganization, LenderOrganization.id == LenderOfficer.organization_id)
            .where(LenderOfficer.user_id == user.id)
        ).first()
        if row:
            org = row.LenderOrganization
            lender = LenderInfoOut(
                organization=LenderOrgOut(id=org.id, name=org.name, is_demo=org.is_demo),
                designation=row.LenderOfficer.designation,
            )
    return MeOut(**user_out(user).model_dump(), lender=lender)
