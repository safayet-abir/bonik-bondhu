"""/profiles/{pid}/advisor (API spec §4.13; P6-T06; FR-ADV-01..08)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from ..ai.tools import Toolbox
from ..core.deps import OwnedProfile, OwnerUser
from ..db import DbSession
from ..schemas.ai import AdvisorIn, AdvisorOut
from ..services import ai_service

router = APIRouter(prefix="/profiles/{pid}/advisor", tags=["advisor"])


@router.post("/messages", response_model=AdvisorOut)
def message(data: AdvisorIn, profile: OwnedProfile, user: OwnerUser, db: DbSession) -> dict:
    return ai_service.advise(db, user, profile, data)


@router.get("/help-topics")
def help_topics(profile: OwnedProfile, user: OwnerUser, db: DbSession, lang: Literal["bn", "en"] | None = None) -> dict:
    lang = lang or user.preferred_language or "bn"
    return ai_service.help_payload(Toolbox(db, profile, lang), lang)
