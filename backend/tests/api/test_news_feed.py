"""SUG-45 daily news collector, offline: a fake RSS server stands in for the
news search. Covers keyword rules, headline-place rule, corroboration,
never overwriting a person's curation, the farm-input match and labels."""
from __future__ import annotations

from datetime import timedelta
from email.utils import format_datetime

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import news_feed
from app.core.clock import today, utcnow
from app.services import news_service
from tests.api.test_risk_p4 import demo_profile, seeded  # noqa: F401  (fixture)


def test_classify_rules() -> None:
    c = news_feed.classify
    assert c("Fire guts 30 shops at Savar kitchen market")[0] == "market_fire"
    assert c("Workers block Dhaka-Aricha highway in Savar")[0] == "hartal_road_blockade"
    assert c("40 factories in Savar shut indefinitely")[0] == "factory_closure_layoffs"
    assert c("Chickpea, rice, sugar prices rise") == ("price_shock", ["grocery"], ["rice", "sugar"])
    assert c("Govt cuts Aman rice buying prices despite rising farm costs") is None  # falling price
    assert c("Ceasefire talks continue") is None and c("Savar team wins cricket final") is None


def _rss(*items: tuple[str, str, int]) -> str:
    body = "".join(
        f"<item><title>{t} - {s}</title><link>https://news.google.com/rss/articles/{abs(hash(t + s))}</link>"
        f"<pubDate>{format_datetime(utcnow() - timedelta(days=d))}</pubDate>"
        f'<source url="https://{s.replace(" ", "").lower()}.example">{s}</source></item>'
        for t, s, d in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'


def _handler(request: httpx.Request) -> httpx.Response:
    q = request.url.params["q"]
    if q.startswith("Savar"):
        return httpx.Response(200, text=_rss(("Fire guts 30 shops at Savar kitchen market", "The Daily Star", 1),
                                             ("Savar market fire: 30 shops gutted", "Dhaka Tribune", 1),
                                             ("Fire at Mirpur market", "Other Paper", 1),  # place not in headline
                                             ("Savar team wins cricket final", "Sports Daily", 1)))
    if q.startswith("Dhamrai"):
        return httpx.Response(500)  # one failing search must not stop the rest
    if q.startswith('"rice"'):
        return httpx.Response(200, text=_rss(("Rice prices rise again", "New Age BD", 1)))
    if q.startswith('"onion"'):  # live run 16 Nov: a foreign story in a national search must not be kept
        return httpx.Response(200, text=_rss(("Onion prices in Tajikistan rise 60% in a month", "UkrAgroConsult", 1)))
    if q.startswith('"fertilizer"'):
        return httpx.Response(200, text=_rss(("Fertilizer prices hiked by Tk 5 a kg", "TBS News", 2),
                                             ("Fertilizer prices hiked old news", "TBS News", 20)))  # outside 7 days
    return httpx.Response(200, text=_rss())


def test_collect_import_and_owner_view(seeded, client) -> None:  # noqa: F811
    d1 = (today() - timedelta(days=1)).isoformat()
    engine = create_engine(seeded)
    with engine.begin() as conn:  # a person already curated the rice story for that day
        conn.execute(text(
            "INSERT INTO news_events (headline, headline_lang, source_name, source_url, published_date, event_type, "
            "sectors, commodities, source_count, dedup_key, is_demo, curated_by) VALUES ('Rice up (curated)', 'en', "
            "'Paper', 'https://p.example/1', :d, 'price_shock', ARRAY['grocery'], ARRAY['rice'], 1, :k, false, "
            "'person')"), {"d": d1, "k": f"price_shock-rice-{d1}"})
    with Session(engine) as db, db.begin(), httpx.Client(transport=httpx.MockTransport(_handler)) as fake:
        rows = news_feed.collect(db, today(), fake)
        report = news_service.import_rows(db, rows)
    assert (report.inserted, report.skipped) == (2, 1)  # fire (2 outlets) + fertilizer; rice kept as curated
    with engine.connect() as conn:
        ev = {r.event_type: r for r in conn.execute(text(
            "SELECT event_type, upazilas, source_count, curated_by, summary FROM news_events "
            "WHERE NOT is_demo AND event_type = 'market_fire'"))}
        rice = conn.execute(text("SELECT curated_by FROM news_events WHERE headline = 'Rice up (curated)'")).scalar()
    engine.dispose()
    assert ev["market_fire"].upazilas == ["Savar"] and ev["market_fire"].source_count == 2
    assert ev["market_fire"].curated_by == news_service.AUTO_CURATOR
    assert "Not checked by a person" in ev["market_fire"].summary and rice == "person"

    shop = demo_profile(client, "01900000001", "Rahim Store")
    items = client.get(f"/api/v1/profiles/{shop['id']}/news-signals").json()["items"]
    fire = next(i for i in items if i["event_type"] == "market_fire")
    assert fire["auto_collected"] is True and fire["corroboration"] == "corroborated"
    assert "location" in fire["match_reasons"]
    assert next(i for i in items if i["headline"] == "Rice up (curated)")["auto_collected"] is False

    farm = next(p for p in client.get("/api/v1/profiles").json()["items"] if p["display_name"] == "Rahim Rice Farm")
    items = client.get(f"/api/v1/profiles/{farm['id']}/news-signals").json()["items"]
    fert = next(i for i in items if i["event_type"] == "price_shock")
    assert fert["match_reasons"] == ["commodity"]  # a farm-input price rise reaches the farm


def test_watch_places_skip_whole_district_when_upazilas_known(seeded) -> None:  # noqa: F811
    engine = create_engine(seeded)
    with Session(engine) as db:
        places = news_feed.watch_places(db)
    engine.dispose()
    assert ("Dhaka", "Savar") in places and ("Gazipur", "Kaliakair") in places
    assert ("Dhaka", None) not in places
