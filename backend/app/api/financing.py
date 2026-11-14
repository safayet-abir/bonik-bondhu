"""/profiles/{pid}/financing-requests, items and assessments
(API spec §4.10–4.11; endpoints #36–39, #41–43). #40 parse-purpose is P6."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from ..core.deps import OwnedProfile
from ..db import DbSession
from ..schemas.assessment import AssessmentOut, ScenarioOut
from ..schemas.financing import FinancingCreate, FinancingList, FinancingOut, FinancingPatch, ItemCreate, ItemOut, ItemPatch
from ..schemas.forecast import AsOfIn
from ..services import assessment_service, financing_service, forecast_service

router = APIRouter(prefix="/profiles/{pid}", tags=["financing"])
BASE = "/financing-requests"


@router.get(BASE, response_model=FinancingList)
def list_requests(profile: OwnedProfile, db: DbSession) -> FinancingList:
    rows = financing_service.list_requests(db, profile)
    return FinancingList(items=[financing_service.request_out(db, profile, r) for r in rows], total=len(rows))


@router.post(BASE, status_code=status.HTTP_201_CREATED, response_model=FinancingOut)
def create_request(data: FinancingCreate, profile: OwnedProfile, db: DbSession) -> FinancingOut:
    return financing_service.request_out(db, profile, financing_service.create(db, profile, data))


@router.get(BASE + "/{rid}", response_model=FinancingOut)
def get_request(rid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> FinancingOut:
    return financing_service.request_out(db, profile, financing_service.get(db, profile, rid))


@router.patch(BASE + "/{rid}", response_model=FinancingOut)
def update_request(rid: uuid.UUID, patch: FinancingPatch, profile: OwnedProfile, db: DbSession) -> FinancingOut:
    return financing_service.request_out(db, profile, financing_service.update(db, profile, rid, patch))


@router.post(BASE + "/{rid}/items", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
def add_item(rid: uuid.UUID, data: ItemCreate, profile: OwnedProfile, db: DbSession) -> ItemOut:
    return financing_service.item_out(financing_service.add_item(db, profile, rid, data))


@router.patch(BASE + "/{rid}/items/{iid}", response_model=ItemOut)
def update_item(rid: uuid.UUID, iid: uuid.UUID, patch: ItemPatch, profile: OwnedProfile, db: DbSession) -> ItemOut:
    return financing_service.item_out(financing_service.update_item(db, profile, rid, iid, patch))


@router.delete(BASE + "/{rid}/items/{iid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(rid: uuid.UUID, iid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> Response:
    financing_service.delete_item(db, profile, rid, iid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(BASE + "/{rid}/assessments", status_code=status.HTTP_201_CREATED, response_model=AssessmentOut)
def run_assessment(rid: uuid.UUID, profile: OwnedProfile, db: DbSession, body: AsOfIn | None = None) -> AssessmentOut:
    as_of = forecast_service.resolve_as_of(body.as_of_date if body else None)
    return assessment_service.assessment_out(db, profile, assessment_service.run(db, profile, rid, as_of))


@router.get(BASE + "/{rid}/assessments/latest", response_model=AssessmentOut)
def latest_assessment(rid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> AssessmentOut:
    return assessment_service.assessment_out(db, profile, assessment_service.latest(db, profile, rid))


@router.get("/assessments/{aid}", response_model=AssessmentOut)
def get_assessment(aid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> AssessmentOut:
    return assessment_service.assessment_out(db, profile, assessment_service.get(db, profile, aid))


@router.get("/assessments/{aid}/scenarios")
def list_scenarios(aid: uuid.UUID, profile: OwnedProfile, db: DbSession) -> dict[str, list[ScenarioOut]]:
    return {"items": assessment_service.scenarios(db, profile, assessment_service.get(db, profile, aid))}
