"""Request dependencies: who is calling, and may they touch this resource
(Architecture §8). The server enforces everything; the UI only mirrors it."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path, Request
from sqlalchemy import select

from ..db import DbSession
from ..models import BusinessProfile, LenderOfficer, LenderOrganization, User, UserSession
from .audit import audit
from .clock import utcnow
from .errors import AppError
from .security import sha256_hex

SESSION_COOKIE = "bb_session"


@dataclass
class AuthContext:
    user: User
    session: UserSession


@dataclass
class LenderContext:
    user: User
    officer: LenderOfficer
    organization: LenderOrganization


def current_session(request: Request, db: DbSession) -> AuthContext:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AppError("AUTH_REQUIRED", 401, "auth.required")
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_sha256 == sha256_hex(token))
    ).first()
    now = utcnow()
    if (
        row is None
        or row.UserSession.revoked_at is not None
        or row.UserSession.expires_at <= now
        or not row.User.is_active
    ):
        raise AppError("SESSION_EXPIRED", 401, "auth.session_expired")
    row.UserSession.last_seen_at = now
    return AuthContext(user=row.User, session=row.UserSession)


CurrentAuth = Annotated[AuthContext, Depends(current_session)]


def require_owner(ctx: CurrentAuth) -> User:
    if ctx.user.role != "owner":
        raise AppError("FORBIDDEN_ROLE", 403, "err.forbidden_role")
    return ctx.user


OwnerUser = Annotated[User, Depends(require_owner)]


def require_lender(ctx: CurrentAuth, db: DbSession) -> LenderContext:
    if ctx.user.role != "lender_officer":
        raise AppError("FORBIDDEN_ROLE", 403, "err.forbidden_role")
    row = db.execute(
        select(LenderOfficer, LenderOrganization)
        .join(LenderOrganization, LenderOrganization.id == LenderOfficer.organization_id)
        .where(LenderOfficer.user_id == ctx.user.id)
    ).first()
    if row is None:
        raise AppError("FORBIDDEN_ROLE", 403, "err.forbidden_role")
    return LenderContext(user=ctx.user, officer=row.LenderOfficer, organization=row.LenderOrganization)


Lender = Annotated[LenderContext, Depends(require_lender)]


def get_owned_profile(
    request: Request,
    db: DbSession,
    user: OwnerUser,
    pid: Annotated[uuid.UUID, Path()],
) -> BusinessProfile:
    """The profile must exist, be active and belong to the caller; otherwise
    404 (never 403, so existence is not leaked — FR-PROF-05)."""
    profile = db.get(BusinessProfile, pid)
    if profile is None or profile.archived_at is not None:
        raise AppError("NOT_FOUND", 404, "err.not_found")
    if profile.owner_user_id != user.id:
        audit(db, "access.denied", "denied", request=request, actor_user_id=user.id,
              actor_role=user.role, entity_type="business_profile", entity_id=pid)
        raise AppError("NOT_FOUND", 404, "err.not_found", commit=True)
    return profile


OwnedProfile = Annotated[BusinessProfile, Depends(get_owned_profile)]


def _require_activity(activity_type: str):
    def dep(profile: OwnedProfile) -> BusinessProfile:
        # Ownership is checked first (404), then the type (403) — P2-T11.
        if profile.activity_type != activity_type:
            raise AppError("PROFILE_TYPE_MISMATCH", 403, "err.profile_type_mismatch")
        return profile
    return dep


FarmProfile = Annotated[BusinessProfile, Depends(_require_activity("crop_farm"))]
ShopProfile = Annotated[BusinessProfile, Depends(_require_activity("shop"))]
