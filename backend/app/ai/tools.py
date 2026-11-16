"""Advisor tools (AI doc §8.1; FR-ADV-02). Read-only and bound to ONE
profile taken from the session — no tool accepts a profile id, so a question
like "show Karim's sales" cannot reach another profile (SEC-19).

Outputs are aggregates, dates, statuses and labels: never phone, email,
person names, entry notes, documents or supplier names ("Supplier 1/2/3",
the same labels the lender sees); every output also goes through the
supplier-name scrub as a second guard. Money is computed here by code; the
model only reads it."""
from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..core.clock import today
from ..core.errors import AppError
from ..engine import baseline as bl
from ..engine.concentration import pct
from ..engine.money import ZERO, money
from ..engine.schedules import horizon_end
from ..services import (
    assessment_service, debt_service, economy_service, financing_service, forecast_service, ledger_service,
    season_service, summary_service, supplier_service,
)
from ..services.snapshot_service import _scrub, name_patterns, supplier_labels

HELP: list[dict] = json.loads((Path(__file__).resolve().parents[1] / "help" / "help_topics.json")
                              .read_text(encoding="utf-8"))


# Plain words for the model (E10: raw codes like "not_checked_yet" ended up in replies). Same text as the UI (en.json).
STATUS_TEXT = {
    "ready_for_lender_review": "ready for a lender to review (a check of the proposal, not a lending decision)",
    "not_affordable_base_case": "in the careful case the proposed payments do not fit the expected cash",
    "insufficient_information": "some information is missing, so the check cannot finish",
}
MISSING_TEXT = {
    "debts_not_declared": "Tell us about your current loans (or say you have none)",
    "household_withdrawal_not_declared": "Write how much you take for your family each month",
    "purpose_items_missing": "Add what you will buy, with prices",
    "gap_inputs_missing": "Fill in your money details",
    "terms_incomplete": "Complete your repayment proposal",
    "forecast_insufficient_history": "Record at least 4 weeks of sales and costs",
    "term_beyond_forecast_horizon": "All installments must fall within the next 90 days for this check",
    "season_incomplete": "Link a crop season with output and price estimates",
    "repayment_due_before_expected_harvest": "Repayment is due before the expected harvest — choose a later date",
    "profile_location_missing": "Add your district and upazila",
}
FLAG_TEXT = {
    "request_exceeds_gap": "You asked for more than the estimated need",
    "over_request_explained": "You asked for more than the estimated need and explained why",
    "weak_price_evidence": "All prices are your own estimates — a supplier quote makes the case stronger",
    "high_supplier_dependency": "Most purchases come from one supplier",
    "scenario_shortfall": "A what-if situation shows a possible shortfall",
    "pre_harvest_cash_shortfall": "Cash may run short before the harvest",
    "starting_cash_unknown": "Cash in hand not given — counted as 0",
    "reserve_zero": "Minimum cash to keep is 0 — no safety margin",
    "interest_fees_unknown": "Interest and fees unknown — counted as 0",
    "existing_debt_overdue": "An existing loan is overdue — the overdue amount is counted as due today",
    "existing_debt_dates_outdated": "A loan's next due date is in the past — please update it",
    "news_signal_single_source": "A news signal comes from one source only",
}


def _m(x) -> str | None:
    return None if x is None else f"{money(Decimal(x)):.2f}"


def _spec(name: str, description: str, props: dict | None = None) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
                                             "parameters": {"type": "object", "properties": props or {}}}}


SPECS = {
    "get_money_summary": _spec("get_money_summary", "Money in and out for a period: sales, costs, net, baki.",
                               {"period": {"type": "string", "enum": ["this_week", "this_month", "last_8_weeks"]}}),
    "get_recent_entries": _spec("get_recent_entries", "The latest recorded entries (type, amount, date).",
                                {"limit": {"type": "integer", "minimum": 1, "maximum": 10}}),
    "get_upcoming_installments": _spec("get_upcoming_installments",
                                       "Known loan installments due soon, with totals, and the owner's proposed new "
                                       "loan installments.", {"days": {"type": "integer", "enum": [7, 30]}}),
    "get_latest_forecast": _spec("get_latest_forecast", "Weekly cash estimate and 7/30/60/90-day totals (shop only)."),
    "get_latest_assessment": _spec("get_latest_assessment", "Result of the latest financing check: status, missing "
                                   "items, flags, funding gap, first shortfall."),
    "get_scenarios": _spec("get_scenarios", "What-if results of the latest check (supplier delay, price rise, harvest)."),
    "get_supplier_dependency": _spec("get_supplier_dependency", "Share of purchases per supplier (labels only)."),
    "get_news_signals": _spec("get_news_signals", "News from our list that may affect this business, with source."),
    "get_season_summary": _spec("get_season_summary", "Current crop season: costs, income range, break-even (farm only)."),
    "get_economy_context": _spec("get_economy_context", "Bangladesh yearly economy figures from the World Bank "
                                 "(inflation, lending interest rate, GDP growth, private credit), with year and "
                                 "source; plus, if a financing check can run, what happens if prices keep rising "
                                 "at last year's inflation."),
    "get_help": _spec("get_help", "Plain explanation of a term or screen.",
                      {"topic": {"type": "string", "enum": [h["key"] for h in HELP]}}),
}


class Toolbox:
    def __init__(self, db: Session, profile, lang: str) -> None:
        self.db, self.p, self.lang, self.today = db, profile, lang, today()
        self.shop = profile.activity_type == "shop"
        self.conc, self.labels, names = supplier_labels(db, profile, self.today)
        self.label_by_name = names
        self.patterns = name_patterns(names)

    def names(self) -> list[str]:
        skip = {"get_season_summary"} if self.shop else {"get_latest_forecast", "get_supplier_dependency"}
        return [n for n in SPECS if n not in skip]

    def specs(self) -> list[dict]:
        return [SPECS[n] for n in self.names()]

    def data(self, name: str, args: dict | None = None) -> dict:
        if name not in self.names():
            return {"error": "unknown_tool"}
        fn = getattr(self, "_" + name)
        try:
            return _scrub(fn(**{k: v for k, v in (args or {}).items()
                                if k in SPECS[name]["function"]["parameters"]["properties"]}), self.patterns)
        except (AppError, TypeError, ValueError):
            return {"error": "not_available"}

    def run(self, name: str, args: dict) -> str:
        return json.dumps(self.data(name, args), ensure_ascii=False, default=str)

    # ------------------------------------------------------------------ tools
    def _get_money_summary(self, period: str = "this_month") -> dict:
        t = self.today
        ranges = {"this_week": (t - timedelta(days=6), t), "last_8_weeks": (t - timedelta(days=56), t - timedelta(days=1))}
        period = period if period in ranges else "this_month"
        frm, to = ranges.get(period, (t.replace(day=1), t))
        s = summary_service.summary(self.db, self.p, frm, to).model_dump(mode="json", by_alias=True)
        return {"period": period, **s}

    def _get_recent_entries(self, limit: int = 5) -> dict:
        rows, _ = ledger_service.list_transactions(self.db, self.p, from_=None, to=None, txn_type=None,
                                                   status="confirmed", limit=max(1, min(int(limit), 10)), offset=0)
        return {"entries": [{"date": t.value_date.isoformat(), "type": t.txn_type, "amount": _m(t.amount),
                             "category": t.category, "evidence": t.evidence_state,
                             "supplier": self.labels.get(t.supplier_id) if t.supplier_id else None} for t in rows]}

    def _get_upcoming_installments(self, days: int = 7) -> dict:
        days = 30 if int(days) > 7 else 7
        until = self.today + timedelta(days=days - 1)
        active = [d for d in debt_service.list_debts(self.db, self.p) if d.status == "active"]
        existing = [{"date": d.isoformat(), "amount": _m(a), "lender_type": active[int(label[4:]) - 1].lender_type}
                    for label, rows in debt_service.obligation_rows(self.db, self.p, self.today, until)
                    for d, a in rows if d <= until]
        reqs = financing_service.list_requests(self.db, self.p)
        proposed = [{"date": d.isoformat(), "amount": _m(a)} for d, a in
                    (financing_service.new_schedule(reqs[0]) if reqs else []) if self.today <= d <= until]
        return {
            "days": days, "from": self.today.isoformat(), "to": until.isoformat(),
            "debts_declared": debt_service.debts_declared(self.db, self.p),
            "existing_installments": existing, "existing_count": len(existing),
            "existing_total": _m(sum((Decimal(r["amount"]) for r in existing), ZERO)),
            "proposed_new_loan_installments": proposed, "proposed_count": len(proposed),
            "proposed_total": _m(sum((Decimal(r["amount"]) for r in proposed), ZERO)),
            "proposed_label": "the owner's own proposal, not a lender offer",
        }

    def _get_latest_forecast(self) -> dict:
        b = forecast_service.compute(self.db, self.p, self.today)
        out = {"status": b.status, "weeks_with_records": b.weeks_used,
               "weeks_needed": get_settings().FORECAST_MIN_WEEKS, "label": "estimate from recent weeks, not a promise"}
        if b.ok:
            debt_rows = [r for _, rows in debt_service.obligation_rows(self.db, self.p, self.today,
                                                                      horizon_end(self.today)) for r in rows]
            out["weekly_net"] = {"low": _m(b.net_weekly_low), "expected": _m(b.net_weekly_expected),
                                 "high": _m(b.net_weekly_high)}
            out["horizons_days"] = bl.horizons(b, self.today, debt_rows)
        return out

    def _latest(self):
        reqs = financing_service.list_requests(self.db, self.p)
        if not reqs:
            return None, None
        try:
            return reqs[0], assessment_service.latest(self.db, self.p, reqs[0].id)
        except AppError:
            return reqs[0], None

    def _get_latest_assessment(self) -> dict:
        r, a = self._latest()
        if r is None:
            return {"status_code": "no_financing_request", "result": "no financing request yet", "screen": "Financing"}
        if a is not None and a.profile_data_version == self.p.data_version:
            code, missing, flags, base = a.status, a.missing_items, a.flags, a.base_result or {}
            totals = (a.purpose_items_total, a.funding_gap, a.request_minus_gap)
            source = f"saved check of {a.as_of_date.isoformat()}"
        else:  # never checked, or the records changed since: work it out now (read-only, nothing is saved)
            ev = assessment_service.evaluate(self.db, self.p, r, self.today)
            code, missing, flags, base = ev.status, ev.missing, ev.flags, ev.base_result
            totals = (ev.gap.items_total, ev.gap.funding_gap, ev.gap.request_minus_gap) if ev.gap else (None,) * 3
            source = "worked out now, not saved (press Check in Financing to save it and see the what-ifs)"
        return {"requested_amount": _m(r.requested_amount), "purpose_category": r.purpose_category,
                "status_code": code, "result": STATUS_TEXT[code], "source": source,
                "missing": [MISSING_TEXT.get(m, m) for m in missing], "flags": [FLAG_TEXT.get(f, f) for f in flags],
                "purpose_items_total": _m(totals[0]), "funding_gap": _m(totals[1]), "request_minus_gap": _m(totals[2]),
                "details": {k: v for k, v in base.items() if k != "checks"},
                "label": "a check of the owner's own proposal, not a lending decision; the lender decides"}

    def _get_scenarios(self) -> dict:
        _, a = self._latest()
        if a is None:
            return {"scenarios": [], "note": "no check yet"}
        out = []
        for s in assessment_service.scenarios(self.db, self.p, a):
            params = dict(s.parameters)
            if "share" in params:
                params["share_pct"] = str(pct(Decimal(params["share"])))
            out.append({"type": s.scenario_type, "origin": s.origin, "status": s.status, "parameters": params,
                        "result": s.result, "supplier": self.label_by_name.get(s.supplier_name or "")})
        return {"scenarios": out, "label": "what-if only, does not change the result"}

    def _get_supplier_dependency(self) -> dict:
        c = self.conc
        order = sorted(c.result.shares, key=lambda k: -c.result.shares[k])
        return {"basis": c.basis, "window_days": supplier_service.WINDOW_DAYS,
                "suppliers": [{"label": self.labels[s], "share_pct": str(pct(c.result.shares[s]))}
                              for s in order if s in self.labels],
                "high_dependency": c.result.high_dependency,
                "threshold_pct": str(pct(get_settings().HIGH_DEPENDENCY_SHARE)),
                "few_records": c.note_key is not None}

    def _get_news_signals(self) -> dict:
        rows = assessment_service.news_signal_rows(self.db, self.p, self.today)
        return {"signals": [{"headline": n["headline"], "source": n["source_name"], "published": n["published_date"],
                             "event_type": n["event_type"], "corroboration": n["corroboration"],
                             "is_demo": n["is_demo"], "collected_automatically": n["auto_collected"],
                             "why_matched": n["match_reasons"],
                             "supplier": self.label_by_name.get(n["matched_supplier"] or "")} for n in rows[:8]],
                "label": "reported news, not confirmed facts"}

    def _get_season_summary(self) -> dict:
        seasons = [s for s in season_service.list_seasons(self.db, self.p) if s.status != "closed"]
        if not seasons:
            return {"status": "no_season", "screen": "Seasons"}
        return season_service.summary(self.db, self.p, seasons[0].id).model_dump(mode="json")

    def _get_economy_context(self) -> dict:
        ctx = economy_service.context()
        out = {"source": ctx["source"]["name"], "country": ctx["country"],
               "figures": [{"name": i["label"], "year": i["year"], "value_pct": i["value"]} for i in ctx["indicators"]],
               "label": "yearly national figures, not live and not about this business"}
        r, _ = self._latest()
        w = economy_service.inflation_whatif(self.db, self.p, r, self.today) if r is not None else None
        if w is not None:
            out["inflation_whatif"] = {"price_rise_pct": w["price_rise_pct"], "days": w["days"],
                                       "covered": w["result"]["covered"],
                                       "label": "what-if only, does not change the result"}
        return out

    def _get_economy_context(self) -> dict:
        ctx = economy_service.context()
        out = {"source": ctx["source"]["name"], "country": ctx["country"],
               "figures": [{"key": i["key"], "name": i["label"], "year": i["year"], "value_pct": i["value"]}
                           for i in ctx["indicators"]],
               "label": "yearly national figures, not live and not about this business"}
        r, _ = self._latest()
        w = economy_service.inflation_whatif(self.db, self.p, r, self.today) if r is not None else None
        if w is not None:
            out["inflation_whatif"] = {"price_rise_pct": w["price_rise_pct"], "days": w["days"],
                                       "covered": w["result"]["covered"],
                                       "label": "what-if only, does not change the result"}
        return out

    def _get_help(self, topic: str = "") -> dict:
        h = next((x for x in HELP if x["key"] == topic), None)
        if h is None:
            return {"topics": [x["key"] for x in HELP]}
        return {"title": h[f"title_{self.lang}"], "text": h[f"body_{self.lang}"]}
