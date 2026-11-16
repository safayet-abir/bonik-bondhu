"""Deterministic financing assessment (FR-ASM-01..09; Architecture §5.2–5.4).

Three statuses only — `insufficient_information`, `not_affordable_base_case`,
`ready_for_lender_review`. This is NOT a lending decision, a score or a
probability: the lender decides. Missing information always produces
`insufficient_information` with a fix list, never a guessed positive.
Scenarios (P4) are what-if only and never change the status (DEC-30)."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.errors import not_found
from ..engine import baseline as bl
from ..engine import schedule_search
from ..engine.crop import crop_check
from ..engine.funding import Gap, funding_gap
from ..engine.money import ZERO, money
from ..engine.projection import DAYS_PER_YEAR, household_daily, shop_due_date_checks
from ..engine.schedules import HORIZON_DAYS, horizon_end
from ..models import (
    BusinessProfile, FarmingSeason, FinancialAssessment, FinancingRequest, FinancingRequestItem, RiskScenario,
    SeasonCostItem,
)
from ..schemas.assessment import AssessmentOut, ScenarioOut
from . import debt_service, financing_service, forecast_service, news_service, scenario_service, supplier_service
from .season_service import _paid_by_item

ENGINE_VERSION = "assess-v1"

MISSING_ORDER = (
    "debts_not_declared", "household_withdrawal_not_declared", "purpose_items_missing", "gap_inputs_missing",
    "terms_incomplete", "forecast_insufficient_history", "term_beyond_forecast_horizon", "season_incomplete",
    "repayment_due_before_expected_harvest", "profile_location_missing",
)
FLAG_ORDER = (
    "request_exceeds_gap", "over_request_explained", "weak_price_evidence", "high_supplier_dependency",
    "scenario_shortfall", "pre_harvest_cash_shortfall", "starting_cash_unknown", "reserve_zero",
    "interest_fees_unknown", "existing_debt_overdue", "existing_debt_dates_outdated", "news_signal_single_source",
)
SEASON_FIELDS = ("expected_output_low", "expected_output_expected", "expected_price_low")


def _s(x: Decimal | None) -> str | None:
    return None if x is None else f"{money(x):.2f}"


def _ordered(codes: set[str], order: tuple[str, ...]) -> list[str]:
    return [c for c in order if c in codes]


def ordered_flags(codes: set[str]) -> list[str]:
    return _ordered(codes, FLAG_ORDER)


@dataclass
class Evaluation:
    status: str
    missing: list[str]
    flags: list[str]
    gap: Gap | None
    base_result: dict
    explanation: dict
    inputs: dict
    baseline: bl.Baseline | None = None
    extra: dict = field(default_factory=dict)


def start_balance(r: FinancingRequest) -> Decimal:
    """DEC-35: max(0, current cash − cash already committed to the purchase);
    unknown current cash → 0 (flag `starting_cash_unknown`)."""
    if r.current_cash_balance is None:
        return ZERO
    return max(ZERO, r.current_cash_balance - (r.cash_safely_available or ZERO))


def _season(db: Session, profile: BusinessProfile, r: FinancingRequest) -> FarmingSeason | None:
    if r.season_id is None:
        return None
    return db.scalar(select(FarmingSeason).where(FarmingSeason.profile_id == profile.id,
                                                 FarmingSeason.id == r.season_id))


def _formula(key: str, expr: str, values: str) -> dict:
    return {"key": key, "expr": expr, "values": values}


# --------------------------------------------------------------------------- evaluation
def evaluate(db: Session, profile: BusinessProfile, r: FinancingRequest, as_of: date) -> Evaluation:
    is_farm = profile.activity_type == "crop_farm"
    all_items = financing_service.list_items(db, profile, r)
    items = financing_service.counted_items(all_items)
    missing: set[str] = set()
    flags: set[str] = set()

    if not debt_service.debts_declared(db, profile):
        missing.add("debts_not_declared")
    if profile.household_declared_at is None:
        missing.add("household_withdrawal_not_declared")
    if not items:
        missing.add("purpose_items_missing")
    if not financing_service.gap_inputs_complete(r):
        missing.add("gap_inputs_missing")
    terms_ok = financing_service.terms_complete(r, as_of)
    if not terms_ok:
        missing.add("terms_incomplete")
    new_rows = financing_service.new_schedule(r) if terms_ok else []
    if not (profile.district and profile.upazila):
        missing.add("profile_location_missing")

    baseline = None
    season = None
    if is_farm:
        season = _season(db, profile, r)
        if season is None or any(getattr(season, n) is None for n in SEASON_FIELDS):
            missing.add("season_incomplete")
        elif new_rows and season.expected_harvest_date > new_rows[0][0]:
            missing.add("repayment_due_before_expected_harvest")
    else:
        baseline = forecast_service.compute(db, profile, as_of)
        if not baseline.ok:
            missing.add("forecast_insufficient_history")
        if new_rows and any(d > horizon_end(as_of) for d, _ in new_rows):
            missing.add("term_beyond_forecast_horizon")

    gap = None
    if items and financing_service.gap_inputs_complete(r):
        gap = funding_gap([(i.quantity, i.unit_price) for i in items], r.associated_expenses,
                          r.liquidity_buffer, r.cash_safely_available, r.committed_financing, r.requested_amount)
        if gap.exceeds:
            flags.add("over_request_explained" if r.over_request_explanation else "request_exceeds_gap")
    if items and all(i.price_source_type == "owner_estimate" for i in items):
        flags.add("weak_price_evidence")
    if r.current_cash_balance is None:
        flags.add("starting_cash_unknown")
    if r.minimum_cash_reserve is not None and r.minimum_cash_reserve == 0:
        flags.add("reserve_zero")
    if r.interest_fees_unknown:
        flags.add("interest_fees_unknown")
    flags.update(debt_service.obligation_flags(db, profile, as_of))
    conc = supplier_service.concentration(db, profile, as_of)
    if conc.result.high_dependency:
        flags.add("high_supplier_dependency")

    start = start_balance(r)
    reserve = r.minimum_cash_reserve or ZERO
    household = profile.household_withdrawal_monthly or ZERO
    base_result: dict = {}
    status = "insufficient_information"
    extra: dict = {}
    if not missing:
        if is_farm:
            base_result, extra = _farm_check(db, profile, r, season, items, new_rows, as_of, start, reserve, household)
            if Decimal(base_result["pre_harvest_shortfall"]) > 0:
                flags.add("pre_harvest_cash_shortfall")
            affordable = base_result["covered"] and Decimal(base_result["pre_harvest_shortfall"]) == 0
        else:
            existing = debt_service.obligation_rows(db, profile, as_of, horizon_end(as_of))
            check = shop_due_date_checks(as_of, baseline, start, reserve, household, existing, new_rows)
            extra = {"shop_inputs": dict(as_of=as_of, baseline=baseline, start=start, reserve=reserve,
                                         household=household, existing=existing, new_rows=new_rows)}
            base_result = {
                "kind": "shop_due_dates", "start_balance": _s(start), "reserve": _s(reserve),
                "household_monthly": _s(household), "daily_net_low": _s(baseline.net_weekly_low / 7),
                "household_daily": _s(household_daily(household)),
                "horizon_end": horizon_end(as_of).isoformat(), **check,
            }
            affordable = not check["any_shortfall"]
        status = "ready_for_lender_review" if affordable else "not_affordable_base_case"

    inputs = _inputs(db, profile, r, all_items, baseline, season, as_of)
    inputs["supplier_shares"] = {"basis": conc.basis,
                                 "shares": {str(k): str(v) for k, v in sorted(conc.result.shares.items(),
                                                                               key=lambda kv: str(kv[0]))}}
    explanation = _explain(profile, r, items, gap, baseline, base_result, new_rows, start, reserve, household, as_of)
    return Evaluation(status=status, missing=_ordered(missing, MISSING_ORDER), flags=_ordered(flags, FLAG_ORDER),
                      gap=gap, base_result=base_result, explanation=explanation, inputs=inputs, baseline=baseline,
                      extra=extra)


def _farm_check(db: Session, profile: BusinessProfile, r: FinancingRequest, season: FarmingSeason,
                items: list[FinancingRequestItem], new_rows, as_of: date, start: Decimal, reserve: Decimal,
                household: Decimal) -> tuple[dict, dict]:
    """Harvest-time check (Architecture §5.4). With equal installments every
    payment must fall on/after harvest; the last due date is the binding
    check because no farm income arrives after harvest."""
    due = new_rows[-1][0]
    repayment = sum((a for _, a in new_rows), ZERO)
    cost_items = list(db.scalars(select(SeasonCostItem).where(
        SeasonCostItem.profile_id == profile.id, SeasonCostItem.season_id == season.id)))
    paid = _paid_by_item(db, profile, cost_items)
    in_request = {i.source_season_cost_item_id for i in items if i.source_season_cost_item_id}
    remaining = sum((max(ZERO, c.total_cost - paid.get(c.id, ZERO)) for c in cost_items if c.id not in in_request),
                    ZERO)
    planned = sum((c.total_cost for c in cost_items), ZERO)
    debts = debt_service.obligation_rows(db, profile, as_of, due)
    debts_due = sum((a for _, rows in debts for d, a in rows if d <= due), ZERO)
    harvest = season.expected_harvest_date
    hh = household_daily(household)
    hh_to_harvest = hh * max(0, (harvest - as_of).days)
    hh_after = hh * max(0, (due - max(harvest, as_of)).days)
    c = crop_check(season.expected_output_low, season.expected_price_low, season.expected_output_expected, planned,
                   remaining, start, debts_due, reserve, repayment, harvest, due,
                   household_to_harvest=hh_to_harvest, household_after_harvest=hh_after)
    result = {
        "kind": "crop_harvest", "start_balance": _s(start), "reserve": _s(reserve),
        "expected_harvest_date": harvest.isoformat(), "due_date": due.isoformat(),
        "first_due_date": new_rows[0][0].isoformat(), "installments": len(new_rows),
        "output_low": _s(season.expected_output_low), "price_low": _s(season.expected_price_low),
        "remaining_costs_outside_request": _s(remaining), "total_planned_costs": _s(planned),
        "debts_due_by_due_date": _s(debts_due), "household_until_due": _s(hh_to_harvest + hh_after),
        **{k: (v if isinstance(v, bool) else _s(v)) for k, v in c.items()},
    }
    return result, {"crop_inputs": dict(output_low=season.expected_output_low, price_low=season.expected_price_low,
                                         output_exp=season.expected_output_expected, total_planned_costs=planned,
                                         remaining=remaining, start=start, debts_due=debts_due, reserve=reserve,
                                         repayment=repayment, harvest=harvest, due=due,
                                         hh_to_harvest=hh_to_harvest, hh_after=hh_after)}


# --------------------------------------------------------------------------- Repayment Fit Finder (SUG-56)
# Missing items that are about the schedule itself: the finder exists to fix exactly these.
FIT_IGNORES = {"terms_incomplete", "term_beyond_forecast_horizon", "repayment_due_before_expected_harvest"}


def schedule_options(db: Session, profile: BusinessProfile, r: FinancingRequest, as_of: date) -> dict:
    """Read-only. Tries candidate schedules through the SAME checks `evaluate` uses and returns up to three
    that fit. Nothing is saved; the owner copies one into their own proposal (DEC-28 stays)."""
    ev = evaluate(db, profile, r, as_of)
    blocked = [m for m in ev.missing if m not in FIT_IGNORES]
    interest = r.interest_fees_total or ZERO
    reserve = r.minimum_cash_reserve or ZERO
    is_farm = profile.activity_type == "crop_farm"
    out = {"as_of_date": as_of.isoformat(), "blocked_by": blocked, "options": [], "closest": None, "tried": 0,
           "fit_count": 0, "requested_amount": _s(r.requested_amount), "interest_fees_counted": _s(interest),
           "reserve_counted": _s(reserve),
           "margin_kind": "surplus_at_due_date" if is_farm else "lowest_balance_above_reserve"}
    if blocked:
        return out
    start = start_balance(r)
    household = profile.household_withdrawal_monthly or ZERO
    if is_farm:
        season = _season(db, profile, r)
        items = financing_service.counted_items(financing_service.list_items(db, profile, r))
        candidates = schedule_search.farm_candidates(as_of, season.expected_harvest_date)

        def check(rows):
            res, _ = _farm_check(db, profile, r, season, items, list(rows), as_of, start, reserve, household)
            surplus, pre = Decimal(res["surplus_or_shortfall"]), Decimal(res["pre_harvest_shortfall"])
            return res["covered"] and pre == 0, surplus, max(-surplus, pre, ZERO)
    else:
        existing = debt_service.obligation_rows(db, profile, as_of, horizon_end(as_of))
        candidates = schedule_search.shop_candidates(as_of)

        def check(rows):
            c = shop_due_date_checks(as_of, ev.baseline, start, reserve, household, existing, rows)
            worst = max((Decimal(x["shortfall_vs_reserve"]) for x in c["checks"]), default=ZERO)
            return (not c["any_shortfall"] and not c["beyond_horizon"],
                    Decimal(c["min_balance_after_payment"]) - reserve, worst)

    results = schedule_search.search(r.requested_amount, interest, candidates, check)
    chosen, closest = schedule_search.pick(results)

    def row(label: str, x: schedule_search.Result) -> dict:
        kind, n, freq, first = x.candidate
        return {"label": label, "schedule_type": kind, "installment_count": n if kind == "equal_installments" else None,
                "installment_frequency": freq if kind == "equal_installments" else None,
                "first_due_date": first.isoformat(), "last_due_date": x.last_due.isoformat(),
                "installment_amount": _s(x.rows[0][1]), "total_repayment": _s(sum((a for _, a in x.rows), ZERO)),
                "margin": _s(x.margin), "shortfall": _s(x.shortfall)}

    out.update(tried=len(results), fit_count=sum(x.fits for x in results),
               options=[row(label, x) for label, x in chosen],
               closest=row("closest", closest) if closest is not None else None)
    return out


def _inputs(db: Session, profile: BusinessProfile, r: FinancingRequest, items, baseline, season, as_of) -> dict:
    """Everything the result depends on, as plain strings — hashed into
    `inputs_sha256` so two runs on the same inputs are provably the same."""
    debts = [{k: str(getattr(d, k)) for k in ("lender_type", "outstanding_balance", "installment_amount",
                                              "installment_frequency", "next_due_date", "is_overdue",
                                              "overdue_amount", "status")}
             for d in debt_service.list_debts(db, profile)]
    req = {k: (None if (v := getattr(r, k)) is None else str(v)) for k in financing_service.PATCHABLE}
    req.pop("purpose_text")  # free text does not change any number
    return {
        "engine_version": ENGINE_VERSION, "as_of": as_of.isoformat(), "activity_type": profile.activity_type,
        "household_withdrawal_monthly": str(profile.household_withdrawal_monthly),
        "household_declared": profile.household_declared_at is not None,
        "no_debt_declared": profile.no_debt_declared_at is not None,
        "location": [profile.district, profile.upazila], "request": req, "debts": debts,
        "items": [[str(i.quantity), str(i.unit_price), i.price_source_type, i.confirmed,
                   str(i.source_season_cost_item_id)] for i in items],
        "weeks": [[w.start.isoformat(), w.has_records, str(w.collections), str(w.payments), str(w.purchases)]
                  for w in baseline.blocks] if baseline else None,
        "season": {k: str(getattr(season, k)) for k in (*SEASON_FIELDS, "expected_harvest_date", "updated_at")}
        if season else None,
    }


def inputs_hash(inputs: dict) -> str:
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _explain(profile, r, items, gap, baseline, base_result, new_rows, start, reserve, household, as_of) -> dict:
    """FR-ASM-08 "How we calculated": formulas with the actual numbers and
    every input with where it came from (declared / records / proposal)."""
    s = get_settings()
    formulas = []
    if gap is not None:
        formulas.append(_formula(
            "formula.funding_gap",
            "funding_gap = max(0, items + associated_expenses + buffer − cash_safely_available − committed_financing)",
            f"max(0, {_s(gap.items_total)} + {_s(r.associated_expenses)} + {_s(r.liquidity_buffer)} − "
            f"{_s(r.cash_safely_available)} − {_s(r.committed_financing)}) = {_s(gap.funding_gap)}"))
        formulas.append(_formula("formula.request_minus_gap", "request − funding_gap",
                                 f"{_s(r.requested_amount)} − {_s(gap.funding_gap)} = {_s(gap.request_minus_gap)}"))
    formulas.append(_formula("formula.start_balance", "start = max(0, current_cash − cash_safely_available)",
                             "unknown → 0" if r.current_cash_balance is None else
                             f"max(0, {_s(r.current_cash_balance)} − {_s(r.cash_safely_available or ZERO)}) = "
                             f"{_s(start)}"))
    if profile.activity_type == "shop" and baseline is not None and baseline.ok:
        formulas.append(_formula(
            "formula.daily_change", "daily = weekly_net_low ÷ 7 − household_monthly × 12 ÷ 365",
            f"{_s(baseline.net_weekly_low)} ÷ 7 − {_s(household)} × 12 ÷ {DAYS_PER_YEAR} = "
            f"{_s(baseline.net_weekly_low / 7 - household_daily(household))}"))
        formulas.append(_formula("formula.due_date_check",
                                 "on each due date: balance after all payments ≥ minimum reserve", f"reserve {_s(reserve)}"))
    if base_result.get("kind") == "crop_harvest":
        b = base_result
        formulas += [
            _formula("formula.income_low", "income_low = output_low × price_low",
                     f"{b['output_low']} × {b['price_low']} = {b['income_low']}"),
            _formula("formula.pre_harvest", "pre_harvest = start − remaining_costs − household_to_harvest",
                     f"= {b['pre_harvest_balance']}"),
            _formula("formula.available_at_due",
                     "available = pre_harvest + income_low − household_after_harvest − debts_due − reserve",
                     f"= {b['available_at_due_date']} (repayment {b['repayment_due']})"),
            _formula("formula.break_even", "break_even = planned_costs ÷ output_expected",
                     f"= {b['break_even_price_per_unit']} Tk/kg"),
            _formula("formula.loan_cover", "loan_cover = (repayment + debts_due + reserve + remaining + household − "
                     "start) ÷ output_low", f"= {b['loan_cover_price_per_unit']} Tk/kg"),
        ]
    sources = []

    def inp(name: str, value, source: str) -> None:
        sources.append({"name": name, "value": value if isinstance(value, (str, int, bool)) or value is None
                        else _s(value), "source": source})

    inp("household_withdrawal_monthly", profile.household_withdrawal_monthly,
        "declared" if profile.household_declared_at else "missing")
    inp("current_cash_balance", r.current_cash_balance, "declared" if r.current_cash_balance is not None else "unknown")
    for n in financing_service.GAP_INPUTS:
        inp(n, getattr(r, n), "declared" if getattr(r, n) is not None else "missing")
    inp("minimum_cash_reserve", r.minimum_cash_reserve, "owner_proposal")
    inp("interest_fees_total", r.interest_fees_total, "unknown" if r.interest_fees_unknown else "owner_proposal")
    price_sources = sorted({i.price_source_type for i in items})
    inp("purpose_items", len(items), "price:" + ",".join(price_sources) if price_sources else "missing")
    if baseline is not None:
        inp("weeks_with_records", baseline.weeks_used, "records")
        if baseline.ok:
            inp("weekly_net_low", baseline.net_weekly_low, "records")
    rows = new_rows
    proposal = {
        "requested_amount": _s(r.requested_amount),
        "schedule_type": r.schedule_type, "installment_count": r.installment_count,
        "frequency": r.installment_frequency, "first_due_date": rows[0][0].isoformat() if rows else None,
        "last_due_date": rows[-1][0].isoformat() if rows else None,
        "interest_fees_total": _s(r.interest_fees_total), "interest_fees_unknown": r.interest_fees_unknown,
        "repayment_total": _s(sum((a for _, a in rows), ZERO)) if rows else None,
        "installments": [{"due_date": d.isoformat(), "amount": _s(a)} for d, a in rows],
        "label": "owner_proposal_not_lender_offer",
    }
    return {
        "formulas": formulas, "inputs": sources, "proposal": proposal,
        "parameters": {"forecast_window_weeks": s.FORECAST_WINDOW_WEEKS, "min_weeks": s.FORECAST_MIN_WEEKS,
                       "horizon_days": HORIZON_DAYS, "days_per_year": int(DAYS_PER_YEAR),
                       "over_request_tolerance_pct": 0, "case": "low"},
        "excluded": ["loan_disbursement", "purpose_spending"],
    }


# --------------------------------------------------------------------------- persistence
def run(db: Session, profile: BusinessProfile, rid: uuid.UUID, as_of: date) -> FinancialAssessment:
    r = financing_service.get(db, profile, rid)
    ev = evaluate(db, profile, r, as_of)
    forecast_run_id = None
    if profile.activity_type == "shop":
        last = forecast_service.latest(db, profile)
        if last is None or last.as_of_date != as_of or forecast_service.is_stale(last, profile):
            last = forecast_service.create_run(db, profile, as_of, ev.baseline)
        forecast_run_id = last.id
    a = FinancialAssessment(
        profile_id=profile.id, financing_request_id=r.id, forecast_run_id=forecast_run_id, as_of_date=as_of,
        engine_version=ENGINE_VERSION, status=ev.status,
        purpose_items_total=ev.gap.items_total if ev.gap else None,
        funding_gap=ev.gap.funding_gap if ev.gap else None,
        request_minus_gap=ev.gap.request_minus_gap if ev.gap else None,
        missing_items=ev.missing, flags=ev.flags, base_result=ev.base_result, explanation=ev.explanation,
        inputs_sha256=inputs_hash(ev.inputs), profile_data_version=profile.data_version,
    )
    db.add(a)
    db.flush()
    extra_flags = scenario_service.create_for_assessment(db, profile, a, ev.extra, as_of)
    if extra_flags - set(ev.flags):
        a.flags = ordered_flags(set(ev.flags) | extra_flags)  # DEC-30: flags only, the status never changes
    db.flush()
    db.refresh(a)
    return a


def latest(db: Session, profile: BusinessProfile, rid: uuid.UUID) -> FinancialAssessment:
    r = financing_service.get(db, profile, rid)
    a = db.scalar(select(FinancialAssessment).where(
        FinancialAssessment.profile_id == profile.id, FinancialAssessment.financing_request_id == r.id)
        .order_by(FinancialAssessment.created_at.desc(), FinancialAssessment.id).limit(1))
    if a is None:
        raise not_found()
    return a


def get(db: Session, profile: BusinessProfile, aid: uuid.UUID) -> FinancialAssessment:
    a = db.scalar(select(FinancialAssessment).where(FinancialAssessment.profile_id == profile.id,
                                                    FinancialAssessment.id == aid))
    if a is None:
        raise not_found()
    return a


ASSUMPTION_KEYS = {"supplier_delay": "scn.delay", "input_price_rise": "scn.price_rise",
                   "harvest_price_fall": "scn.harvest_price", "yield_shortfall": "scn.yield"}


def scenario_out(db: Session, profile: BusinessProfile, s: RiskScenario,
                 suppliers: dict | None = None) -> ScenarioOut:
    """Owner view: the supplier's own name is shown to its owner only (the
    lender snapshot uses Supplier 1/2/3; P5)."""
    if suppliers is None:
        suppliers = {x.id: x for x in supplier_service.list_suppliers(db, profile)}
    sup = suppliers.get(s.supplier_id) if s.supplier_id else None
    key = ASSUMPTION_KEYS[s.scenario_type]
    if s.scenario_type == "input_price_rise" and profile.activity_type == "crop_farm":
        key = "scn.input_cost"
    return ScenarioOut(id=s.id, scenario_type=s.scenario_type, origin=s.origin, status=s.status,
                       parameters=s.parameters, result=s.result, news_event_id=s.news_event_id,
                       supplier_name=sup.display_name if sup else None, assumption_key=key)


def scenarios(db: Session, profile: BusinessProfile, a: FinancialAssessment) -> list[ScenarioOut]:
    rows = db.scalars(select(RiskScenario).where(RiskScenario.profile_id == profile.id,
                                                 RiskScenario.assessment_id == a.id)
                      .order_by(RiskScenario.created_at, RiskScenario.id))
    suppliers = {x.id: x for x in supplier_service.list_suppliers(db, profile)}
    return [scenario_out(db, profile, s, suppliers) for s in rows]


def news_signal_rows(db: Session, profile: BusinessProfile, as_of: date,
                     scenarios_by_event: dict | None = None) -> list[dict]:
    """FR-NEWS-02/03: matched events with reason, source, corroboration and
    DEMO label. Empty news table -> [] (FR-NEWS-06)."""
    conc = supplier_service.concentration(db, profile, as_of)
    out = []
    for m in news_service.match(db, profile, as_of, conc.result.shares):
        e = m.event
        sc = (scenarios_by_event or {}).get(e.id)
        out.append({
            "id": str(e.id), "news_event_id": str(e.id), "headline": e.headline, "headline_lang": e.headline_lang,
            "summary": e.summary, "source_name": e.source_name, "source_url": e.source_url,
            "published_date": e.published_date.isoformat(),
            "event_date": e.event_date.isoformat() if e.event_date else None, "event_type": e.event_type,
            "districts": list(e.districts), "upazilas": list(e.upazilas), "is_demo": e.is_demo,
            "source_count": e.source_count, "corroboration": m.corroboration, "match_reasons": m.reasons,
            "auto_collected": e.curated_by == news_service.AUTO_CURATOR,  # SUG-45: not checked by a person
            "matched_supplier": m.supplier.display_name if m.supplier else None,
            "proposed_scenario_id": str(sc.id) if sc else None,
            "scenario_status": sc.status if sc else None,
        })
    return out


def assessment_out(db: Session, profile: BusinessProfile, a: FinancialAssessment) -> AssessmentOut:
    rows = list(db.scalars(select(RiskScenario).where(RiskScenario.profile_id == profile.id,
                                                      RiskScenario.assessment_id == a.id,
                                                      RiskScenario.news_event_id.is_not(None))))
    by_event = {s.news_event_id: s for s in rows}
    return AssessmentOut(
        id=a.id, financing_request_id=a.financing_request_id, activity_type=profile.activity_type, status=a.status,
        as_of_date=a.as_of_date, engine_version=a.engine_version, forecast_run_id=a.forecast_run_id,
        purpose_items_total=a.purpose_items_total, funding_gap=a.funding_gap, request_minus_gap=a.request_minus_gap,
        missing_items=a.missing_items, flags=a.flags, base_result=a.base_result, explanation=a.explanation,
        scenarios=scenarios(db, profile, a), news_signals=news_signal_rows(db, profile, a.as_of_date, by_event),
        inputs_sha256=a.inputs_sha256,
        is_stale=a.profile_data_version != profile.data_version, created_at=a.created_at,
    )


# --------------------------------------------------------------------------- season summary hook
def season_loan_cover(db: Session, profile: BusinessProfile, season: FarmingSeason, as_of: date) -> tuple | None:
    """SCR-F05 loan-cover price for the most recent request linked to this
    season, only when the request is complete enough to compute it."""
    r = db.scalar(select(FinancingRequest).where(
        FinancingRequest.profile_id == profile.id, FinancingRequest.season_id == season.id,
        FinancingRequest.status == "draft").order_by(FinancingRequest.created_at.desc()).limit(1))
    if r is None:
        return None
    ev = evaluate(db, profile, r, as_of)
    if ev.base_result.get("kind") != "crop_harvest":
        return None
    return Decimal(ev.base_result["loan_cover_price_per_unit"]), r.id, Decimal(ev.base_result["repayment_due"])
