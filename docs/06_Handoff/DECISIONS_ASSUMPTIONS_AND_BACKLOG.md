# DECISIONS, ASSUMPTIONS AND BACKLOG

**Document ID:** BB-DOC-14 · **Version:** 1.0 (12 Nov 2026) · **Owner:** Product/Research lead
**Read with:** `01_Product/MVP_SCOPE_AND_SOURCE_MAPPING.md`, `README.md`

This file is the single register for every decision in the blueprint. Other documents refer to IDs defined here (`DEC-xx`, `SUG-xx`, `ASM-xx`, `CON-xx`, `GAP-xx`, `BL-xx`).

---

## 0. Source IDs and citation rules

| ID | File | Access status (verified 12 Nov 2026) | Role |
|---|---|---|---|
| **MP** | `Bonik_Bondhu_Master_Prompt_Updated.md` | Read in full (§1–§24) | Explicit owner instructions. Overrides older scope/priority (MP §2). §23 (source-only) has highest priority. |
| **S1** | `Bonik_Bondhu_v3_1_Team_Plan_cleaned.docx` (in `Bonik_Bondhu_Updated_Documents.zip`) | Read in full (§0–§14, Appendix A–B) | Authoritative concept: F1–F12, L1–L3, accounting, datasets, risks, tests |
| **S2** | `Bonik_Bondhu_One_Page_Summary.docx` (in ZIP) | Read in full | Pitch summary, demo narrative |
| **S5** | `Bonik_Bondhu_3min_Video_Script.docx` (in ZIP) | Read in full | Video script, honesty labels, fallback table |
| **S6** | `Bonik_Bondhu_Complete_Source_Based_Architecture.md` (in ZIP) | Read in full | Consolidated architecture of S1–S4 |
| S3 | `EVENT.txt` | **UNAVAILABLE** — referenced by S6 §0, not in ZIP | Only S6 §16's secondhand summary is known |
| S4 | `judge.txt` | **UNAVAILABLE** — referenced by S6 §0, not in ZIP | Only S6 §16's secondhand rubric table is known |

Source IDs S1, S2, S3, S4 keep the numbering used inside S6 §0 so that citations stay consistent with the existing architecture file. S5 and S6 are new IDs for the two ZIP files S6 did not number.

**Tags used in all blueprint files**

| Tag | Meaning |
|---|---|
| `[SRC: …]` | Directly supported by a named source and section |
| `[DERIVED: …]` | Implementation detail that only operationalizes a sourced requirement (e.g. a column for a field S1 Appendix A1 requires). No new scope. |
| `[SUG-xx]` | **Suggestion (Not Approved; Outside Current Sources)** per MP §23 rule 3. Used as a *pending default* so documents are complete, but **must be approved before implementation** (Phase 0 task P0-T01). |
| `[GAP-xx]` | Information the sources do not contain; work is blocked or reduced until supplied |
| `DEMO` | Fictional synthetic data (MP §18). Never a real person, shop, lender or event. |

**No web research was performed** (MP §23 rule 4). External URLs inside S1 were **not opened**.

---

## 1. Decision log (source-backed)

| ID | Decision | Reason | Source |
|---|---|---|---|
| DEC-01 | Stack: **React + Vite + Tailwind** frontend, **Python FastAPI** backend, **PostgreSQL** database | All three named in sources; MP asks for one stack | S1 §8 (React or Next.js, Tailwind, FastAPI, PostgreSQL); S2 "FastAPI, PostgreSQL, React"; MP §10 (React/Vite, FastAPI) |
| DEC-02 | **Modular monolith**: one FastAPI app + one DB; no microservices/queues | Simplicity | MP §10, MP §17 rule 18 |
| DEC-03 | Roles: `owner` (shop and/or farm), `lender_officer`, `admin` (CLI only, no UI) | Three user types + minimal admin | MP §4; S1 §2 ("Platform admin … minimal build") |
| DEC-04 | One user → many `business_profiles`; profile has `activity_type` = `shop` or `crop_farm`; every owner record is keyed by `profile_id` | Multi-activity without two accounts | MP §5 |
| DEC-05 | Farmer MVP = **crop only**; poultry/fish/cattle deferred (no input schemas built) | Crop-first in both sources | MP §4B; S1 §5 ("one crop-finance estimator [SHOULD]… fish and cattle [ROADMAP]") |
| DEC-06 | **Farmer Buy/Sell page deferred** (design kept in BL-01) | S1 warns price/market screens risk drifting into another challenge; MP allows deferral; not needed for the financing journey | S1 §5 "Stay in our challenge"; S1 §12.1 "Do not build … Inventory ERP"; MP §4B |
| DEC-07 | **Text-first**; voice entry and voice advisor deferred | MP makes voice optional; S5 fallback table says show text if voice not reliable | MP §6 F1, F12; S5 "If something is not ready"; S1 §14 item 4 |
| DEC-08 | F1 = manual entry + optional receipt-photo extraction into a **draft that the user must confirm**; statements/khata import deferred | Never auto-save uncertain AI values | MP §6 F1; S1 F1 ("owner confirms before anything counts") |
| DEC-09 | F3 = transparent **rolling weekly baseline** (expected/low/high) + known scheduled payments; returns `insufficient_history` when data is thin; horizon ≤ 90 days | Simple, testable, ranges required | S1 F3; MP §6 F3 |
| DEC-10 | Assessment outcomes: `insufficient_information`, `not_affordable_base_case`, `ready_for_lender_review`; lender decision stored separately and only by lender | MP's five-way distinction; S1 F6 outcome vocabulary | MP §3; S1 F6 ("needs information / refer / ready for lender assessment") |
| DEC-11 | **No F8 optimizer** in MVP. Owner enters proposed repayment terms (labelled "your proposal, not a lender offer"); engine tests them | F8 is not one of the six MVP features; S1 says schedules are hypothetical until a lender documents them | MP §6, §7; S1 §14 item 6 |
| DEC-12 | **No Monte Carlo (F4)**. Deterministic due-date check under base low case and explicit scenarios | Simpler; S1 A2 requires due-date testing | MP §7 (reuse F4 internally only if needed); S1 Appendix A2 |
| DEC-13 | **No Business Health card (F5)**; show plain "record coverage" (weeks with records / weeks in window) only | Not in MVP six; avoid score-like numbers | MP §6, §17 rule 12; S1 F5 naming caution |
| DEC-14 | **No Repayment Gate (F6) logic**; declared obligations are shown and included in affordability | No 75% gate; lender reviews | S1 F6 (no universal gate); MP §7 |
| DEC-15 | L1 = **small curated news dataset** entered by the team with structured fields; no live crawling, no LLM news extraction in MVP | MP asks for limited verified source strategy | MP §6 L1; S1 L1 guardrails |
| DEC-16 | L2 = **Stage 1 only** (supplier list, concentration share, 7/14-day delay and 15% input-price scenarios); no GNN | Explainable rules | MP §6 L2; S1 L2 Stage 1 |
| DEC-17 | F12 = text advisor using **read-only, profile-scoped backend tools**; product help from a small static bilingual help table (vector RAG deferred) | AI explains, code calculates | MP §6 F12; S1 F12 |
| DEC-18 | Lender access flow: **officer requests with the owner's share code → owner approves sections + validity → officer reads**; expiry and revocation | Follows S1 F10; share code is S1's "Business ID is a locator only" | S1 F10; S5 2:05 scene (one-time code); see CON-06 |
| DEC-19 | Shared report = **frozen JSON snapshot + SHA-256** stored server-side; digital signature deferred | Integrity without key management in MVP | S1 F10 (snapshot + hash + signature) simplified |
| DEC-20 | **No NID** or identity documents collected in MVP | Minimal data | MP §8 |
| DEC-21 | **No OTP, no self-service password reset**; admin-assisted reset via CLI after offline identity check | Avoid insecure recovery | MP §8 |
| DEC-22 | LLM: **Gemini** as the single primary provider behind an adapter; fallback = **non-LLM path** (manual entry, template explanations) | Gemini named in both S1 and MP; MP prefers one primary | S1 §8; MP §11 |
| DEC-23 | Phase order changed: deterministic engine, supplier/news and lender review **before** AI integration | S1 kill switch: core thread must work before extras | MP §16 (reorder allowed); S1 §12.2 kill switch; S1 A5 |
| DEC-24 | Lender organizations/officers are created by a CLI command; no public lender sign-up | Manually provisioned accounts | MP §4C |
| DEC-25 | Evidence states in MVP: `declared` and `document_attached` only; others deferred | Others need reconciliation/issuers | S1 F1 table |
| DEC-26 | Counterparties in MVP: **suppliers only** (buyer concentration deferred) | MP L2 scope | MP §6 L2 |
| DEC-27 | "Farming expenses" stored as **transactions with `season_id`**, not a separate ledger | One ledger for both paths | MP §8 "same underlying data model"; MP §12 "no unnecessary tables" |
| DEC-28 | Proposed schedule types: `equal_installments` (weekly/monthly) and `single_payment` (e.g. after harvest) | Covers shop and S1 Boro example | S1 §5.1 Boro example; DEC-11 |
| DEC-29 | Affordability uses the **low case** (shop: lowest recent week; crop: low output × low price) | "even the low-income case covers repayment" | S1 §5.1 stage 1 |
| DEC-30 | News/supplier scenarios **never change the assessment status automatically**; they are shown as what-if results; news-proposed scenarios need owner confirmation | No adverse conclusion from one story | S1 L1 guardrail and step 6; MP §6 L1 |
| DEC-31 | Lender reads only the **approved snapshot**, never live tables | Scope cannot silently grow | S1 F10; MP §4C |
| DEC-32 | PDF export of case file deferred | Not required for working workflow | S1 §7 (export) → backlog |
| DEC-33 | Shop loans whose due dates go beyond the 90-day forecast horizon get `insufficient_information` (reason `term_beyond_forecast_horizon`) | Never extrapolate unsupported forecasts | S1 F3 (7/30/60/90-day horizons); MP §6 F3 |
| DEC-34 | Lender actions in MVP: mark under review, request information (visible to owner), add private note, record **demo decision** with reason | Working lender workflow, no disbursement | MP §4C; S1 §7 section 11 |
| DEC-35 | Starting cash for capacity = max(0, owner-declared current cash − cash committed to the purchase); if not declared → 0 with flag `starting_cash_unknown` | Avoid double-using purchase cash | S1 Appendix A2 (cash safely available); S1 F7 |
| DEC-36 | Loan disbursement and purpose spending are **excluded** from the repayment projection (assumed to net out); any excess of request over gap is **not** counted as repayment capacity | Conservative, simple | S1 F7 ("funding gap alone is not a recommended loan amount") |
| DEC-37 | Household withdrawal (monthly) is **required** before assessment and subtracted every day of the projection; per profile | "Subtracted in every affordability check" | S1 §3 table |

---

## 2. Suggestion register — Not Approved; Outside Current Sources (MP §23 rule 3)

These are proposals needed to make the blueprint buildable. Phase 0 task `P0-T01` asks the team/owner to approve, change or reject each. Until approved, implementation of the affected part must not start.

> **P0-T01 outcome (14 Nov 2026): SUG-01 … SUG-29 — all APPROVED as written by the project owner.** No SUG was changed or rejected. Implementation may use them. GAP-06 (team roles) and GAP-07 (host) remain open. Local dev note: PostgreSQL 16 is installed natively on Windows (no Docker on the dev machine); `docker-compose.yml` is kept for other machines.

| ID | Suggestion | Why it is needed | Affects | If rejected |
|---|---|---|---|---|
| SUG-01 | SQLAlchemy 2.x (ORM, parameterized queries) + Alembic migrations + Pydantic v2 schemas | FastAPI needs a DB layer; ORM prevents SQL injection | TRD, schema | Use psycopg with hand-written parameterized SQL + plain `.sql` migrations |
| SUG-02 | Password hashing **Argon2id** (`argon2-cffi`, library defaults) | MP requires "suitable algorithm" but names none | Auth | bcrypt (`passlib`/`bcrypt`) |
| SUG-03 | Opaque random session token (32 bytes) in `HttpOnly; Secure; SameSite=Lax` cookie; only SHA-256 of token stored in `user_sessions`; owner session 7 days, lender 8 hours absolute expiry | Session expiry + logout revocation (MP §8) | Auth, schema | JWT access token (shorter expiry, no revocation table) |
| SUG-04 | CSRF defence: SameSite=Lax + required header `X-BB-Client: web` on all non-GET requests + strict CORS allowlist | Cookie sessions need CSRF control | API, security | Bearer token in header (no cookies) |
| SUG-05 | Rate limits: 5 failed logins per phone → 15-min lock; 30 auth requests/10 min/IP; per-user daily AI caps: advisor 30 messages, photo extraction 10, purpose parsing 10 | Abuse + free-tier protection (MP §11) | API, AI | Different numbers |
| SUG-06 | Money as `NUMERIC(14,2)` + Python `Decimal`, ROUND_HALF_UP to paisa; currency fixed `BDT` | Exact arithmetic | Schema, engine | Integer paisa (`BIGINT`) |
| SUG-07 | Forecast parameters: 8-week look-back of complete 7-day blocks; minimum 4 blocks with ≥1 confirmed operating record; expected = mean, low = min, high = max of weekly net operating cash; blocks with no records = missing (not zero) | S1 requires validated minimum, not a fixed 60-day gate; something must be the initial value | Forecast | Other window/min; must be revisited after validation (S1 F5 note) |
| SUG-08 | Monthly household withdrawal → daily = monthly × 12 / 365 | Daily due-date projection | Engine | Weekly buckets |
| SUG-09 | Scenario effect models: **supplier delay** = lose (supplier share × expected daily net operating cash) for each delay day; **input price rise** = extra outflow (pct × supplier share × expected daily purchase payments) for the whole horizon | S1 gives scenario names, not formulas; S1 L1 says severity is an assumption | L2 engine | Other explicit formulas, always shown to users |
| SUG-10 | "High dependency" flag when top supplier share ≥ 50% (configurable) | S1 gives 65% only as an example | L2 | Show share only, no flag |
| SUG-11 | Over-request prompt when request > funding gap by any amount (tolerance 0%, configurable) | S1: "configurable tolerance … no 25% rule" | F7 | Another tolerance |
| SUG-12 | Crop scenarios: harvest price fall 15% below low price; yield shortfall 20% below low output; news event-type → scenario mapping in AI doc §6 | S1 lists crop risks (flood, pests, price fall) without parameters | Crop engine | Owner-chosen percentages |
| SUG-13 | Loan-cover price = (new repayment + other debts due by that date + reserve + remaining unpaid season costs − starting balance) ÷ low expected output | S1 §5.1 names the concept, not the formula | Crop summary | Omit loan-cover price |
| SUG-14 | Land units: acre (base), decimal = acre/100, sq ft = acre/43,560; **bigha has no default** — farmer must enter "1 bigha = __ decimal" | MP needs configurable local units; bigha varies | Season form | Remove bigha |
| SUG-15 | Specific Gemini model and SDK chosen by config `LLM_MODEL`; free-tier limits **NOT VERIFIED** (needs research approval, GAP-05) | Provider named in source, model not | AI | Another provider |
| SUG-16 | Frontend: TypeScript; libraries `react-router`, `react-i18next`, `lucide-react` icons; no chart library (simple bars in CSS); runtime versions Python 3.11+, Node 20 LTS | Routing, bilingual UI, icons, type safety | Frontend | Plain JavaScript / equivalent libraries |
| SUG-17 | Design tokens (colours, Noto Sans Bengali + system sans, spacing scale) in UI spec §2 | MP asks for limited palette; values not in sources | UI | Team-chosen palette |
| SUG-18 | Uploads: JPEG/PNG only, ≤ 5 MB, magic-byte check, Pillow re-encode (strips EXIF), random UUID filename on private disk path, never served publicly | Secure file upload (MP §13) | F1 | Disable photo upload |
| SUG-19 | Deployment: one container running FastAPI (also serving built React files) + PostgreSQL; HTTPS from hosting platform; Docker Compose for local Postgres. Host not chosen (GAP-07) | Simple deployment (MP §10) | TRD | Any single-VM option |
| SUG-20 | Testing tools: pytest + FastAPI TestClient (httpx); Vitest optional; Playwright optional for E2E (else manual scripted E2E) | MP §15 File 12 | Testing | Other tools |
| SUG-21 | Consent validity options 7 / 14 / 30 days (default 14) | S1 says "validity" without values | Consent | Other durations |
| SUG-22 | AI logs: metadata only (feature, provider, tokens, latency, status); no prompt/response text stored; 90-day retention | Privacy (MP §11) | AI, schema | Store redacted text |
| SUG-23 | Advisor numeric-grounding check: every number in the AI reply must appear in tool outputs of that turn, else return template answer | Enforce "never invents a number" | F12 | Prompt-only control (weaker) |
| SUG-24 | Phone format: Bangladesh mobile normalised to `+8801XXXXXXXXX`, accepted pattern `^(?:\+?88)?01[3-9]\d{8}$` | Login identifier | Auth | Looser validation |
| SUG-25 | Password policy: 8–128 chars, not purely digits, not equal to phone | Basic strength | Auth | Other policy |
| SUG-26 | UUID (v4, `gen_random_uuid()`) primary keys | Harder to enumerate; authorization still required | Schema | BIGSERIAL ids |
| SUG-27 | Calendar: phases mapped to 13 Nov – 25 Dec 2026 (Implementation Plan §2) | S1 §12.3 window ends 25 Dec; proposed fit for reduced scope | Plan | Team re-plans |
| SUG-28 | Duplicate-entry warning: same profile + type + amount + value_date (+ supplier if set) as a confirmed entry → user must tick "this is a separate entry" | S1 A4 duplicate rule needs a concrete matcher | F1 | Other matcher |
| SUG-29 | Lockout/admin CLI commands (`create-lender`, `reset-password`, `seed-demo`, `import-news`) | Manual provisioning | Ops | Other tooling |

### 2.1 Implementation suggestions raised in P3 and P4 (14 Nov 2026)
These fill gaps the sources do not settle. Each is cautious (can only make a result look *worse*, never better), does not change any golden number D1–D4, and is easy to switch off.

> **Outcome (14 Nov 2026): SUG-30 … SUG-44 — APPROVED; SUG-45 … SUG-54 added 15–16 Nov 2026 the same way.** The project owner delegated these
> implementation decisions to the AI developer (Claude) ("fix the gaps the plan leaves open"); they are
> recorded here so the team can still revisit any of them. SUG-32 is approved with a UI clarification:
> the household field says "only the part paid from this business — if you have a shop and a farm, split
> it, don't write the same money twice", so per-profile subtraction (DEC-37) does not double count.

| ID | Suggestion (implemented) | Why | Golden impact | Alternative |
|---|---|---|---|---|
| SUG-30 | Declared **overdue amount** = outflow on as_of; the regular schedule continues with outstanding − overdue | Ignoring money already owed would overstate capacity; total never exceeds declared outstanding | none (no overdue in seed) | Ignore overdue in projection (flag only) |
| SUG-31 | Past `next_due_date` dates are skipped **without** consuming the outstanding (flag `existing_debt_dates_outdated`) | Sources say "skip past dates" but not whether the balance shrinks; not shrinking keeps the burden visible | none | Consume skipped installments |
| SUG-32 | Farm check subtracts the profile's declared household withdrawal from as_of to harvest (pre-harvest) and harvest to due date | DEC-37 applies per profile; a farm with no pre-harvest income still feeds the household | none (D3 household = 0) | Household ignored for farms (reference formula) |
| SUG-33 | Farm with equal installments: every installment must fall on/after harvest; the last due date is the binding check | Reference covers a single payment only | none (D3 single) | Farm limited to single payment |
| SUG-34 | `terms_incomplete` also when the first due date is before as_of or the minimum reserve is missing | A schedule starting in the past cannot be checked | none | Accept and skip past dates |
| SUG-35 | `profile_location_missing` = district or upazila empty (status insufficient) | Location needed for news matching (L1) and lender profile | none (seed has both) | Flag only |
| SUG-36 | With an explanation, flag `request_exceeds_gap` is replaced by `over_request_explained` (request − gap still shown) | Plan P3-T11 "flag switches" | none | Show both flags |
| SUG-37 | **News relevance (P4).** `supplier_location` counts only when the event is relevant to that supply: event names no sector, or names the shop's sector, or one of its commodities is in the supplier's goods. Sector/commodity alone matches only events with no location (national news); for local events they are extra reasons after a location match. Location names are compared case/space-insensitively with a small alias list (Chittagong→Chattogram, Ashulia→Savar …) | Architecture §5.6 read literally makes D1 match the Dhamrai flood through Supplier C (spices) — contradicting golden §4.2 "Dhamrai flood **not** matched"; a crop-field flood does not stop a spice wholesaler, and a grocery-sector event 100 km away is noise without a location link | none — makes the golden hold | §5.6 literally (golden D1 changes) |
| SUG-38 | **News → scenario mapping details.** Supply events need a known share for the matched supplier (else signal only); start = max(event date, as_of); `price_shock` → shop input +15% on the top supplier share, farm only when the event's commodities are farm inputs (fertiliser, seed, diesel …) — a rice price rise is not a cost rise for a rice farmer; supplier-delay proposals are shop-only (a farm has no forecast) | SUG-12 mapping is per event type and silent on these cases | none | Mechanical mapping |
| SUG-39 | **Confirm = same inputs.** Confirming a news scenario re-evaluates the assessment's own inputs; if the profile changed (or the inputs hash differs) → 409 `ASSESSMENT_STALE`. A confirmed shortfall adds `scenario_shortfall` / `pre_harvest_cash_shortfall`; a confirmed single-source event adds `news_signal_single_source`. Status never changes (DEC-30) | Reproducibility; the stored hash proves the what-if used the checked inputs | none (flags only appear after the owner tests a news risk) | Recompute on current data |
| SUG-41 | **Snapshot privacy scrub (P5).** Besides labelling suppliers "Supplier 1/2/3" (by share), every string in the snapshot is scrubbed for supplier display names (case-insensitive, names ≥ 3 chars) — owner free text such as the purpose or over-request explanation can contain a supplier name. Item `price_source_note`, entry notes, documents, phone and email are never included | SEC-12 must hold for all text, not only the supplier section | none | Label the supplier section only |
| SUG-42 | **Snapshot extras.** Sections also carry what a lender needs to read them honestly: gap inputs, proposal rows, assessment formulas/inputs/parameters, `inputs_sha256`, debt evidence state, `source:"declared_by_owner"`; money summary covers the 8 weeks before the check; `transaction_list` = confirmed entries of those 8 weeks (date, type, amount, category, Supplier n, evidence) | API §5 shows an abbreviated example | none | Minimal example fields only |
| SUG-43 | **Owner may approve any allowed section** (not only the ones requested), shown as "not asked by lender"; mandatory profile + financing request; `forecast` shop-only, `season_summary` farm-only (422 otherwise). The approval needs the latest assessment of the chosen request to exist and be current (409 `ASSESSMENT_STALE`) | API §4.14 says "⊆ allowed keys" | none | Restrict to requested |
| SUG-44 | **Review rules.** A decision event is visible to the owner (with reason); after a decision, `status_change` → 409 and further `info_request`/notes keep the decision status; a new decision replaces the old one (all logged). Every case-file GET is a logged read, so reloads after review actions count as views. A duplicate open request from the same organisation gets the same 202 and is audited `denied` (`already_open`) | Spec silent on these edges | none | Other edge handling |
| SUG-45 | **Daily automatic news collection (15 Nov 2026, owner request).** CLI `fetch-news [--dry-run]` and, when `NEWS_FETCH_HOURS > 0`, a background run ~1 min after start then every N hours (single instance). Source: Google News RSS search (free, no key) for the upazilas of active profiles and suppliers (a district alone only if nobody there gave an upazila) + national commodity price searches; last 7 days. Fixed English keyword rules classify the headline (market fire, flood, blockade/hartal, eviction, factory closure, outbreak, price rise — a "cut/decline" headline is never a price rise); the place must be in the headline itself. Stored: headline, outlet, link, date + our own one-sentence summary (no article text); `curated_by = auto-news-search`; same validation, dedup and corroboration as the curated CSV; a person's curated event is never overwritten. UI/snapshot label: "Collected automatically — not checked by a person"; proposals still need the owner (DEC-30) | Real news ages out after 30 days (latest curated item 14 Nov → nothing real at the 18–25 Dec demo); hand curation every week is not realistic for a 5-person team | none (tests use no network; seed news unchanged) | Weekly hand curation only (DEC-15 as written); an LLM classifier (BL-11) later |
| SUG-46 | **Whole-word supplier scrub + farm-input news (fixes, 15 Nov 2026).** The SUG-41 scrub now replaces a supplier name only as a whole word (it turned "Quality" into "QuSupplier 1ty" for a supplier "Ali"; Bangla suffixes like "রহিমের" still match). A national `price_shock` on farm inputs (fertiliser, urea, seed, diesel …) now matches crop farms (reason `commodity`) — before, SUG-38's farm input rule could never trigger | Bugs found in the pre-P6 review | none | — |
| SUG-47 | **LLM adapter = one OpenAI-compatible HTTP client, Gemini + Groq (P6, 15 Nov 2026, owner chose free providers).** `ai/provider.py` calls `…/chat/completions` with `httpx` (already a dependency; no vendor SDK). Gemini (Google AI Studio OpenAI-compatible endpoint) is primary; Groq is the automatic fallback for text features (purpose, advisor) on timeout/429/5xx; receipt photos use Gemini only (vision). Models are settings: `LLM_MODEL` (text, default `gemini-flash-lite-latest` — higher free daily quota), `LLM_VISION_MODEL` (`gemini-flash-lite-latest`; live test 15 Nov: `gemini-flash-latest` returned 503 "high demand"/timeouts). Gemini tool calls carry a `thought_signature`; the adapter sends the provider's assistant message back unchanged (else 400). Empty model settings in `.env` fall back to these defaults, `GROQ_MODEL` (`openai/gpt-oss-120b`). JSON is requested in the prompt and validated with Pydantic (no vendor JSON mode). Free-tier limits change often and were read from third-party pages (official console to be checked, GAP-05); free-tier data may be used by the provider — fine for DEMO data, check terms before real users | Free tiers: Flash ≈ 20 req/day vs Flash-Lite ≈ 500/day; one advisor question costs 2–4 calls; one provider down must not stop the demo | none | Google SDK, single provider (BL-20 as written) |
| SUG-48 | **Advisor details.** Ten read-only tools bound to the session profile (no profile-id argument; extra arguments ignored); outputs use the lender snapshot's "Supplier 1/2/3" labels and are scrubbed again for supplier names; no notes, documents, phone, email or person names; debts as `lender_type` only. Up to 3 tool rounds, then one answer call. Grounding: every number in the reply must be in this turn's tool output, the user's message, today's date or 1–31; replies with forbidden words ("approved", "eligible", "credit score", "probability of default", "guaranteed", Bangla equivalents) also fail. A failed reply is replaced by the fixed answer for the tool the model used (`mode:"template"`). No LLM → 503 with `help_topics` = 8 bilingual help texts + 6 quick answers computed from the records; the UI shows them as buttons. Language = Bangla if the message has Bangla letters, else English if Latin, else the user's setting | AI doc §8 leaves these open | none | — |
| SUG-49 | **P6 UI/API details.** Owner nav = Home · Entries · Financing · Advisor · More (UI spec §4.1); "Add" stays on Home and Entries. `POST /transactions` accepts an owned `document_id`, so the manual path keeps the photo as evidence (FR-EXT-04: AI off/failed/limit → form pre-filled with the photo). Draft review happens on the normal entry form (unsure fields < 0.8 labelled, `unknown` type must be picked, Discard button). Purpose parse: AI items replace earlier unconfirmed AI items; quantity missing → 1, unit missing → "pcs"; the purpose text is supplier-name-scrubbed before sending; same text is cached per request in process memory (lost on restart). Uploads: magic bytes, ≤ 5 MB, > 40 MP refused, EXIF-upright then re-encoded ≤ 1600 px, SHA-256 of the original for the duplicate warning | Spec leaves these open | none | — |
| SUG-50 | **Changes from the real-provider measurements (P6-T08, 15 Nov 2026).** Receipts: prompt `receipt_v2` (seller's bill/"cash received" = purchase; d/m/y dates); a broken `\u` escape in model JSON is kept as text instead of rejecting the answer; a read date more than a year old gets confidence ≤ 0.5 (shown "unsure"). Advisor: prompt `advisor_v2` (Bangla digits + lakh grouping in Bangla, farms have no weekly forecast, no internal codes); the assessment tool returns plain-language status / missing items / flags and, when there is no saved or current check, works it out live without saving; a reply rejected for a forbidden phrase gets a fixed "the lender decides" answer. Results: `backend/tests/ai/reports/E2_report.md`, `E10_report.md` | E2 17/20 → 19/20 (tuned on the same synthetic set — optimistic); E10 9/20 → 16/20 | none | — |
| SUG-51 | **P7 deployment and hardening choices (15 Nov 2026).** Suggested host (GAP-07): Render free Docker web service + Neon free PostgreSQL (`render.yaml`, DEPLOY.md); uvicorn trusts proxy headers in the container (`--forwarded-allow-ips *`, per-phone lockout still applies); production refuses to start without a 16+ character `SECRET_SALT`; database errors are logged as type + SQLSTATE only; upload storage failure → 503 `doc.err.storage`; a missing photo file → 404; after a session expiry the owner/lender returns to the same screen (only paths inside their own area). Details: P7_STATUS.md | Hosting and log privacy gaps found in the P7 review | none | Other host; per-IP limit on the proxy IP |
| SUG-52 | **Receipts: keep the data, not the photo (owner request, 16 Nov 2026).** The uploaded image is kept only while the owner checks the entry; it is deleted when the entry is saved (AI draft confirmed or manual entry with the photo) or the draft is discarded. The `documents` row stays (SHA-256, size, upload time), so the duplicate-photo warning still works; the entry keeps type, amount, date, note and its own timestamps. Labels say "Entered from a photo (data kept, photo not stored)" | Free storage (Neon 1 GB), Render's disk is ephemeral anyway, receipts carry third-party names/phones (data minimisation), lenders never saw images (snapshot is data only) | none | Keep a small copy in object storage |
| SUG-53 | **Warning colour #975A00** (was #B26A00): WCAG AA contrast 5.2:1 on the page background (was 3.9:1). Measured for all tokens in `docs/06_Handoff/review/README.md` | P7-T02 accessibility | none | — |
| SUG-54 | **Automatic national news = Bangladesh only (16 Nov 2026).** A story from the national commodity-price searches (SUG-45) is kept only if the publisher is Bangladeshi (host ends `.bd`, first label ends `bd`, or a hand-kept outlet list) or the headline names Bangladesh/Dhaka; area searches are unchanged (place must be in the headline). Found on the live run: "Onion prices in Tajikistan rise 60%" was stored and matched grocery shops | A foreign price story must not become a Bangladeshi owner's risk signal; skipping an unlisted BD outlet only means one signal fewer | none (tests offline) | Country classifier / LLM (BL-11) |
| SUG-40 | **Concentration details.** Window = 56 days ending yesterday (same as the forecast); owner-reported shares are used as stated (not normalised — the owner may not list every supplier); scenario share rounded to 4 dp (0.6500); "sparse" note when not high-dependency and the basis is owner-reported or < 4 linked purchases | FR-SUP-03/06 give the rule, not these edges | none | Other edges |

---

## 3. Assumptions (stated, testable, revisit after evidence)

| ID | Assumption | Basis | How to check |
|---|---|---|---|
| ASM-01 | Owners can enter weekly totals instead of daily entries and still get a forecast | S1 §3, F5 | Usability test with interviewed owners (S1 §12.2) |
| ASM-02 | A user-entered expected output and price range is acceptable for the crop MVP because no yield/price dataset is available in sources | S1 §5 lists BBS/DAM but provides no data; GAP-03 | Replace with sourced data later |
| ASM-03 | Lenders in the demo are fictional organisations labelled DEMO | MP §4C; S1 §7.1 "never imply a partnership" | Demo checklist |
| ASM-04 | Current cash, reserve and household withdrawal are declared by the owner and labelled `declared` | S1 §3 | Shown in report evidence mix |
| ASM-05 | One demo lender organisation and two officer accounts are enough for the hackathon | MP §4C | Demo rehearsal |
| ASM-06 | Bangla is the default UI language; English available via switcher | S1 §2 "Bangla first"; MP §9 | UI review |

---

## 4. Source conflicts and resolutions

| ID | Conflict | Resolution | Basis |
|---|---|---|---|
| CON-01 | Delay example: 7 days (S1 §1.5) vs 14 days (S2, S5) | Both supported as scenario parameter (S1 L2 itself says "7 or 14-day") | S1 L2; S6 §14 |
| CON-02 | Registration content: S1 §3 starts with business type, location, capital request, debts; MP §8 wants only name/phone/email/password | MP wins; S1 items collected progressively later | MP §2, §8 |
| CON-03 | S1/S2 "Bangla voice first" vs MP "text first, voice optional" | Text first (DEC-07) | MP §6; S5 fallback |
| CON-04 | Frontend "React or Next.js" (S1) vs "React/Vite" (MP) | React + Vite | MP §10 |
| CON-05 | LLM options: S1 (Gemini, GPT-4o, Claude) vs MP (Gemini, Groq) | Gemini, the only overlap (DEC-22) | S1 §8; MP §11 |
| CON-06 | Lender access: S5 "owner shares a one-time code" vs S1 F10 "officer requests named report; owner approves" | Share code is the locator, approval happens in-app (DEC-18) | S1 F10; S5 |
| CON-07 | S1 "Must (December core)" includes optimizer, shortfall simulation, evidence states, report signature; MP six features exclude them | MP overrides scope: simplified or deferred (see scope map) | MP §2, §6, §7 |
| CON-08 | Land units: S1 bigha/decimal vs MP acre/sq ft | Support acre, decimal, sq ft, bigha (factor entered) | MP §4B; S1 §5; SUG-14 |
| CON-09 | S2 business model "lenders pay per review" vs S1 §7.2 "possible future model" | Out of MVP; treat as future, unvalidated | S1 §7.2 |
| CON-10 | S1 §12 dates (Oct submission, Dec build) predate this blueprint; today is 12 Nov 2026 | Re-plan within the remaining S1 window (SUG-27); preliminary submission outcome unknown (GAP-08) | S1 §12.3 |
| CON-11 | S1 §14 item 2 suggests renaming to "Dheu (ঢেউ)" | Keep "Bonik Bondhu" until team decides (S1 says companion files keep the name) | S1 §14 |

---

## 5. Gaps (not in sources — do not invent)

| ID | Missing information | Impact | Needed from |
|---|---|---|---|
| GAP-01 | `EVENT.txt` and `judge.txt` originals | Cannot verify event deadline/rubric beyond S6 §16 summary | Team uploads files |
| GAP-02 | Real lender-permitted repayment patterns, rates, fees | All terms are owner-entered proposals | Loan officer interviews (S1 §7.1) |
| GAP-03 | Crop yield and price datasets (BBS, DAM, TCB) — named in S1 §9 but no data supplied | Crop uses owner-entered ranges (ASM-02) | Team obtains files; web research approval |
| GAP-04 | Real curated news items for Bangladesh | MVP news set must be curated by team from real articles, or labelled DEMO | **Partly closed 14 Nov 2026:** owner approved web research; 7 real events (10 sources) for Dhaka/Gazipur in `data/news/curated_news.csv`, AI-assisted — still needs the P4-T08 second-person review |
| GAP-05 | Current Gemini/Groq free-tier limits, data-use terms | Budget/privacy cannot be confirmed | **Owner approval for web research** (MP §23 rule 5) |
| GAP-06 | Team size and role assignment | Plan assumes S1 §12.4 five roles; merge if fewer | Team |
| GAP-07 | Hosting provider for demo deployment | SUG-19 is generic | Team |
| GAP-08 | Result of 29 Oct preliminary submission / current event status | Plan cannot confirm judging timeline | Team |
| GAP-09 | Lender interview findings (S1 §7.1 "this week") | Lender portal fields unvalidated | Team |
| GAP-10 | Legal/privacy review in Bangladesh (S1 Appendix B) | No compliance claims possible | Qualified counsel before any real use |

---

## 6. Known limitations of the MVP (must be said honestly in demo)

1. Forecast is a simple rolling baseline; it is not validated on Bangladesh data (S1 F3, A3).
2. Due-date checks are deterministic scenario tests, **not** probability of default (S1 F4, §13.1).
3. Repayment terms are owner-entered proposals, not lender offers (S1 §14 item 6).
4. Supplier scenarios use explicit assumed formulas (SUG-09), not observed losses (MP §17 rule 17).
5. News data is a small curated set; coverage is incomplete; DEMO events are fictional (S1 L1 limits).
6. No phone/email ownership verification; accounts can be created with someone else's number (Security doc §2).
7. No CIB access; official checks stay with lenders (S1 F9).
8. Report hash shows the snapshot did not change after sharing; it does not prove the inputs are true (S1 F10).
9. AI extraction quality is unmeasured until E2 test set exists (S1 §10 E2).

---

## 7. Backlog (deferred functionality, with source of origin)

| ID | Item | Origin | Earliest phase after MVP |
|---|---|---|---|
| BL-01 | **Farmer Buy/Sell page** — design: simple listing (crop, quantity, unit, asking price, district, contact preference), owner-only create/close, no payments, no messaging; listing never feeds the financial engine. Reconsider only if it supports the loan journey (S1 §5 caution) | MP §4B | Post-hackathon |
| BL-02 | Voice entry (Whisper / Google STT fallback) and voice advisor | S1 F1, F12 | After E2 Bangla speech test |
| BL-03 | bKash/Nagad/bank statement import + reconciliation, evidence states `reconciled`, `counterparty_confirmed`, `issuer_attested`, `repaid_on_platform` | S1 F1 | Later |
| BL-04 | F4 Monte Carlo shortfall frequency + sensitivity bands | S1 F4 | Later |
| BL-05 | F5 Business Health card (Data Reliability 0–100, Repayment Stress L/M/H) | S1 F5 | After formula is disclosed and reviewed |
| BL-06 | F6 Responsible Borrowing Gate with lender-configured policies | S1 F6 | With a real lender |
| BL-07 | F8 constrained optimizer (OR-Tools/PuLP), shaped vs fixed comparison; RL stretch | S1 F8 | After lender terms (GAP-02) |
| BL-08 | F9 Capital Use & Repayment History | S1 F9 | Later |
| BL-09 | F10 digital signature of snapshots; PDF/JSON export | S1 F10, §7.1 | Later |
| BL-10 | F11 Early Warning alerts | S1 F11 | Later |
| BL-11 | L1 automated collection (GDELT, Bangla feeds), LLM event extraction, de-dup, E7 evaluation | S1 L1 | After labelled set (~400 headlines target, S1 §9.1) |
| BL-12 | L2 buyer concentration, counterparty confirmation, keyed pseudonyms, GNN Stage 2 | S1 L2 | Later |
| BL-13 | L3 Private Revenue Proof (Circom/snarkjs) | S1 L3 | Later |
| BL-14 | Poultry adapter; fish and cattle research estimators | S1 §5 | After crop validated |
| BL-15 | Crop yield/price defaults from BBS/DAM/TCB with date, level, unit | S1 §5, §9 | When GAP-03 closed |
| BL-16 | Vector RAG help (Chroma/FAISS) | S1 §8 | Later |
| BL-17 | Phone/email verification, secure password recovery, optional NID with legal basis | MP §8 | Before any real deployment |
| BL-18 | Synthetic 1,000-shop simulator calibrated to World Bank surveys | S1 §9.2 | Research track |
| BL-19 | Admin web UI (accounts, audit search) | S1 §2 | Later |
| BL-20 | Secondary LLM provider (e.g. Groq) adapter | MP §11 | If reliability requires |
