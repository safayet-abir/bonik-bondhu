"""/profiles (API spec §4.3). Every {pid} route goes through
get_owned_profile (404 if not owned)."""
from __future__ import annotations

from fastapi import APIRouter, status

from ..core.deps import OwnedProfile, OwnerUser
from ..db import DbSession
from ..schemas.profile import ProfileCreate, ProfileList, ProfileOut, ProfilePatch, ShareCodeOut
from ..services import profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=ProfileList)
def list_profiles(user: OwnerUser, db: DbSession) -> ProfileList:
    return ProfileList(items=[profile_service.profile_out(p) for p in profile_service.list_profiles(db, user)])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileOut)
def create_profile(data: ProfileCreate, user: OwnerUser, db: DbSession) -> ProfileOut:
    return profile_service.profile_out(profile_service.create_profile(db, user, data))


@router.get("/{pid}", response_model=ProfileOut)
def get_profile(profile: OwnedProfile) -> ProfileOut:
    return profile_service.profile_out(profile)


@router.patch("/{pid}", response_model=ProfileOut)
def patch_profile(patch: ProfilePatch, profile: OwnedProfile) -> ProfileOut:
    return profile_service.profile_out(profile_service.update_profile(profile, patch))


@router.post("/{pid}/share-code/regenerate", response_model=ShareCodeOut)
def regenerate_share_code(profile: OwnedProfile, db: DbSession) -> ShareCodeOut:
    return ShareCodeOut(share_code=profile_service.regenerate_share_code(db, profile))
