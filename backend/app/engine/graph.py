"""Supply graph (Plan Ultra F4, SUG-62) — pure: no DB, no clock, no network.

One business's own supply picture: business → suppliers → the areas they sit in and the goods they supply →
the news events that touch those areas or goods. It is NOT a network across businesses (that, and any graph
learning, is roadmap). The only number it produces is an *exposure*: the share of this business's purchases
that passes through a node, from the same supplier shares the concentration check uses. Turning an exposure
into money is left to the existing scenario engine.

Area rule = the news matcher's rule: an event that names upazilas matches on upazila, otherwise on district."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SupplierIn:
    key: str
    label: str
    share: Decimal | None          # fraction of purchases (0.65), None when there is no basis
    district: str | None = None
    upazila: str | None = None
    goods: str | None = None       # free text: "rice, oil, lentils"


@dataclass(frozen=True)
class NewsIn:
    key: str
    label: str
    districts: tuple[str, ...] = ()
    upazilas: tuple[str, ...] = ()
    commodities: tuple[str, ...] = ()


@dataclass
class Graph:
    nodes: dict[str, dict] = field(default_factory=dict)      # id -> {kind, label, ...}
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (from, to, relation)

    def add_node(self, nid: str, **attrs) -> str:
        self.nodes.setdefault(nid, attrs)
        return nid

    def add_edge(self, a: str, b: str, rel: str) -> None:
        if (a, b, rel) not in self.edges:
            self.edges.append((a, b, rel))


def canon(s: str | None) -> str:
    return " ".join((s or "").casefold().split())


def goods(text: str | None) -> list[str]:
    """Supplied goods as phrases: split on commas, semicolons, slashes, bars and the word "and"."""
    return [g for g in (canon(x) for x in re.split(r"[,;/|]+|\s+and\s+", text or "")) if g]


def _words(phrase: str) -> set[str]:
    return set(canon(phrase).split())


def area_id(district: str | None, upazila: str | None) -> str:
    return "area:" + canon(district) + (("/" + canon(upazila)) if upazila else "")


def _in_area(n: NewsIn, district: str | None, upazila: str | None) -> bool:
    if n.upazilas:
        return bool(upazila) and canon(upazila) in {canon(u) for u in n.upazilas}
    return bool(district) and canon(district) in {canon(d) for d in n.districts}


def build(business_label: str, district: str | None, upazila: str | None, crops: list[str],
          suppliers: list[SupplierIn], news: list[NewsIn]) -> Graph:
    g = Graph()
    biz = g.add_node("business", kind="business", label=business_label)
    areas: dict[str, tuple[str | None, str | None]] = {}

    def area(d: str | None, u: str | None) -> str | None:
        if not d:
            return None
        nid = area_id(d, u)
        areas[nid] = (d, u)
        return g.add_node(nid, kind="area", label=", ".join(x for x in (u, d) if x))

    own = area(district, upazila)
    if own:
        g.add_edge(biz, own, "located_in")
    for c in crops:
        if canon(c):
            g.add_edge(biz, g.add_node("good:" + canon(c), kind="good", label=c.strip()), "grows")
    for s in suppliers:
        sid = g.add_node("supplier:" + s.key, kind="supplier", label=s.label, share=s.share)
        g.add_edge(biz, sid, "buys_from")
        a = area(s.district, s.upazila)
        if a:
            g.add_edge(sid, a, "located_in")
        for item in goods(s.goods):
            g.add_edge(sid, g.add_node("good:" + item, kind="good", label=item), "supplies")
    for n in news:
        nid = g.add_node("news:" + n.key, kind="news", label=n.label)
        for aid, (d, u) in areas.items():
            if _in_area(n, d, u):
                g.add_edge(nid, aid, "affects")
        wanted = set().union(*(_words(c) for c in n.commodities)) if n.commodities else set()
        for gid, attrs in list(g.nodes.items()):
            if attrs["kind"] == "good" and wanted & _words(attrs["label"]):
                g.add_edge(nid, gid, "affects")
    return g


def suppliers_through(g: Graph, node_id: str) -> set[str]:
    """Supplier nodes whose purchases pass through `node_id`."""
    kind = g.nodes[node_id]["kind"]
    if kind == "supplier":
        return {node_id}
    if kind in ("area", "good"):
        return {a for a, b, rel in g.edges if b == node_id and rel in ("located_in", "supplies")
                and g.nodes[a]["kind"] == "supplier"}
    if kind == "news":
        out: set[str] = set()
        for _, target, rel in (e for e in g.edges if e[0] == node_id):
            out |= suppliers_through(g, target)
        return out
    return {n for n, attrs in g.nodes.items() if attrs["kind"] == "supplier"}  # business: everything


def exposure(g: Graph, node_id: str) -> Decimal | None:
    """Share of purchases through the node (sum of distinct suppliers' shares). None when a share is unknown."""
    sids = suppliers_through(g, node_id)
    shares = [g.nodes[s].get("share") for s in sids]
    if any(x is None for x in shares):
        return None
    return sum(shares, Decimal(0))
