"""/profiles/{pid}/forecasts (API spec §4.9). Shop profiles only: a farm
profile gets 403 PROFILE_TYPE_MISMATCH (FR-SEA-08, AT-15)."""
from __future__ import annotations

from fastapi import APIRouter, status

from ..core.errors import not_found
from ..db import DbSession
from ..core.deps import ShopProfile
from ..schemas.forecast import AsOfIn, ForecastOut
from ..services import forecast_service

router = APIRouter(prefix="/profiles/{pid}/forecasts", tags=["forecasts"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ForecastOut)
def run_forecast(profile: ShopProfile, db: DbSession, body: AsOfIn | None = None) -> ForecastOut:
    as_of = forecast_service.resolve_as_of(body.as_of_date if body else None)
    return forecast_service.forecast_out(forecast_service.create_run(db, profile, as_of), profile)


@router.get("/latest", response_model=ForecastOut)
def latest_forecast(profile: ShopProfile, db: DbSession) -> ForecastOut:
    run = forecast_service.latest(db, profile)
    if run is None:
        raise not_found()
    return forecast_service.forecast_out(run, profile)
