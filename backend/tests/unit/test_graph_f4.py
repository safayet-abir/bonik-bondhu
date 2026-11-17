"""Plan Ultra F4 supply graph engine (pure) — D1-like fixture: A 65 % Kaliakair, B 25 % Savar, C 10 % Dhamrai."""
from decimal import Decimal as D

from app.engine import graph as g

SUPPLIERS = [
    g.SupplierIn("a", "Supplier 1", D("0.65"), "Gazipur", "Kaliakair", "rice, oil, lentils"),
    g.SupplierIn("b", "Supplier 2", D("0.25"), "Dhaka", "Savar", "lentils, flour"),
    g.SupplierIn("c", "Supplier 3", D("0.10"), "Dhaka", "Dhamrai", "spices"),
]
BLOCKADE = g.NewsIn("blk", "Blockade near Kaliakair", ("Gazipur",), ("Kaliakair",), ("rice", "oil"))
DHAKA_FLOOD = g.NewsIn("fl", "Dhaka district flood", ("Dhaka",), (), ())


def graph(news=(BLOCKADE,)):
    return g.build("Rahim Store", "Dhaka", "Savar", [], SUPPLIERS, list(news))


def test_nodes_and_edges() -> None:
    gr = graph()
    kinds = {n: a["kind"] for n, a in gr.nodes.items()}
    assert kinds["business"] == "business" and kinds["supplier:a"] == "supplier"
    assert {n for n, k in kinds.items() if k == "area"} == {"area:gazipur/kaliakair", "area:dhaka/savar",
                                                             "area:dhaka/dhamrai"}
    assert {n for n, k in kinds.items() if k == "good"} == {"good:rice", "good:oil", "good:lentils", "good:flour",
                                                             "good:spices"}
    assert ("business", "area:dhaka/savar", "located_in") in gr.edges          # own shop location
    assert ("news:blk", "area:gazipur/kaliakair", "affects") in gr.edges
    assert ("news:blk", "area:dhaka/savar", "affects") not in gr.edges         # upazila rule, not district
    assert {("news:blk", "good:rice", "affects"), ("news:blk", "good:oil", "affects")} <= set(gr.edges)


def test_exposure_per_kind() -> None:
    gr = graph()
    assert g.exposure(gr, "supplier:b") == D("0.25")
    assert g.exposure(gr, "area:gazipur/kaliakair") == D("0.65")
    assert g.exposure(gr, "good:lentils") == D("0.90")            # A and B both supply lentils, counted once each
    assert g.exposure(gr, "news:blk") == D("0.65")               # area + goods reach only Supplier 1, no double count
    assert g.exposure(gr, "business") == D("1.00")


def test_district_event_without_upazilas_hits_every_upazila_of_that_district() -> None:
    gr = graph((DHAKA_FLOOD,))
    assert g.exposure(gr, "news:fl") == D("0.35")                # Savar 25 % + Dhamrai 10 %
    assert ("news:fl", "area:dhaka/savar", "affects") in gr.edges


def test_unknown_share_is_unknown_not_zero() -> None:
    gr = g.build("X", None, None, [], [g.SupplierIn("x", "Supplier 1", None, "Rajshahi", None, "mango")], [])
    assert g.exposure(gr, "good:mango") is None                  # sparse data is never shown as low risk


def test_farm_crops_and_goods_parsing() -> None:
    gr = g.build("Farm", "Dhaka", "Dhamrai", ["Rice"], [], [g.NewsIn("f", "flood", ("Dhaka",), ("Dhamrai",), ("rice",))])
    assert ("business", "good:rice", "grows") in gr.edges and ("news:f", "good:rice", "affects") in gr.edges
    assert g.exposure(gr, "news:f") == D(0)                      # a farm with no suppliers: no purchase exposure
    assert g.goods("rice, oil and lentils; sugar/flour") == ["rice", "oil", "lentils", "sugar", "flour"]
