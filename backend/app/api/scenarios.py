"""/profiles/{pid}/scenarios/{scid}/{confirm,dismiss} (API #44–45; FR-NEWS-04).
Neither action changes the assessment status (DEC-30)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from ..core.deps import OwnedProfile
from ..db import DbSession
from ..schemas.assessment import ScenarioOut
from ..services import assessment_service, scenario_service

router = APIRouter(prefix="/profiles/{pid}/scenarios", tags=["scenarios"])


@router.post("/{scid}/confirm", response_model=ScenarioOut)
def confirm(scid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> ScenarioOut:
    return assessment_service.scenario_out(db, profile, scenario_service.confirm(db, profile, scid))


@router.post("/{scid}/dismiss", response_model=ScenarioOut)
def dismiss(scid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> ScenarioOut:
    return assessment_service.scenario_out(db, profile, scenario_service.dismiss(db, profile, scid))
