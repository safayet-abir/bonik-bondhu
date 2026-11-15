"""Daily news collector (SUG-45). Never real-time; never runs inside a request.

Google News RSS search (free, no key) for the areas our owners and their
suppliers are in, plus national price searches -> headlines classified by
fixed keyword rules -> the same validation, dedup and corroboration as the
curated CSV (news_service.import_rows). We store headline, outlet, link and
date only; the summary is our own sentence, never article text. Rows are
marked `curated_by = auto-news-search` and the UI says "collected
automatically, not checked by a person"; any scenario they propose still
waits for the owner. A person's curated event is never overwritten.

shortcut: English-language headlines only (Bangla place names would need a
gazetteer); add one to also search Bangla outlets."""
from __future__ import annotations

import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BusinessProfile, Supplier
from .services import news_service
from .services.news_service import ALIASES, AUTO_CURATOR, ImportReport, canon

log = logging.getLogger("bonik.news_feed")
FEED = "https://news.google.com/rss/search"
DHAKA = ZoneInfo("Asia/Dhaka")
WINDOW_DAYS = 7


def _w(pattern: str) -> re.Pattern:
    return re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)


MARKET = r"markets?|bazaa?rs?|kitchen market|wholesale|shops?|stalls?"
RULES: list[tuple[str, list[re.Pattern]]] = [  # first rule whose patterns ALL occur in the headline wins
    ("market_fire", [_w(r"fire|blaze|gutted|burnt|burned"), _w(MARKET)]),
    ("flood_waterlogging", [_w(r"floods?|flooding|flooded|waterlog\w*|inundat\w*|submerged")]),
    ("hartal_road_blockade", [_w(r"blockades?|blockaded|hartal|(?:block|blocked|blocking)\s+(?:the\s+)?"
                                 r"(?:[\w-]+\s+)?(?:highway|road|rail\w*)")]),  # "block Dhaka-Aricha highway"
    ("market_eviction_relocation", [_w(r"evict\w*|demolish\w*|relocat\w*"), _w(MARKET)]),
    ("factory_closure_layoffs", [_w(r"factor(?:y|ies)|mills?"), _w(r"closed?|closure|shut\w*|layoffs?|laid off")]),
    ("disease_outbreak", [_w(r"outbreak|anthrax|cholera|bird flu|avian influenza")]),
]
PRICE = _w(r"prices?")
PRICE_UP = _w(r"rises?|rising|rose|hikes?|hiked|soar\w*|jump\w*|surg\w*|spik\w*|increase[sd]?|up")
PRICE_DOWN = _w(r"cuts?|declin\w*|falls?|fell|drops?|dropped|eases?|eased|lower\w*")  # mixed headline -> skip
# commodity -> sectors it matters to (farm inputs: none; they reach farms via the input rule)
COMMODITIES = {"rice": ["grocery"], "edible oil": ["grocery"], "soybean oil": ["grocery"], "onion": ["grocery"],
               "potato": ["grocery"], "lentil": ["grocery"], "sugar": ["grocery"], "egg": ["grocery"],
               "fertiliser": [], "fertilizer": [], "urea": [], "diesel": []}


def classify(title: str) -> tuple[str, list[str], list[str]] | None:
    """Headline -> (event_type, sectors, commodities), or None if not one of ours."""
    for event_type, patterns in RULES:
        if all(p.search(title) for p in patterns):
            return event_type, [], []
    if PRICE.search(title) and PRICE_UP.search(title) and not PRICE_DOWN.search(title):
        found = [c for c in COMMODITIES if _w(re.escape(c)).search(title)]
        if found:
            return "price_shock", sorted({s for c in found for s in COMMODITIES[c]}), found
    return None


def watch_places(db: Session) -> list[tuple[str, str | None]]:
    """(district, upazila) of active profiles and suppliers. A district is
    searched on its own only when nobody there gave an upazila (a whole-city
    search like "Dhaka" is too noisy)."""
    rows = list(db.execute(select(BusinessProfile.district, BusinessProfile.upazila)
                           .where(BusinessProfile.archived_at.is_(None))))
    rows += list(db.execute(select(Supplier.district, Supplier.upazila).where(Supplier.is_active.is_(True))))
    seen: dict[tuple[str, str], tuple[str, str | None]] = {}
    for district, upazila in rows:
        if district and district.strip():
            seen.setdefault((canon(district), canon(upazila)), (district.strip(), (upazila or "").strip() or None))
    with_upazila = {d for d, u in seen if u}
    return sorted(v for (d, u), v in seen.items() if u or d not in with_upazila)


def _names(place: str) -> re.Pattern:
    names = {place} | {alias for alias, target in ALIASES.items() if target == canon(place)}
    return _w("|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)))


# National price searches also return foreign stories ("Onion prices in Tajikistan rise", live run 16 Nov):
# keep one only if the headline names Bangladesh/Dhaka or the publisher is Bangladeshi.
# shortcut: hand-kept outlet list; an unlisted BD outlet's national story is skipped (fewer signals, never a
# foreign one) — extend the list if real BD stories go missing.
BD_OUTLETS = {"thedailystar", "tbsnews", "newagebd", "observerbd", "dhakatribune", "bdnews24", "prothomalo",
              "banglatribune", "thefinancialexpress", "daily-sun", "thedailynewnation", "unb", "bssnews", "risingbd",
              "jugantor", "samakal", "kalerkantho", "ittefaq", "bd-pratidin", "dailyjanakantha", "ajkerpatrika",
              "jagonews24", "somoynews", "banglanews24", "dhakapost", "dailyasianage", "dailynewnation",
              "bonikbarta"}
BD_WORDS = _w(r"Bangladesh|Bangladeshi|Dhaka")


def _bd_outlet(host: str) -> bool:
    h = host.lower().removeprefix("www.").removeprefix("en.")
    label = h.split(".")[0]
    return h.endswith(".bd") or label.endswith("bd") or label in BD_OUTLETS  # "…bd": newagebd, observerbd


def _search(client: httpx.Client, query: str) -> list[tuple[str, str, str, date, str]]:
    """(headline, link, outlet, published Dhaka date, publisher host) from one RSS search."""
    r = client.get(FEED, params={"q": f"{query} when:{WINDOW_DAYS}d", "hl": "en-BD", "gl": "BD", "ceid": "BD:en"})
    r.raise_for_status()
    out = []
    for item in ET.fromstring(r.content).iter("item"):
        title, link = item.findtext("title") or "", item.findtext("link") or ""
        outlet = (item.findtext("source") or "").strip()
        src = item.find("source")
        host = httpx.URL(src.get("url", "")).host if src is not None else ""
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(DHAKA).date()
        except (TypeError, ValueError):
            continue
        if outlet and title.endswith(f" - {outlet}"):
            title = title[: -len(outlet) - 3]
        if title and link.startswith("https://") and outlet:
            out.append((title.strip(), link, outlet, published, host))
    return out


LABELS = {"market_fire": "a market fire", "flood_waterlogging": "flooding or waterlogging",
          "hartal_road_blockade": "a road blockade or hartal", "market_eviction_relocation": "a market eviction",
          "factory_closure_layoffs": "factory closures or layoffs", "disease_outbreak": "a disease outbreak",
          "price_shock": "a price rise"}


def _row(title: str, link: str, outlet: str, published: date, kind: tuple[str, list[str], list[str]],
         district: str | None, upazila: str | None) -> dict[str, str]:
    event_type, sectors, commodities = kind
    where = f" in {', '.join(p for p in (upazila, district) if p)}" if district else ""
    what = f"a rise in {', '.join(commodities)} prices" if event_type == "price_shock" else LABELS[event_type]
    return {
        "headline": title[:300], "headline_lang": "en",
        "summary": f"Collected automatically from a news search: {what} reported{where} by {outlet} on "
                   f"{published.isoformat()}. Headline only; open the link for details. Not checked by a person.",
        "source_name": outlet, "source_url": link, "published_date": published.isoformat(), "event_date": "",
        "event_type": event_type, "districts": district or "", "upazilas": upazila or "",
        "sectors": "|".join(sectors), "commodities": "|".join(commodities), "is_demo": "false",
        "curated_by": AUTO_CURATOR,
        # national price news: one event per commodity and day (rice and oil must not merge)
        "dedup_key": f"price_shock-{commodities[0].replace(' ', '_')}-{published.isoformat()}"
        if event_type == "price_shock" and not district else "",
    }


def collect(db: Session, today: date, client: httpx.Client) -> list[dict]:
    """Validated rows ready for news_service.import_rows. A failed search is
    logged and skipped; the rest still count."""
    rows: list[dict] = []
    searches: list[tuple[str, str | None, str | None]] = [
        (u or d, d, u) for d, u in watch_places(db)] + [(f'"{c}" price Bangladesh', None, None) for c in COMMODITIES]
    for query, district, upazila in searches:
        try:
            items = _search(client, query)
        except (httpx.HTTPError, ET.ParseError) as exc:
            log.warning("news search failed", extra={"error": type(exc).__name__})
            continue
        place = _names(upazila or district) if district else None
        for title, link, outlet, published, host in items:
            if published < today - timedelta(days=WINDOW_DAYS) or published > today:
                continue
            if district is None and not (_bd_outlet(host) or BD_WORDS.search(title)):
                continue  # national search: Bangladesh stories only
            if place is not None and not place.search(title):  # the place must be in the headline itself
                continue
            kind = classify(title)
            if kind is None or (district is None and kind[0] != "price_shock"):
                continue
            try:
                rows.append(news_service.validate_row(_row(title, link, outlet, published, kind, district, upazila),
                                                      today))
            except ValueError:
                continue
    return rows


def fetch(db: Session, today: date) -> ImportReport:
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "BonikBondhu-news/1.0"}) as client:
        return news_service.import_rows(db, collect(db, today, client))


def start_daily(hours: int) -> None:
    """Background daily run for the single app instance: once ~1 minute after
    start (so a host that sleeps refreshes on wake), then every `hours`."""
    from .core.clock import today
    from .db import get_sessionmaker

    def loop() -> None:
        time.sleep(60)
        while True:
            try:
                with get_sessionmaker()() as db, db.begin():
                    r = fetch(db, today())
                log.info("news fetch done", extra={"inserted": r.inserted, "updated": r.updated, "skipped": r.skipped})
            except Exception:  # never kill the thread; the next run retries
                log.exception("news fetch failed")
            time.sleep(hours * 3600)

    threading.Thread(target=loop, name="news-daily", daemon=True).start()
