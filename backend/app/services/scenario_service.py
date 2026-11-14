"""What-if scenarios (FR-SCN-01..04, FR-NEWS-04; Architecture §5.5; SUG-09/12).

DEC-30: a scenario NEVER changes the assessment status. A shortfall in a
scenario only adds a flag (`scenario_shortfall`, or `pre_harvest_cash_shortfall`
for a farm whose money runs out before harvest).

* auto scenarios are computed when the assessment runs (only when the base
  case could be computed — there is nothing to stress otherwise);
* news scenarios start `proposed`; the owner confirms (computed) or
  dismisses. Confirming re-evaluates the SAME inputs (the stored
  inputs_sha256 must still match), so the result is reproducible."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.clock import utcnow
from ..core.errors import AppError, not_found
from ..engine.concentration import scenario_share
from ..engine.crop import crop_check
from ..engine.money import money
from ..engine.projection import Scenario, shop_due_date_checks
from ..models import BusinessProfile, FinancialAssessment, NewsEvent, RiskScenario
from . import news_service, supplier_service

DELAY_DAYS = (7, 14)                 # S1 L2 "7 or 14-day" (CON-01)
PRICE_RISE = Decimal("0.15")         # SUG-09 / S1 L2 example
HARVEST_PRICE_FALL = Decimal("0.15")  # SUG-12
YIELD_SHORTFALL = Decimal("0.20")    # SUG-12
NEWS_DELAY_DAYS = 7                  # SUG-12 mapping
SUPPLY_EVENTS = ("hartal_road_blockade", "flood_waterlogging", "market_fire")


def _s(x: Decimal) -> str:
    return f"{money(x):.2f}"


# --------------------------------------------------------------------------- pure computation
def compute(kind: str, params: dict, extra: dict) -> tuple[dict, set[str]]:
    """Run one scenario on the evaluation inputs; returns (result, flags)."""
    if "shop_inputs" in extra:
        i = extra["shop_inputs"]
        if kind == "supplier_delay":
            sc = Scenario("supplier_delay", Decimal(params["share"]), int(params["days"]),
                          date.fromisoformat(params["start"]))
        elif kind == "input_price_rise":
            sc = Scenario("input_price_rise", Decimal(params["share"]), pct=Decimal(params["pct"]))
        else:
            raise ValueError(kind)
        c = shop_due_date_checks(i["as_of"], i["baseline"], i["start"], i["reserve"], i["household"],
                                 i["existing"], i["new_rows"], sc)
        fs = c["first_shortfall"]
        result = {
            "kind": "shop_due_dates", "any_shortfall": c["any_shortfall"], "covered": not c["any_shortfall"],
            "checks_count": len(c["checks"]), "min_balance_after_payment": c["min_balance_after_payment"],
            "first_shortfall": {k: fs[k] for k in ("date", "balance_after", "shortfall_vs_reserve")} if fs else None,
        }
        return result, ({"scenario_shortfall"} if c["any_shortfall"] else set())
    i = extra["crop_inputs"]
    pct = Decimal(params["pct"])
    factors = {"harvest_price_fall": {"price_factor": 1 - pct}, "yield_shortfall": {"yield_factor": 1 - pct},
               "input_price_rise": {"cost_factor": 1 + pct}}[kind]
    c = crop_check(i["output_low"], i["price_low"], i["output_exp"], i["total_planned_costs"], i["remaining"],
                   i["start"], i["debts_due"], i["reserve"], i["repayment"], i["harvest"], i["due"],
                   household_to_harvest=i["hh_to_harvest"], household_after_harvest=i["hh_after"], **factors)
    result = {"kind": "crop_harvest", **{k: (v if isinstance(v, bool) else _s(v)) for k, v in c.items()}}
    flags = set()
    if not c["covered"]:
        flags.add("scenario_shortfall")
    if c["pre_harvest_shortfall"] > 0:
        flags.add("pre_harvest_cash_shortfall")
    return result, flags


# --------------------------------------------------------------------------- at assessment time
def _add(db: Session, profile: BusinessProfile, a: FinancialAssessment, kind: str, origin: str, params: dict,
         extra: dict, *, supplier_id=None, news_event_id=None, proposed=False) -> set[str]:
    result, flags = (None, set()) if proposed else compute(kind, params, extra)
    db.add(RiskScenario(profile_id=profile.id, assessment_id=a.id, scenario_type=kind, origin=origin,
                        news_event_id=news_event_id, supplier_id=supplier_id, parameters=params,
                        status="proposed" if proposed else "computed", result=result))
    return flags


def create_for_assessment(db: Session, profile: BusinessProfile, a: FinancialAssessment, extra: dict,
                          as_of: date) -> set[str]:
    """Auto scenarios + news proposals. Returns flags to add (never a status)."""
    flags: set[str] = set()
    conc = supplier_service.concentration(db, profile, as_of)
    if "shop_inputs" in extra:
        top = conc.top_supplier
        if top is not None:
            share = str(scenario_share(conc.result.top_share))
            for days in DELAY_DAYS:
                flags |= _add(db, profile, a, "supplier_delay", "auto",
                              {"days": days, "share": share, "start": as_of.isoformat(), "basis": conc.basis},
                              extra, supplier_id=top.id)
            flags |= _add(db, profile, a, "input_price_rise", "auto",
                          {"pct": str(PRICE_RISE), "share": share, "basis": conc.basis}, extra, supplier_id=top.id)
    elif "crop_inputs" in extra:
        for kind, pct in (("harvest_price_fall", HARVEST_PRICE_FALL), ("yield_shortfall", YIELD_SHORTFALL),
                          ("input_price_rise", PRICE_RISE)):
            flags |= _add(db, profile, a, kind, "auto", {"pct": str(pct)}, extra)
    else:
        return flags  # base case not computable -> nothing to stress, no proposals
    for m in news_service.match(db, profile, as_of, conc.result.shares):
        proposal = news_proposal(m, profile, conc, as_of)
        if proposal:
            kind, params, supplier_id = proposal
            _add(db, profile, a, kind, "news", params, extra, supplier_id=supplier_id, news_event_id=m.event.id,
                 proposed=True)
    return flags


def news_proposal(m: news_service.Match, profile: BusinessProfile, conc: supplier_service.SupplierConcentration,
                  as_of: date) -> tuple[str, dict, uuid.UUID | None] | None:
    """SUG-12 mapping. Events that cannot be turned into a computable
    scenario stay signals only (shown, never silently converted)."""
    e = m.event
    shop = profile.activity_type == "shop"
    if shop and e.event_type in SUPPLY_EVENTS and "supplier_location" in m.reasons and m.supplier:
        share = conc.share_of(m.supplier.id)
        if share:
            start = max(e.event_date or as_of, as_of)  # Plan §7: a start in the past defaults to as_of
            return "supplier_delay", {"days": NEWS_DELAY_DAYS, "share": str(scenario_share(share)),
                                      "start": start.isoformat(), "basis": conc.basis}, m.supplier.id
    if e.event_type == "price_shock":
        if shop and conc.top_supplier is not None:
            return "input_price_rise", {"pct": str(PRICE_RISE), "share": str(scenario_share(conc.result.top_share)),
                                        "basis": conc.basis}, conc.top_supplier.id
        if not shop and news_service.is_farm_input_shock(e):
            return "input_price_rise", {"pct": str(PRICE_RISE)}, None
    if not shop and e.event_type == "flood_waterlogging" and "location" in m.reasons:
        return "yield_shortfall", {"pct": str(YIELD_SHORTFALL)}, None
    return None


# --------------------------------------------------------------------------- confirm / dismiss
def get(db: Session, profile: BusinessProfile, scid: uuid.UUID) -> RiskScenario:
    s = db.scalar(select(RiskScenario).where(RiskScenario.profile_id == profile.id, RiskScenario.id == scid))
    if s is None:
        raise not_found()
    return s


def _proposed(s: RiskScenario) -> None:
    if s.origin != "news" or s.status != "proposed":
        raise AppError("CONFLICT", 409, "scn.err.not_proposed")


def confirm(db: Session, profile: BusinessProfile, scid: uuid.UUID) -> RiskScenario:
    from . import assessment_service, financing_service  # local: assessment_service imports this module

    s = get(db, profile, scid)
    _proposed(s)
    a = assessment_service.get(db, profile, s.assessment_id)
    stale = AppError("ASSESSMENT_STALE", 409, "asm.err.stale")
    if a.profile_data_version != profile.data_version:
        raise stale
    r = financing_service.get(db, profile, a.financing_request_id)
    ev = assessment_service.evaluate(db, profile, r, a.as_of_date)
    if assessment_service.inputs_hash(ev.inputs) != a.inputs_sha256:
        raise stale
    result, flags = compute(s.scenario_type, s.parameters, ev.extra)
    s.result, s.status, s.resolved_at = result, "computed", utcnow()
    event = db.get(NewsEvent, s.news_event_id)
    if event is not None and event.source_count < 2:
        flags.add("news_signal_single_source")
    if flags - set(a.flags):
        a.flags = assessment_service.ordered_flags(set(a.flags) | flags)  # flags only; status untouched (DEC-30)
    db.flush()
    return s


def dismiss(db: Session, profile: BusinessProfile, scid: uuid.UUID) -> RiskScenario:
    s = get(db, profile, scid)
    _proposed(s)
    s.status, s.resolved_at = "dismissed", utcnow()
    db.flush()
    return s
