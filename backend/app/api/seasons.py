"""/profiles/{pid}/seasons (API spec §4.8). crop_farm only: any other
profile type gets 403 PROFILE_TYPE_MISMATCH (P2-T11, AT-15)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from ..core.clock import today
from ..core.deps import FarmProfile
from ..db import DbSession
from ..schemas.season import (
    CostItemCreate, CostItemOut, CostItemPatch, HarvestIn, LoanCoverBasis, SeasonCreate, SeasonDetail, SeasonList,
    SeasonOut, SeasonPatch, SeasonSummaryOut,
)
from ..services import assessment_service, season_service

router = APIRouter(prefix="/profiles/{pid}/seasons", tags=["seasons"])


@router.get("", response_model=SeasonList)
def list_seasons(profile: FarmProfile, db: DbSession) -> SeasonList:
    rows = season_service.list_seasons(db, profile)
    return SeasonList(items=[season_service.season_out(s) for s in rows], total=len(rows))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SeasonOut)
def create_season(data: SeasonCreate, profile: FarmProfile, db: DbSession) -> SeasonOut:
    return season_service.season_out(season_service.create(db, profile, data))


@router.get("/{sid}", response_model=SeasonDetail)
def get_season(sid: uuid.UUID, profile: FarmProfile, db: DbSession) -> SeasonDetail:
    return season_service.detail(db, profile, sid)


@router.patch("/{sid}", response_model=SeasonOut)
def update_season(sid: uuid.UUID, patch: SeasonPatch, profile: FarmProfile, db: DbSession) -> SeasonOut:
    return season_service.season_out(season_service.update(db, profile, sid, patch))


@router.post("/{sid}/cost-items", status_code=status.HTTP_201_CREATED, response_model=CostItemOut)
def add_cost_item(sid: uuid.UUID, data: CostItemCreate, profile: FarmProfile, db: DbSession) -> CostItemOut:
    return season_service.item_out(season_service.add_item(db, profile, sid, data))


@router.patch("/{sid}/cost-items/{iid}", response_model=CostItemOut)
def update_cost_item(sid: uuid.UUID, iid: uuid.UUID, patch: CostItemPatch, profile: FarmProfile,
                     db: DbSession) -> CostItemOut:
    return season_service.item_out(season_service.update_item(db, profile, sid, iid, patch))


@router.delete("/{sid}/cost-items/{iid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_item(sid: uuid.UUID, iid: uuid.UUID, profile: FarmProfile, db: DbSession) -> Response:
    season_service.delete_item(db, profile, sid, iid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{sid}/harvest", response_model=SeasonOut)
def record_harvest(sid: uuid.UUID, data: HarvestIn, profile: FarmProfile, db: DbSession) -> SeasonOut:
    return season_service.season_out(season_service.harvest(db, profile, sid, data))


@router.get("/{sid}/summary", response_model=SeasonSummaryOut)
def season_summary(sid: uuid.UUID, profile: FarmProfile, db: DbSession) -> SeasonSummaryOut:
    out = season_service.summary(db, profile, sid)
    cover = assessment_service.season_loan_cover(db, profile, season_service.get(db, profile, sid), today())
    if cover is not None:
        price, rid, repayment = cover
        out.loan_cover_price_per_kg = price
        out.loan_cover_basis = LoanCoverBasis(financing_request_id=rid, repayment_total=repayment)
    return out
