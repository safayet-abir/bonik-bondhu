"""Shared-report snapshot (P5-T03; API spec §5; DEC-19/31).

The lender never reads live data: on approval/reshare we build a JSON
snapshot from an ALLOWLIST of the approved section keys only, store it in
`shared_reports` and hash its canonical form with SHA-256. The hash proves the
snapshot was not changed after sharing — not that the inputs are true.

Privacy (SEC-12): supplier names are replaced by "Supplier 1/2/3" (ordered
by share) everywhere, including owner-written free text; no phone, email,
document or note fields are ever included."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.clock import utcnow
from ..models import (
    BusinessProfile, FarmingSeason, FinancialAssessment, FinancingRequest, ForecastRun, RiskScenario, Transaction,
)
from . import (assessment_service, debt_service, financing_service, graph_service, season_service, summary_service,
               supplier_service)

SCHEMA = "bb-report-v1"
SECTIONS = ("profile_summary", "money_summary", "forecast", "financing_request", "obligations", "supplier_risk",
            "news_signals", "season_summary", "transaction_list")
REQUIRED = ("profile_summary", "financing_request")
SHOP_ONLY = ("forecast",)
FARM_ONLY = ("season_summary",)
CIB_NOTICE = "Official credit checks (CIB) are done by the lender, outside Bonik Bondhu."


def allowed_sections(profile: BusinessProfile) -> tuple[str, ...]:
    blocked = FARM_ONLY if profile.activity_type == "shop" else SHOP_ONLY
    return tuple(s for s in SECTIONS if s not in blocked)


def canonical(snapshot: dict) -> bytes:
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(snapshot: dict) -> str:
    return hashlib.sha256(canonical(snapshot)).hexdigest()


def verify_snapshot(snapshot: dict, stored_sha256: str) -> bool:
    """True when the stored snapshot still matches its hash (Testing §7)."""
    return sha256(snapshot) == stored_sha256


def _m(x) -> str | None:
    return None if x is None else f"{x:.2f}"


# --------------------------------------------------------------------------- sections
def _profile(p: BusinessProfile) -> dict:
    return {"display_name": p.display_name, "activity_type": p.activity_type, "business_category": p.business_category,
            "district": p.district, "upazila": p.upazila, "market_area": p.market_area}


def _money(db: Session, p: BusinessProfile, as_of: date) -> dict:
    weeks = get_settings().FORECAST_WINDOW_WEEKS
    start, end = as_of - timedelta(days=7 * weeks), as_of - timedelta(days=1)
    s = summary_service.summary(db, p, start, end).model_dump(mode="json")
    keep = ("sales_recorded", "cash_sales", "credit_sales", "operating_cash_in", "operating_cash_out",
            "net_operating_cash", "receivables_outstanding", "payables_outstanding", "financing_received",
            "principal_repaid", "interest_fees_paid", "owner_withdrawals", "owner_contributions", "evidence_mix",
            "record_coverage")
    return {"period": {"from": start.isoformat(), "to": end.isoformat()}, **{k: s[k] for k in keep if k in s}}


def _forecast(db: Session, a: FinancialAssessment) -> dict | None:
    run = db.get(ForecastRun, a.forecast_run_id) if a.forecast_run_id else None
    if run is None:
        return None
    return {"status": run.status, "as_of_date": run.as_of_date.isoformat(), "method_version": run.method_version,
            "weeks_with_records": run.weeks_with_records, "window_weeks": run.window_weeks,
            "weekly_net": None if run.status != "ok" else
            {"low": _m(run.net_weekly_low), "expected": _m(run.net_weekly_expected), "high": _m(run.net_weekly_high)},
            "horizons": run.horizons, "disclaimer": "estimate"}


def _financing(db: Session, p: BusinessProfile, r: FinancingRequest, a: FinancialAssessment,
               labels: dict) -> dict:
    items = financing_service.counted_items(financing_service.list_items(db, p, r))
    scen = db.scalars(select(RiskScenario).where(RiskScenario.profile_id == p.id, RiskScenario.assessment_id == a.id,
                                                 RiskScenario.status == "computed")
                      .order_by(RiskScenario.created_at, RiskScenario.id))
    prop = a.explanation.get("proposal", {})
    return {
        "requested_amount": _m(r.requested_amount), "purpose_text": r.purpose_text,
        "purpose_category": r.purpose_category,
        "items": [{"item_name": i.item_name, "quantity": f"{i.quantity.normalize():f}", "unit": i.unit,
                   "unit_price": _m(i.unit_price), "line_total": _m(i.line_total),
                   "price_source_type": i.price_source_type,
                   "price_date": i.price_date.isoformat() if i.price_date else None} for i in items],
        "purpose_items_total": _m(a.purpose_items_total), "funding_gap": _m(a.funding_gap),
        "request_minus_gap": _m(a.request_minus_gap), "over_request_explanation": r.over_request_explanation,
        "gap_inputs": {"associated_expenses": _m(r.associated_expenses), "liquidity_buffer": _m(r.liquidity_buffer),
                       "buffer_justification": r.buffer_justification,
                       "cash_safely_available": _m(r.cash_safely_available),
                       "committed_financing": _m(r.committed_financing)},
        "proposal": {"schedule_type": prop.get("schedule_type"), "installment_count": prop.get("installment_count"),
                     "frequency": prop.get("frequency"), "first_due_date": prop.get("first_due_date"),
                     "last_due_date": prop.get("last_due_date"), "total_interest_fees": prop.get("interest_fees_total"),
                     "interest_fees_unknown": prop.get("interest_fees_unknown"),
                     "repayment_total": prop.get("repayment_total"), "installments": prop.get("installments", []),
                     "current_cash_balance": _m(r.current_cash_balance),
                     "minimum_cash_reserve": _m(r.minimum_cash_reserve),
                     "label": "owner_proposal_not_lender_offer"},
        "assessment": {
            "id": str(a.id), "status": a.status, "as_of_date": a.as_of_date.isoformat(),
            "engine_version": a.engine_version, "missing_items": a.missing_items, "flags": a.flags,
            "base_result": a.base_result, "formulas": a.explanation.get("formulas", []),
            "inputs": a.explanation.get("inputs", []), "parameters": a.explanation.get("parameters", {}),
            "inputs_sha256": a.inputs_sha256, "disclaimer": "not_a_lending_decision",
            "scenarios": [{"scenario_type": s.scenario_type, "origin": s.origin,
                           "supplier": labels.get(s.supplier_id) if s.supplier_id else None,
                           "parameters": s.parameters, "result": s.result, "label": "what_if_only"} for s in scen],
        },
    }


def _obligations(db: Session, p: BusinessProfile) -> dict:
    debts = [d for d in debt_service.list_debts(db, p) if d.status == "active"]
    return {
        "declared": [{"lender_type": d.lender_type, "lender_label": d.lender_label,
                      "outstanding_balance": _m(d.outstanding_balance),
                      "outstanding_as_of": d.outstanding_as_of.isoformat(),
                      "installment_amount": _m(d.installment_amount), "installment_frequency": d.installment_frequency,
                      "next_due_date": d.next_due_date.isoformat() if d.next_due_date else None,
                      "is_overdue": d.is_overdue, "overdue_amount": _m(d.overdue_amount),
                      "evidence_state": d.evidence_state} for d in debts],
        "no_debt_declared": p.no_debt_declared_at is not None, "source": "declared_by_owner",
        "cib_notice": CIB_NOTICE,
    }


def _supplier_risk(conc: supplier_service.SupplierConcentration, labels: dict) -> dict:
    order = sorted(conc.result.shares, key=lambda k: -conc.result.shares[k])
    from ..engine.concentration import pct
    return {"basis": conc.basis, "window_days": supplier_service.WINDOW_DAYS,
            "suppliers": [{"label": labels[sid], "share_pct": str(pct(conc.result.shares[sid]))}
                          for sid in order if sid in labels],
            "top_share_pct": str(pct(conc.result.top_share)) if conc.result.top else None,
            "high_dependency": conc.result.high_dependency, "note_key": conc.note_key}


def _news(db: Session, p: BusinessProfile, as_of: date, names: dict) -> list[dict]:
    keep = ("headline", "headline_lang", "summary", "source_name", "source_url", "published_date", "event_date",
            "event_type", "districts", "upazilas", "is_demo", "corroboration", "source_count", "match_reasons",
            "auto_collected")
    out = []
    for n in assessment_service.news_signal_rows(db, p, as_of):
        row = {k: n[k] for k in keep}
        row["matched_supplier"] = names.get(n["matched_supplier"]) if n["matched_supplier"] else None
        out.append(row)
    return out


def _season(db: Session, p: BusinessProfile, r: FinancingRequest) -> dict | None:
    season = db.get(FarmingSeason, r.season_id) if r.season_id else None
    if season is None or season.profile_id != p.id:
        return None
    s = season_service.summary(db, p, season.id).model_dump(mode="json")
    s.pop("loan_cover_basis", None)
    return s


def _transactions(db: Session, p: BusinessProfile, as_of: date, labels: dict) -> list[dict]:
    weeks = get_settings().FORECAST_WINDOW_WEEKS
    rows = db.scalars(select(Transaction).where(
        Transaction.profile_id == p.id, Transaction.status == "confirmed",
        Transaction.value_date >= as_of - timedelta(days=7 * weeks), Transaction.value_date < as_of)
        .order_by(Transaction.value_date, Transaction.created_at))
    return [{"value_date": t.value_date.isoformat(), "txn_type": t.txn_type, "amount": _m(t.amount),
             "category": t.category, "supplier": labels.get(t.supplier_id) if t.supplier_id else None,
             "evidence_state": t.evidence_state, "entry_method": t.entry_method} for t in rows]


# --------------------------------------------------------------------------- build
def _scrub(value, names: list[tuple[re.Pattern, str]]):
    """Replace any supplier name inside owner-written text with its label."""
    if isinstance(value, str):
        for pattern, label in names:
            value = pattern.sub(label, value)
        return value
    if isinstance(value, list):
        return [_scrub(v, names) for v in value]
    if isinstance(value, dict):
        return {k: _scrub(v, names) for k, v in value.items()}
    return value


def supplier_labels(db: Session, profile: BusinessProfile, as_of: date):
    """(concentration, {supplier_id: "Supplier n"}, {display_name: label}) — n by share, largest first.
    Used for everything that leaves the owner: lender snapshots and AI tool output."""
    conc = supplier_service.concentration(db, profile, as_of)
    ordered = sorted(conc.suppliers.values(),
                     key=lambda s: (-(conc.result.shares.get(s.id) or 0), s.created_at, str(s.id)))
    labels = {s.id: f"Supplier {i}" for i, s in enumerate(ordered, 1)}
    return conc, labels, {s.display_name: labels[s.id] for s in ordered}


def name_patterns(names: dict[str, str]) -> list[tuple[re.Pattern, str]]:
    """Whole-word, case-insensitive; longest first. Bangla vowel signs are not
    \\w, so "রহিমের" still matches "রহিম". shortcut: names under 3 letters are
    not scrubbed (too many false hits); a different spelling/script is not caught."""
    return [(re.compile(r"(?<!\w)" + re.escape(n.strip()) + r"(?!\w)", re.IGNORECASE), lbl)
            for n, lbl in sorted(names.items(), key=lambda kv: -len(kv[0])) if len(n.strip()) >= 3]


def build(db: Session, profile: BusinessProfile, sections: list[str], r: FinancingRequest,
          a: FinancialAssessment) -> dict:
    as_of = a.as_of_date
    conc, labels, names = supplier_labels(db, profile, as_of)
    builders = {
        "profile_summary": lambda: _profile(profile),
        "money_summary": lambda: _money(db, profile, as_of),
        "forecast": lambda: _forecast(db, a),
        "financing_request": lambda: _financing(db, profile, r, a, labels),
        "obligations": lambda: _obligations(db, profile),
        "supplier_risk": lambda: {**_supplier_risk(conc, labels),
                                  "graph": graph_service.supply_graph(db, profile, as_of, outside=True)},
        "news_signals": lambda: _news(db, profile, as_of, names),
        "season_summary": lambda: _season(db, profile, r),
        "transaction_list": lambda: _transactions(db, profile, as_of, labels),
    }
    body = {key: builders[key]() for key in SECTIONS if key in sections}  # allowlist, fixed order
    patterns = name_patterns(names)
    return {"schema": SCHEMA, "generated_at": utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "as_of_date": as_of.isoformat(), "is_demo": profile.is_demo, "sections": _scrub(body, patterns)}
