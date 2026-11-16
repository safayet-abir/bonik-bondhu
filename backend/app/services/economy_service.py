"""Economy context from World Bank Open Data (Plan Ultra F2; SUG-58).

Yearly national figures for Bangladesh — shown with their year and source, never called "live". Kept in
memory: starts from the committed snapshot `app/data/worldbank_bgd.json`, refreshed by the daily background
job (never inside a request); a failed refresh keeps the last values. Nothing is stored in the database.

The inflation what-if is deterministic code on the same inputs as the assessment and never changes the
status (DEC-30)."""
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from ..models import BusinessProfile, FinancingRequest
from . import assessment_service, scenario_service

log = logging.getLogger("bonik.economy")
SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "worldbank_bgd.json"
API = "https://api.worldbank.org/v2/country/BGD/indicator/{code}"
SOURCE = {"name": "World Bank Open Data", "url": "https://data.worldbank.org/country/bangladesh"}
INDICATORS = {  # code -> key used by the screens
    "FP.CPI.TOTL.ZG": "inflation",
    "FR.INR.LEND": "lending_rate",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "FS.AST.PRVT.GD.ZS": "private_credit",
}
HORIZON_DAYS = 90
_cache: dict | None = None


def context() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return _cache


def collect(client: httpx.Client) -> dict:
    """Latest non-empty value of each indicator; an indicator that fails keeps its previous value."""
    old = {i["code"]: i for i in context()["indicators"]} if SNAPSHOT.is_file() else {}
    out = []
    for code, key in INDICATORS.items():
        try:
            r = client.get(API.format(code=code), params={"format": "json", "mrnev": 1})
            r.raise_for_status()
            row = r.json()[1][0]
            out.append({"code": code, "key": key, "label": row["indicator"]["value"], "year": int(row["date"]),
                        "value": f"{Decimal(str(row['value'])):.1f}"})
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            log.warning("world bank indicator failed", extra={"indicator": code})
            if code in old:
                out.append(old[code])
    return {"source": SOURCE, "country": "Bangladesh", "indicators": out}


def refresh() -> None:
    """Background job only (daily, next to the news fetch)."""
    global _cache
    with httpx.Client(timeout=20, headers={"User-Agent": "BonikBondhu-economy/1.0"}) as client:
        _cache = collect(client)


def indicator(key: str) -> dict | None:
    return next((i for i in context()["indicators"] if i["key"] == key), None)


def inflation_whatif(db: Session, profile: BusinessProfile, r: FinancingRequest, as_of: date) -> dict | None:
    """What if prices keep rising at last year's inflation? Shop: every purchase costs the yearly rate
    pro-rated to the 90-day check window more, for the whole window (cautious). Farm: the season's remaining
    costs rise by the rate pro-rated to the days left until harvest. None when the check cannot run yet."""
    infl = indicator("inflation")
    ev = assessment_service.evaluate(db, profile, r, as_of)
    if infl is None or ev.missing or not ev.extra:
        return None
    rate = Decimal(infl["value"]) / 100
    if "shop_inputs" in ev.extra:
        days = HORIZON_DAYS
        params = {"share": "1", "pct": str((rate * days / 365).quantize(Decimal("0.0001")))}
    else:
        days = max(0, min(365, (ev.extra["crop_inputs"]["harvest"] - as_of).days))
        params = {"pct": str((rate * days / 365).quantize(Decimal("0.0001")))}
    result, _ = scenario_service.compute("input_price_rise", params, ev.extra)
    return {"inflation_pct": infl["value"], "inflation_year": infl["year"], "days": days,
            "price_rise_pct": f"{Decimal(params['pct']) * 100:.1f}", "result": result,
            "base_status": ev.status, "label": "what-if only — does not change your result"}
