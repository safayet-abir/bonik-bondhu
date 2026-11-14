from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from .common import MoneyOut


class ScenarioOut(BaseModel):
    id: uuid.UUID
    scenario_type: str
    origin: str
    status: str
    parameters: dict
    result: dict | None
    news_event_id: uuid.UUID | None
    assumption_key: str
    label_key: str = "scn.whatif"


class AssessmentOut(BaseModel):
    """FR-ASM-01..09. Three statuses only; never approval language
    (FR-ASM-07). Terms inside are the owner's proposal, not a lender offer."""

    id: uuid.UUID
    financing_request_id: uuid.UUID
    activity_type: str
    status: str
    as_of_date: date
    engine_version: str
    forecast_run_id: uuid.UUID | None
    purpose_items_total: MoneyOut | None
    funding_gap: MoneyOut | None
    request_minus_gap: MoneyOut | None
    missing_items: list[str]
    flags: list[str]
    base_result: dict
    explanation: dict
    scenarios: list[ScenarioOut]
    news_signals: list[dict]
    inputs_sha256: str
    is_stale: bool
    disclaimer_key: str = "asm.not_approval"
    created_at: datetime
