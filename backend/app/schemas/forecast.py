from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from .common import InModel, MoneyOut


class AsOfIn(InModel):
    """Optional as-of date; honoured outside production only (tests, demo
    rehearsal). In production the business date is always today (Dhaka)."""

    as_of_date: date | None = None


class WeeklyNet(BaseModel):
    low: MoneyOut
    expected: MoneyOut
    high: MoneyOut


class Weekly(BaseModel):
    net: WeeklyNet
    collections_expected: MoneyOut
    payments_expected: MoneyOut
    purchases_expected: MoneyOut


class WeekOut(BaseModel):
    """One 7-day block (oldest first) for the coverage strip on SCR-O10."""

    start: date
    end: date
    has_records: bool
    net: MoneyOut | None


class ForecastOut(BaseModel):
    id: uuid.UUID
    status: str
    as_of_date: date
    method_version: str
    weeks_with_records: int
    window_weeks: int
    min_weeks_required: int
    weekly: Weekly | None
    horizons: dict
    weeks: list[WeekOut]
    is_stale: bool
    disclaimer_key: str = "forecast.estimate"
    created_at: datetime
