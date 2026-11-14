"""Curated news (L1; DEC-15; Architecture §5.6, §7). Events are imported by
the admin CLI from `data/news/curated_news.csv` and only READ at request
time — no network calls. An empty table is a normal state (FR-NEWS-06).

Matching (SUG-37, resolves the §5.6 vs golden-D1 conflict):
  * location            — the profile's own area (upazila list if the event
                          has one, else district list)
  * supplier_location   — an active supplier's area, AND the event is
                          relevant to that supply: the event names no sector,
                          or names the shop's sector, or one of its
                          commodities is in the supplier's goods
  * sector / commodity  — on their own only for events without a location
                          (national news); for local events they are added
                          as extra reasons when a location already matched
Relevant window: published within 30 days before as_of (and not after it),
or an event date on/after as_of."""
from __future__ import annotations

import csv
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import BusinessProfile, FarmingSeason, NewsEvent, Supplier

EVENT_TYPES = ("flood_waterlogging", "market_fire", "hartal_road_blockade", "disease_outbreak", "price_shock",
               "policy_change", "factory_closure_layoffs", "market_eviction_relocation")
LOOKBACK_DAYS = 30
DEMO_SOURCE = "DEMO (fictional)"
CSV_COLUMNS = ("headline", "headline_lang", "summary", "source_name", "source_url", "published_date", "event_date",
               "event_type", "districts", "upazilas", "sectors", "commodities", "is_demo", "curated_by")
# Common spelling variants -> canonical (official current spellings). Team-maintained (Plan §7 common problems).
ALIASES = {
    "chittagong": "chattogram", "comilla": "cumilla", "barisal": "barishal", "jessore": "jashore",
    "bogra": "bogura", "chapai nawabganj": "chapainawabganj", "nawabganj": "chapainawabganj",
    "kaliakoir": "kaliakair", "dhamrae": "dhamrai", "saver": "savar", "ashulia": "savar",
}
# Farm inputs: a price shock on these is a cost rise for a farm (not on its own crop).
FARM_INPUT_WORDS = ("fertilizer", "fertiliser", "urea", "seed", "pesticide", "diesel", "fuel", "irrigation", "tsp",
                    "dap", "mop", "সার", "বীজ", "কীটনাশক", "ডিজেল")


def canon(value: str | None) -> str:
    if not value:
        return ""
    v = re.sub(r"\s+", " ", value).strip().casefold()
    v = re.sub(r"\s+(upazila|district|zila|sadar)$", "", v)
    return ALIASES.get(v, v)


def _canon_set(values: Iterable[str] | None) -> set[str]:
    return {c for c in (canon(v) for v in values or ()) if c}


def _words(text: str | None) -> set[str]:
    return {w for w in re.split(r"[,;/|]+|\s+and\s+|\s+", (text or "").casefold()) if w}


# --------------------------------------------------------------------------- matching
@dataclass
class Match:
    event: NewsEvent
    reasons: list[str] = field(default_factory=list)
    supplier: Supplier | None = None

    @property
    def corroboration(self) -> str:
        return "corroborated" if self.event.source_count >= 2 else "single_source"


def _in_area(event: NewsEvent, district: str | None, upazila: str | None) -> bool:
    if event.upazilas:
        return bool(upazila) and canon(upazila) in _canon_set(event.upazilas)
    return bool(district) and canon(district) in _canon_set(event.districts)


def _relevant_to_supplier(event: NewsEvent, category: str, supplier: Supplier) -> bool:
    sectors = _canon_set(event.sectors)
    if not sectors or category in sectors:
        return True
    goods = _words(supplier.goods_supplied)
    return any(_words(c) & goods for c in event.commodities or ())


def candidates(db: Session, as_of: date) -> list[NewsEvent]:
    return list(db.scalars(
        select(NewsEvent).where(
            NewsEvent.published_date <= as_of,
            or_(NewsEvent.published_date >= as_of - timedelta(days=LOOKBACK_DAYS), NewsEvent.event_date >= as_of))
        .order_by(NewsEvent.published_date.desc(), NewsEvent.id)))


def match(db: Session, profile: BusinessProfile, as_of: date,
          supplier_shares: dict[uuid.UUID, object] | None = None) -> list[Match]:
    """Events relevant to this profile with the reasons. With several
    matching suppliers the one with the largest known share is named."""
    events = candidates(db, as_of)
    if not events:
        return []
    category = canon(profile.business_category)
    suppliers = list(db.scalars(select(Supplier).where(Supplier.profile_id == profile.id,
                                                       Supplier.is_active.is_(True))
                                .order_by(Supplier.created_at)))
    shares = supplier_shares or {}
    suppliers.sort(key=lambda s: -(shares.get(s.id) or 0))
    crops: set[str] = set()
    if profile.activity_type == "crop_farm":
        crops = _canon_set(db.scalars(select(FarmingSeason.crop_name).where(
            FarmingSeason.profile_id == profile.id, FarmingSeason.status != "closed")))
    out: list[Match] = []
    for e in events:
        m = Match(e)
        local = bool(e.districts or e.upazilas)
        if local and _in_area(e, profile.district, profile.upazila):
            m.reasons.append("location")
        if local:
            for s in suppliers:
                if _in_area(e, s.district, s.upazila) and _relevant_to_supplier(e, category, s):
                    m.reasons.append("supplier_location")
                    m.supplier = s
                    break
        sector = bool(category) and category in _canon_set(e.sectors)
        # A farm buys inputs: a fertiliser/diesel price shock is relevant even though it is not its crop.
        commodity = bool(crops & _canon_set(e.commodities)) or (
            profile.activity_type == "crop_farm" and e.event_type == "price_shock" and is_farm_input_shock(e))
        if not local or m.reasons:
            if sector:
                m.reasons.append("sector")
            if commodity:
                m.reasons.append("commodity")
        if m.reasons:
            out.append(m)
    return out


def is_farm_input_shock(event: NewsEvent) -> bool:
    return any(w in " ".join(event.commodities or ()).casefold() for w in FARM_INPUT_WORDS)


# --------------------------------------------------------------------------- import (CLI only)
AUTO_CURATOR = "auto-news-search"  # curated_by of rows from the daily collector (SUG-45)


@dataclass
class ImportReport:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: list[tuple[int, str]] = field(default_factory=list)


def _split(v: str | None) -> list[str]:
    return [p.strip() for p in (v or "").split("|") if p.strip()]


def _date(v: str | None, name: str, required: bool) -> date | None:
    v = (v or "").strip()
    if not v:
        if required:
            raise ValueError(f"{name} is required")
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise ValueError(f"{name} must be YYYY-MM-DD") from None


def validate_row(row: dict[str, str], today: date) -> dict:
    """One CSV row -> clean values, or ValueError with a plain reason."""
    g = {k: (row.get(k) or "").strip() for k in CSV_COLUMNS}
    if not 5 <= len(g["headline"]) <= 300:
        raise ValueError("headline must be 5–300 characters")
    if g["headline_lang"] not in ("bn", "en"):
        raise ValueError("headline_lang must be bn or en")
    if len(g["summary"]) > 500:
        raise ValueError("summary must be ≤ 500 characters (a short team-written summary, never article text)")
    if g["event_type"] not in EVENT_TYPES:
        raise ValueError(f"event_type must be one of {', '.join(EVENT_TYPES)}")
    is_demo = g["is_demo"].casefold() in ("true", "1", "yes")
    if is_demo:
        if g["source_name"] != DEMO_SOURCE:
            raise ValueError(f"DEMO rows must have source_name '{DEMO_SOURCE}'")
    else:
        if not g["source_name"]:
            raise ValueError("source_name is required")
        if not re.match(r"^https?://\S+$", g["source_url"]):
            raise ValueError("source_url (http/https) is required for real news")
    if not g["curated_by"]:
        raise ValueError("curated_by is required")
    published = _date(g["published_date"], "published_date", True)
    event_date = _date(g["event_date"], "event_date", False)
    if published > today:
        raise ValueError("published_date is in the future")
    districts = _split(g["districts"])
    key_date = event_date or published
    dedup = (row.get("dedup_key") or "").strip() or \
        f"{g['event_type']}-{canon(districts[0]) if districts else 'national'}-{key_date.isoformat()}".replace(" ", "_")
    return {
        "headline": g["headline"], "headline_lang": g["headline_lang"], "summary": g["summary"] or None,
        "source_name": g["source_name"], "source_url": g["source_url"] or None, "published_date": published,
        "event_date": event_date, "event_type": g["event_type"], "districts": districts,
        "upazilas": _split(g["upazilas"]), "sectors": [s.casefold() for s in _split(g["sectors"])],
        "commodities": [c.casefold() for c in _split(g["commodities"])], "is_demo": is_demo,
        "curated_by": g["curated_by"], "dedup_key": dedup,
    }


def import_csv(db: Session, path: Path, today: date) -> ImportReport:
    """Validate every row; rows sharing a dedup_key are one event reported by
    several sources (source_count = distinct sources; the first row is the
    primary). Upsert by dedup_key; re-importing the same file is idempotent."""
    report = ImportReport()
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in CSV_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            report.rejected.append((1, f"missing columns: {', '.join(missing)}"))
            return report
        for line, row in enumerate(reader, start=2):
            try:
                rows.append(validate_row(row, today))
            except ValueError as exc:
                report.rejected.append((line, str(exc)))
    return import_rows(db, rows, report)


def import_rows(db: Session, clean_rows: list[dict], report: ImportReport | None = None) -> ImportReport:
    """Upsert validated rows grouped by dedup_key. An automatically collected
    row never overwrites an event a person curated."""
    report = report or ImportReport()
    groups: dict[str, list[dict]] = {}
    for clean in clean_rows:
        groups.setdefault(clean["dedup_key"], []).append(clean)
    for key, rows in groups.items():
        primary = rows[0]
        sources = {(r["source_url"] or r["source_name"]).casefold() for r in rows}
        existing = db.scalar(select(NewsEvent).where(NewsEvent.dedup_key == key))
        if existing is None:
            db.add(NewsEvent(**primary, source_count=len(sources)))
            report.inserted += 1
        elif primary["curated_by"] == AUTO_CURATOR and existing.curated_by != AUTO_CURATOR:
            report.skipped += 1
        else:
            for k, v in primary.items():
                setattr(existing, k, v)
            existing.source_count = max(existing.source_count, len(sources))
            report.updated += 1
    db.flush()
    return report
