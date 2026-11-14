"""UT-08 supplier concentration + P4 pure helpers (news location rules)."""
from __future__ import annotations

from decimal import Decimal as D

from app.engine import concentration as conc
from app.services.news_service import canon

T = D("0.50")


def test_ut08_d1_shares_65_25_10_high() -> None:
    c = conc.from_amounts({"A": D("488800"), "B": D("188000"), "C": D("75200")}, T)
    assert c.total == D("752000")
    assert {k: conc.pct(v) for k, v in c.shares.items()} == {"A": D("65.0"), "B": D("25.0"), "C": D("10.0")}
    assert c.top == "A" and c.high_dependency is True
    assert conc.scenario_share(c.top_share) == D("0.6500")


def test_ut08_single_supplier_100_and_equal_split_at_threshold() -> None:
    one = conc.from_amounts({"A": D("1000")}, T)
    assert conc.pct(one.top_share) == D("100.0") and one.high_dependency
    half = conc.from_amounts({"A": D("500"), "B": D("500")}, T)
    assert half.top_share == D("0.5") and half.high_dependency  # ≥ 0.50 counts (SUG-10)


def test_ut08_below_threshold_and_empty() -> None:
    c = conc.from_amounts({"A": D("40"), "B": D("35"), "C": D("25")}, T)
    assert not c.high_dependency and conc.pct(c.top_share) == D("40.0")
    empty = conc.from_amounts({}, T)
    assert empty.top is None and not empty.high_dependency


def test_declared_shares_are_not_normalised() -> None:
    c = conc.from_declared({"A": D("60"), "B": D("20")}, T)  # owner listed only 80% of purchases
    assert c.total is None and c.shares["A"] == D("0.6") and c.high_dependency


def test_pct_rounds_half_up() -> None:
    assert conc.pct(D("0.12345")) == D("12.3") and conc.pct(D("0.12350")) == D("12.4")


def test_location_canonicalisation() -> None:
    assert canon("  Kaliakair  ") == "kaliakair"
    assert canon("Chittagong") == "chattogram" == canon("CHATTOGRAM")
    assert canon("Savar Upazila") == "savar"
    assert canon(None) == ""
