"""Supply graph (Plan Ultra F4, SUG-62): the owner's suppliers, their areas and goods, and the news that touches
them, with the share of purchases that passes through each node. Read-only, computed on request, never stored.

* Owner view uses the owner's own supplier names; anything that leaves the owner (lender snapshot) uses the
  same "Supplier 1/2/3" labels as everywhere else (SUG-41).
* The what-if turns a node's exposure into money with the EXISTING supplier-delay scenario on the latest
  financing check's inputs. It never changes a status (DEC-30) and is never saved."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import AppError, not_found
from ..engine import graph as eg
from ..engine.concentration import pct, scenario_share
from ..models import BusinessProfile, FarmingSeason, FinancialAssessment
from . import assessment_service, financing_service, news_service, scenario_service, supplier_service

WHATIF_DAYS = (7, 14)


def _build(db: Session, profile: BusinessProfile, as_of: date, outside: bool):
    conc = supplier_service.concentration(db, profile, as_of)
    if outside:
        from .snapshot_service import supplier_labels  # local: snapshot_service imports this module
        _, labels, _ = supplier_labels(db, profile, as_of)
    else:
        labels = {sid: s.display_name for sid, s in conc.suppliers.items()}
    sups = []
    for sid, s in conc.suppliers.items():
        if not s.is_active:
            continue
        share = conc.share_of(sid)
        if share is None and conc.basis == "linked_purchases":
            share = Decimal(0)  # measured: no linked purchases in the window
        sups.append(eg.SupplierIn(str(sid), labels[sid], share, s.district, s.upazila, s.goods_supplied))
    matches = news_service.match(db, profile, as_of, conc.result.shares)
    news = [eg.NewsIn(str(m.event.id), m.event.headline, tuple(m.event.districts or ()), tuple(m.event.upazilas or ()),
                      tuple(m.event.commodities or ())) for m in matches]
    crops = []
    if profile.activity_type == "crop_farm":
        crops = list(dict.fromkeys(db.scalars(select(FarmingSeason.crop_name).where(
            FarmingSeason.profile_id == profile.id, FarmingSeason.status != "closed"))))
    g = eg.build(profile.display_name, profile.district, profile.upazila, crops, sups, news)
    return g, conc, {str(m.event.id): m for m in matches}


def _pct(x: Decimal | None) -> str | None:
    return None if x is None else str(pct(x))


def supply_graph(db: Session, profile: BusinessProfile, as_of: date, *, outside: bool = False) -> dict:
    g, conc, matches = _build(db, profile, as_of, outside)
    nodes = []
    for nid, a in g.nodes.items():
        row = {"id": nid, "kind": a["kind"], "label": a["label"], "exposure_pct": _pct(eg.exposure(g, nid))}
        if a["kind"] == "news":
            m = matches[nid.removeprefix("news:")]
            e = m.event
            row.update(event_type=e.event_type, source_name=e.source_name, published_date=e.published_date.isoformat(),
                       is_demo=e.is_demo, corroboration=m.corroboration, auto_collected=e.curated_by == "auto-news-search",
                       match_reasons=m.reasons)
        nodes.append(row)
    return {"as_of": as_of.isoformat(), "basis": conc.basis, "window_days": supplier_service.WINDOW_DAYS,
            "nodes": nodes, "edges": [{"from": a, "to": b, "relation": r} for a, b, r in g.edges],
            "whatif_available": profile.activity_type == "shop" and not outside}


def whatif(db: Session, profile: BusinessProfile, node_id: str, days: int, as_of: date) -> dict:
    """Shop only (the route enforces it). Supply from the node stops for `days` from today."""
    if days not in WHATIF_DAYS:
        raise AppError("VALIDATION_ERROR", 422, "err.validation", fields={"days": "graph.err.days"})
    g, _, _ = _build(db, profile, as_of, outside=False)
    if node_id not in g.nodes:
        raise not_found()
    x = eg.exposure(g, node_id)
    out = {"node": node_id, "label": g.nodes[node_id]["label"], "kind": g.nodes[node_id]["kind"],
           "exposure_pct": _pct(x), "days": days, "result": None, "reason": None, "financing_request_id": None}
    if x is None:
        out["reason"] = "share_unknown"
        return out
    if x == 0:
        out["reason"] = "no_purchases_through_node"
        return out
    a = db.scalar(select(FinancialAssessment).where(FinancialAssessment.profile_id == profile.id)
                  .order_by(FinancialAssessment.created_at.desc(), FinancialAssessment.id).limit(1))
    if a is None:
        out["reason"] = "no_check_yet"
        return out
    r = financing_service.get(db, profile, a.financing_request_id)
    ev = assessment_service.evaluate(db, profile, r, as_of)
    if "shop_inputs" not in ev.extra:
        out["reason"] = "check_not_computable"
        return out
    result, _ = scenario_service.compute("supplier_delay", {"share": str(scenario_share(min(x, Decimal(1)))),
                                                            "days": days, "start": as_of.isoformat()}, ev.extra)
    out.update(result=result, financing_request_id=str(r.id))
    return out
