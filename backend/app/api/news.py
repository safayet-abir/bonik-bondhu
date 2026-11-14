"""/profiles/{pid}/news-signals (API #46; FR-NEWS-02/03/06)."""
from __future__ import annotations

from fastapi import APIRouter

from ..core.clock import today
from ..core.deps import OwnedProfile
from ..db import DbSession
from ..services import assessment_service

router = APIRouter(prefix="/profiles/{pid}", tags=["news"])


@router.get("/news-signals")
def news_signals(profile: OwnedProfile, db: DbSession) -> dict[str, list[dict]]:
    """Curated events relevant to this profile today. An empty list is a
    normal answer (no news in our list), never an error."""
    return {"items": assessment_service.news_signal_rows(db, profile, today())}
