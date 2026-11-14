"""Business profiles: many per owner, shop or crop farm (MP §5, DEC-04)."""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..models import BusinessProfile, User
from ..schemas.profile import ProfileCreate, ProfileOut, ProfilePatch

# 32 symbols, no 0/O/1/I: ~50 bits for 10 chars (Security T14)
SHARE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SHARE_CODE_LENGTH = 10


def _new_share_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(SHARE_CODE_ALPHABET) for _ in range(SHARE_CODE_LENGTH))
        if not db.scalar(select(BusinessProfile.id).where(BusinessProfile.share_code == code)):
            return code


def bump_data_version(profile: BusinessProfile) -> None:
    """Call from every service that changes assessment inputs; assessments
    built on an older version become stale (FR-ASM-09)."""
    profile.data_version += 1
    profile.updated_at = utcnow()


def list_profiles(db: Session, user: User) -> list[BusinessProfile]:
    return list(db.scalars(
        select(BusinessProfile)
        .where(BusinessProfile.owner_user_id == user.id, BusinessProfile.archived_at.is_(None))
        .order_by(BusinessProfile.created_at)
    ))


def create_profile(db: Session, user: User, data: ProfileCreate) -> BusinessProfile:
    now = utcnow()
    declared = "household_withdrawal_monthly" in data.model_fields_set and data.household_withdrawal_monthly is not None
    profile = BusinessProfile(
        owner_user_id=user.id,
        activity_type=data.activity_type,
        display_name=data.display_name,
        business_category=data.business_category,
        district=data.district,
        upazila=data.upazila,
        market_area=data.market_area,
        household_withdrawal_monthly=data.household_withdrawal_monthly,
        household_declared_at=now if declared else None,
        share_code=_new_share_code(db),
    )
    db.add(profile)
    db.flush()
    return profile


def update_profile(profile: BusinessProfile, patch: ProfilePatch) -> BusinessProfile:
    fields = patch.model_fields_set
    for name in ("display_name", "business_category", "district", "upazila", "market_area"):
        if name in fields:
            value = getattr(patch, name)
            if name == "display_name" and value is None:
                continue  # display name cannot be removed
            setattr(profile, name, value)
    if "household_withdrawal_monthly" in fields:
        # Declaring 0 is valid and counts as declared (DEC-37); null clears it.
        profile.household_withdrawal_monthly = patch.household_withdrawal_monthly
        profile.household_declared_at = utcnow() if patch.household_withdrawal_monthly is not None else None
    bump_data_version(profile)
    return profile


def regenerate_share_code(db: Session, profile: BusinessProfile) -> str:
    # Existing consents reference the profile, not the code, so they are unaffected.
    profile.share_code = _new_share_code(db)
    profile.updated_at = utcnow()
    return profile.share_code


def profile_out(p: BusinessProfile) -> ProfileOut:
    return ProfileOut(
        id=p.id,
        activity_type=p.activity_type,
        display_name=p.display_name,
        business_category=p.business_category,
        district=p.district,
        upazila=p.upazila,
        market_area=p.market_area,
        household_withdrawal_monthly=p.household_withdrawal_monthly,
        household_declared=p.household_declared_at is not None,
        no_debt_declared=p.no_debt_declared_at is not None,
        share_code=p.share_code,
        is_demo=p.is_demo,
        financing_fields_complete=bool(p.district and p.upazila and p.business_category)
        and p.household_declared_at is not None,
    )
