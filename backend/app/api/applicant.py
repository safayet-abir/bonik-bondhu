from fastapi import APIRouter, Request

from ..core.deps import OwnedProfile, OwnerUser
from ..db import DbSession
from ..schemas.applicant import ApplicantIn
from ..services import applicant_service

router = APIRouter(prefix="/profiles/{pid}/applicant-details", tags=["applicant"])


@router.get("")
def get(profile: OwnedProfile, db: DbSession):
    return applicant_service.masked(applicant_service.get(db, profile))


@router.put("")
def upsert(data: ApplicantIn, profile: OwnedProfile, user: OwnerUser, db: DbSession, request: Request):
    return applicant_service.masked(applicant_service.upsert(db, user, profile, data, request))
