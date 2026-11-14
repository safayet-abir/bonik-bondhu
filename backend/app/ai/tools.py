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
    assessment_service, debt_service, financing_service, forecast_service, ledger_service, season_service,
    summary_service, supplier_service,
)
from ..services.snapshot_service import _scrub, name_patterns, supplier_labels

HELP: list[dict] = json.loads((Path(__file__).resolve().parents[1] / "help" / "help_topics.json")
                              .read_text(encoding="utf-8"))


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
            return {"status": "no_financing_request", "screen": "Financing"}
        out = {"requested_amount": _m(r.requested_amount), "purpose_category": r.purpose_category}
        if a is None:
            return {**out, "status": "not_checked_yet", "screen": "Financing"}
        return {**out, "status": a.status, "checked_on": a.as_of_date.isoformat(),
                "is_stale": a.profile_data_version != self.p.data_version, "missing_items": a.missing_items,
                "flags": a.flags, "purpose_items_total": _m(a.purpose_items_total), "funding_gap": _m(a.funding_gap),
                "request_minus_gap": _m(a.request_minus_gap),
                "result": {k: v for k, v in (a.base_result or {}).items() if k != "checks"},
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

    def _get_help(self, topic: str = "") -> dict:
        h = next((x for x in HELP if x["key"] == topic), None)
        if h is None:
            return {"topics": [x["key"] for x in HELP]}
        return {"title": h[f"title_{self.lang}"], "text": h[f"body_{self.lang}"]}
