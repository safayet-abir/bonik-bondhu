# Curated news (L1, DEC-15)

`curated_news.csv` is the curated news list for the MVP. Import it with:

```bash
cd backend
python -m app.cli import-news ../data/news/curated_news.csv
```

## Rules (FR-NEWS-01..05, Architecture §7)

- One row = one **source** for an event. Rows that share a `dedup_key` are the same event
  reported by different sources; the first row is the one shown, and `source_count` = number of
  distinct sources (≥ 2 shows "Reported by several sources", 1 shows "Reported by one source — not confirmed").
- Store only the **headline as published**, the link, and a **short summary in our own words**
  (≤ 500 chars). Never copy article text.
- Real rows need an `http(s)` URL. DEMO rows (`is_demo=true`) must use `source_name = DEMO (fictional)`.
  The two DEMO events used by the demo script are in `backend/db/seed_demo.sql`, not here.
- Arrays (`districts`, `upazilas`, `sectors`, `commodities`) are `|`-separated. Use official
  spellings (Chattogram, Cumilla, Kaliakair …); common variants are normalised on match.
- `event_type` ∈ flood_waterlogging, market_fire, hartal_road_blockade, disease_outbreak,
  price_shock, policy_change, factory_closure_layoffs, market_eviction_relocation.
- Leave `sectors` empty when an event affects everyone in the area (e.g. a highway blockade).

## Provenance of the current list

Curated on 14 Nov 2026 with AI assistance (web search) for the demo districts Dhaka (Savar,
Dhamrai) and Gazipur (Kaliakair): 7 real events from 10 source articles. Headlines and dates were
taken from the publishers' pages as listed by search; summaries are our own. **Plan P4-T08 asks for
a review by a second person**: open each link, check the headline, dates and districts, then change
`curated_by` to the reviewer's initials. Real news ages out of matching 30 days after publication.
