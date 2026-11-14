# IMPLEMENTATION PLAN — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-11 · **Version:** 1.0 (12 Nov 2026)
**Inputs:** all documents in this blueprint. **Rule:** a phase is complete only when its Definition of Done and critical tests pass `[SRC: MP §16]`. Build the first vertical slice early and extend a working system `[SRC: MP §16]`. Core financial thread before AI extras `[SRC: S1 §12.2 kill switch; DEC-23]`.

---

## 1. Phase overview

| Phase | Name | Ends with (testable) | Depends on |
|---|---|---|---|
| P0 | Foundation & approvals | Repo runs locally; SUG items approved; DB migrated | — |
| P1 | Auth, profiles, **first vertical slice** | Register → login → profile → save entry → reload → correct summary | P0 |
| P2 | Financial data engine | Full ledger types, void, duplicates, debts, suppliers, crop seasons | P1 |
| P3 | First working financial assessment | Forecast, financing request, gap, due-date/crop checks, statuses (D1–D4 golden pass) | P2 |
| P4 | External intelligence (deterministic) | Supplier concentration, scenarios, curated news matching | P3 |
| P5 | Consent & lender review | Request → approve → snapshot → lender reads → events → revoke/expiry | P3 (P4 optional sections) |
| P6 | AI integration | Receipt draft, purpose parse, grounded advisor, all with fallback | P2 (extraction), P3 (purpose/advisor) |
| P7 | Integration, testing, deployment, demo | Deployed build passes E2E shop + farm scripts and SEC tests | P1–P6 |

Phase order differs from MP §16's example (AI moved after lender review) — see DEC-23.

### 1.1 Proposed calendar `[SUG-27 — Not Approved]`
Remaining window per S1 §12.3 ends 25 Dec 2026.

| Phase | Dates (2026) | Working days |
|---|---|---|
| P0 | 13–14 Nov | 2 |
| P1 | 15–18 Nov | 4 |
| P2 | 19–24 Nov | 6 |
| P3 | 25 Nov – 1 Dec | 7 |
| P4 | 2–5 Dec | 4 |
| P5 | 6–11 Dec | 6 |
| P6 | 12–17 Dec | 6 |
| P7 | 18–25 Dec | 8 |

**Kill switches** (adapted from S1 §12.2):
- KS-1 (end of 1 Dec): if D1–D4 golden assessment tests do not pass → stop P4 news work; keep supplier scenarios only.
- KS-2 (end of 12 Dec): if lender flow (P5) is not working end-to-end → P6 reduced to `LLM_PROVIDER=none` fallbacks (help menu + manual entry); no LLM features in demo.
- KS-3 (20 Dec): feature freeze; only bug fixes, tests, deployment, rehearsal.

### 1.2 Team roles (S1 §12.4, merge if fewer people — GAP-06)
| Role | Owns in this plan |
|---|---|
| Finance/backend lead | engine/*, ledger, assessment, consent services, golden tests |
| AI/data lead | ai/*, news curation, demo data, E2/E10 sets |
| Security lead | core/*, SEC tests, upload handling, deployment hardening |
| Frontend lead | all screens, i18n files, accessibility |
| Product/research lead | SUG approvals, microcopy review, lender interview, demo script, video |

---

## 2. Conventions for every task

- **Task ID** `Px-Tyy`. Each task lists files, inputs/outputs, how it connects, and how to verify.
- Branch per task; PR must include tests; reviewer checks the Security checklist items touched.
- Backend first, then the screen that uses it (MP §16: no screens before functionality).
- Use names exactly as in `DATABASE_SCHEMA.md` and `API_SPECIFICATION.md`.

---

## 3. Phase P0 — Project foundation & approvals

**Objective:** a running skeleton, approved decisions, migrated database.
**Prerequisites:** team access to repo; this blueprint read by all.

| Task | What to build | Where | Verify |
|---|---|---|---|
| P0-T01 | **Approve / change / reject every SUG-xx** in `DECISIONS…md` §2; record outcome column; decide GAP-06 roles, GAP-07 host | `docs/06_Handoff/DECISIONS…md` | All SUG rows marked Approved/Changed/Rejected |
| P0-T02 | Create repo structure exactly as TRD §2; `.gitignore` (`.env`, `node_modules`, `.venv`, `uploads/`) | root | Tree matches |
| P0-T03 | `docker-compose.yml` with `postgres:16` (db `bonik_bondhu`, user `bb`), healthcheck | root | `docker compose up -d db` healthy |
| P0-T04 | Backend skeleton: `create_app()`, `config.py` (all env vars TRD §6), `db.py`, `GET /api/v1/health` | `backend/app/` | `curl /api/v1/health` → ok |
| P0-T05 | Alembic init; revision `0001_initial` executes `schema.sql` | `backend/migrations/` | `alembic upgrade head` creates 24 tables |
| P0-T06 | Copy `reference_calculations.py` into `backend/tests/golden/` and add `test_reference_runs.py` that asserts golden JSON (TESTING §4) | tests | `pytest tests/golden` passes |
| P0-T07 | Frontend skeleton: Vite React TS, Tailwind with tokens (UI spec §2), `react-i18next` with `bn.json`/`en.json` seeded from UI spec §7.3, router with placeholder pages **only for routes needed in P1** | `frontend/` | `npm run dev` shows SCR-A01 with language switch |
| P0-T08 | API client (`api/client.ts`) with credentials, `X-BB-Client`, error mapping | `frontend/src/api` | Unit test or manual call to `/health` |
| P0-T09 | CI: pytest, i18n key-parity script, frontend build, secret grep in `dist/` | `.github/workflows/ci.yml` (or equivalent) | CI green |
| P0-T10 | Shared components: Button, Field, AmountInput (accepts Bangla digits), Card, StatusBanner, DemoBadge, EmptyState | `frontend/src/components` | Storybook not required; visual check |

**Tests:** health endpoint test; golden reference test; CI pipeline.
**Expected deliverable:** skeleton app + empty DB schema + green CI.
**Completion checklist:** ☐ SUG decisions recorded ☐ DB migrated ☐ health OK ☐ frontend runs ☐ CI green.
**Definition of Done:** any team member can clone, follow TRD §7, and see the welcome screen talking to `/health`.
**Common problems:** Postgres port clash → change host port; Alembic can't find models → use `op.execute(open(schema.sql).read())`; Bangla font not loading → self-host font files in `public/fonts`.

**End-of-phase answers:** (1) Working: skeleton + health. (2) DB: empty schema. (3) User can: open welcome page, switch language. (4) Test: `pytest`, CI. (5) Before P1: SUG-02/03/04/05/24/25/26 approved (auth-related).

---

## 4. Phase P1 — Authentication, profiles, first vertical slice

**Objective:** register → login → create profile → save one entry → reopen → see correct summary `[SRC: MP §16]`.
**Prerequisites:** P0 DoD; auth SUGs approved.

| Task | What | Files | Inputs → Outputs | Verify |
|---|---|---|---|---|
| P1-T01 | Models `User`, `UserSession`, `BusinessProfile`, `Transaction` (SQLAlchemy, mirror schema) | `models/user.py`, `profile.py`, `ledger.py` | — | import & simple insert test |
| P1-T02 | `core/security.py`: `hash_password`, `verify_password` (Argon2id), `new_session_token()`, `sha256_hex()` | core | password → hash | unit tests (hash ≠ password; verify true/false) |
| P1-T03 | `auth_service.register/login/logout`; phone normalisation `+8801…`; lockout; dummy verify; audit | services | `RegisterIn` → user; `LoginIn` → session | API tests FR-AUTH-01..07 |
| P1-T04 | `core/deps.py`: `current_user`, `require_owner`, `require_lender`, `get_owned_profile`; `core/csrf.py`; `core/errors.py` | core | cookie → user | SEC-01, 02, 03, 16 |
| P1-T05 | Routers `/auth/*` (register, login, logout, me, PATCH me) | `api/auth.py` | API spec §4.2 | TestClient |
| P1-T06 | `profile_service` + `/profiles` routes (list, create with random share code, get, patch) | `services/profile_service.py`, `api/profiles.py` | §4.3 | FR-PROF-01..05 tests |
| P1-T07 | **Slice ledger**: `ledger_service.create` for `sale_cash`, `operating_expense` only; `engine/accounting.py` with full TXN_EFFECTS table; `summary_service` | engine, services, `api/transactions.py` | entry → row; summary aggregates | E1 subset; reload test |
| P1-T08 | Frontend: SCR-A02 Register, SCR-A03 Login (role routing), SCR-O02 Create profile (minimal), SCR-O01 chooser, header with profile + language | `pages/auth`, `pages/owner` | — | Manual flow on 360 px |
| P1-T09 | Frontend: SCR-O03 Home (returning variant: today/month totals), SCR-O04 Add entry (2 types), SCR-O07 Summary (basic) | pages/owner | — | Save entry, refresh browser, totals persist |
| P1-T10 | Seed 1 lender via CLI `create-lender` (needed later; proves role routing) | `cli.py` | org/officer | Lender login lands on placeholder SCR-L01 |

**DB changes:** none beyond schema (rows only).
**Integration:** frontend↔backend via Vite proxy; cookies same-origin.
**Tests:** FR-AUTH-01..07, FR-PROF-01..05, SEC-01/02/03/06/07/15/16, slice summary test (sale 8,500 + rent 1,500 → net operating 7,000).
**Deliverable:** working vertical slice.
**Completion checklist:** ☐ register/login/logout ☐ lockout ☐ profile create/list ☐ entry saved and summary correct after reload ☐ owner cannot read other profile ☐ lender cannot use owner routes.
**DoD:** demo of the slice on a phone-sized browser + all listed tests green.
**Dependencies:** none other than P0.
**Common problems:** cookie not set in dev → ensure same origin via proxy and `SameSite=Lax`; `Secure` cookie on http localhost → only set `Secure` when `APP_ENV=production`; timezone off-by-one → compute business dates in Asia/Dhaka.

**End-of-phase answers:** (1) Accounts, sessions, profiles, two entry types, summary. (2) `users`, `user_sessions`, `business_profiles`, `transactions`, `audit_logs`, `lender_*`. (3) Register, log in, create shop/farm profile, record cash sale/expense, see totals. (4) API tests + manual slice. (5) All 12 transaction types and void before P2 screens.

---

## 5. Phase P2 — Financial data engine

**Objective:** complete, correct ledger for shops and farms; debts; suppliers; crop seasons.
**Prerequisites:** P1 DoD.

| Task | What | Files | Verify |
|---|---|---|---|
| P2-T01 | All 12 `txn_type`s with link rules (supplier/debt/season), validation (amount, date ≤ today+1), idempotency `client_request_id` | `ledger_service`, `schemas/ledger.py` | FR-LED-01..04, 10 |
| P2-T02 | Duplicate detection (SUG-28) → 409 with existing summary; `confirm_duplicate` path | ledger_service | FR-LED-05 |
| P2-T03 | Void endpoint; voided rows excluded everywhere | ledger_service | FR-LED-06 |
| P2-T04 | Full summary (all fields FR-LED-08, evidence mix, record coverage) | summary_service | **E1 golden fixture** exact match |
| P2-T05 | `bump_data_version(profile)` helper called by all input-changing services | profile_service | unit test |
| P2-T06 | Debts: models, `debt_service` CRUD, declare-none, `engine/schedules.existing_debt_schedule` | services, engine, `api/debts.py` | FR-DEBT-01..03; schedule unit tests (weekly/monthly/single, outstanding cap, skip past dates) |
| P2-T07 | Suppliers CRUD (no concentration yet) | `supplier_service`, `api/suppliers.py` | FR-SUP-01/02 |
| P2-T08 | Seasons: `engine/units.to_acres` (SUG-14), season CRUD, cost items, harvest, season summary (income range, planned/paid totals, break-even) | `season_service`, `engine/crop.py`, `api/seasons.py` | FR-SEA-01..06,08; units golden (150 decimal → 1.5 acres; 21,780 sq ft → 0.5; 2 bigha @33 → 0.66) |
| P2-T09 | Frontend: SCR-O04 all types with helper rules, SCR-O06 list/detail/void, SCR-O07 full summary, SCR-O09 debts, SCR-O08 supplier list (no chart yet) | pages/owner | manual + i18n parity |
| P2-T10 | Frontend farm: SCR-F01, SCR-F02 (unit + bigha factor), SCR-F03 (plan + "Paid" → entry prefilled), SCR-F04, SCR-F05 (without loan-cover) | pages/farm | manual |
| P2-T11 | Profile-type guards (`PROFILE_TYPE_MISMATCH`) for season/forecast endpoints | deps | API tests |

**DB changes:** none (all tables exist); start using `debt_facilities`, `suppliers`, `farming_seasons`, `season_cost_items`.
**Tests:** E1 fixture; FR-LED-*, FR-DEBT-*, FR-SEA-*; SEC-04/05/18; unit tests for schedules & units.
**Deliverable:** shop and farm owners can record everything the assessment needs.
**Completion checklist:** ☐ 12 types ☐ duplicates ☐ void ☐ E1 passes ☐ debts + declare-none ☐ suppliers ☐ seasons with units ☐ farm never sees forecast.
**DoD:** E1 golden + all P2 API tests green; manual walkthrough shop + farm.
**Dependencies:** P1.
**Common problems:** generated columns not writable → never send `total_cost/line_total`; Decimal serialised as float → configure Pydantic to serialise `Decimal` as string; monthly schedule on 31st → use `add_months` clamp (reference code).

**End-of-phase answers:** (1) Full ledger, debts, suppliers, seasons. (2) Plus debts, suppliers, seasons, cost items. (3) Record any money event; manage loans, suppliers, seasons; see correct totals. (4) Golden E1 + API tests. (5) Forecast and financing need correct weekly aggregates → verify with seed D1 before P3.

---

## 6. Phase P3 — First working financial assessment

**Objective:** forecast, financing request with gap, deterministic assessment with honest statuses.
**Prerequisites:** P2 DoD; SUG-06/07/08/11/13 approved.

| Task | What | Files | Verify |
|---|---|---|---|
| P3-T01 | `engine/baseline.py` (weekly blocks, min weeks, expected/low/high, horizons) | engine | golden D1, D2, D4 baselines |
| P3-T02 | `forecast_service` + routes (shop only), store `forecast_runs`, `is_stale` | services, `api/forecasts.py` | FR-FC-01..06 |
| P3-T03 | Financing request CRUD + items CRUD + copy from season cost items + live `preview` | `financing_service`, `api/financing.py` | FR-FIN-01,02,04,05,07,08 |
| P3-T04 | `engine/funding.py` (gap), `engine/schedules.new_loan_schedule` (rounding: last installment absorbs) | engine | golden gaps 150,000/70,000/40,000; D1 installments 12×18,000 |
| P3-T05 | `engine/projection.py` daily low-case projection + due-date checks + scenario hooks | engine | golden D1 base (min 21,626.22), D2 first shortfall as_of+7 (2,746.97) |
| P3-T06 | `engine/crop.py` crop check, break-even, loan-cover | engine | golden D3 (available 64,600; loan-cover 19.78; break-even 19.70) |
| P3-T07 | `assessment_service`: completeness → missing codes; status rules; flags; explanation JSON; inputs hash; data_version | services, `api/assessments.py` | D1 ready, D2 not affordable, D3 ready, D4 insufficient (6 codes) |
| P3-T08 | Forbidden-words test on assessment payloads (FR-ASM-07) | tests | passes |
| P3-T09 | CLI `seed-demo` + `reset-demo` (runs `seed_demo.sql`, sets demo password hashes) | `cli.py` | seed on fresh DB; golden via API equals reference |
| P3-T10 | Frontend: SCR-O10 Forecast; SCR-O11 wizard steps 1–5 with autosave PATCH; SCR-O12 Result + How-calculated tabs; SCR-F05 loan-cover | pages | manual D1–D4 |
| P3-T11 | Owner explanation for over-request (`over_request_explanation`) | financing_service + UI | flag switches to `over_request_explained` |

**DB changes:** `forecast_runs`, `financing_requests`, `financing_request_items`, `financial_assessments` used.
**Tests:** golden D1–D4 through engine **and** through API on seeded DB with fixed `as_of_date`; FR-ASM-01..09.
**Deliverable:** the core "can this repayment fit my cash?" answer, honest and explained.
**Completion checklist:** ☐ forecast ok/insufficient ☐ gap ☐ schedules ☐ shop checks ☐ crop checks ☐ 3 statuses ☐ stale detection ☐ forbidden words absent ☐ seed/reset CLI.
**DoD:** all golden cases pass via API; KS-1 checkpoint met.
**Dependencies:** P2.
**Common problems:** off-by-one in week blocks → blocks are `[as_of−7k, as_of−7k+6]`; installments beyond 90 days → must give `term_beyond_forecast_horizon`; float drift → Decimal everywhere, quantize only for output.

**End-of-phase answers:** (1) Forecast + assessment. (2) Forecast runs, requests, items, assessments. (3) Get a status with reasons, gap and due-date results. (4) Golden tests D1–D4. (5) Scenario hooks in projection must exist (done in P3-T05) before P4.

---

## 7. Phase P4 — External intelligence (deterministic L1/L2)

**Objective:** connect supplier dependency and curated news to the assessment as what-if scenarios.
**Prerequisites:** P3 DoD; SUG-09/10/12 approved; curated news CSV started (AI/data lead).

| Task | What | Files | Verify |
|---|---|---|---|
| P4-T01 | `engine/concentration.py` + `supplier_service.concentration` (linked vs owner-reported vs none) + route | engine, services | D1 shares 65/25/10, flag true; FR-SUP-03..06 |
| P4-T02 | Auto scenarios at assessment: shop delay 7 & 14 days, price +15% (top supplier); farm price −15%, yield −20%, inputs +15% | `scenario_service` | golden D1 scenarios (delay7 first shortfall as_of+7: 9,376.90; delay14: 12,377.35; price+15 first shortfall as_of+14: 4,465.12); D3 scenarios |
| P4-T03 | Flag `scenario_shortfall` / `pre_harvest_cash_shortfall` without changing status | assessment_service | DEC-30 test |
| P4-T04 | `import-news` CLI (CSV → validate → upsert by dedup_key, source_count) | `cli.py`, `news_service` | invalid rows rejected with report |
| P4-T05 | News matching rules (Architecture §5.6) + `/news-signals` | `news_service`, `api/news.py` | D1 matches blockade via supplier location; D3 matches flood via upazila; D1 does **not** match Dhamrai flood |
| P4-T06 | News-proposed scenarios (`origin=news`, `proposed`) + confirm/dismiss endpoints | `scenario_service`, `api/scenarios.py` | FR-NEWS-04 |
| P4-T07 | Frontend: SCR-O08 dependency bars + notes; SCR-O12 Risks tab + News tab (cards, confirm/dismiss, DEMO badge, single-source label) | pages | manual |
| P4-T08 | Curate ≥ 5 real news items for demo districts (with URLs) + 2 DEMO events (already in seed) | `data/news/curated_news.csv` | review by second person |

**Tests:** golden scenario values; matching tests; empty-news test (FR-NEWS-06); status-unchanged test.
**Deliverable:** L1 and L2 meaningfully connected to the financial analysis.
**Completion checklist:** ☐ concentration ☐ auto scenarios ☐ news import ☐ matching ☐ proposals confirm/dismiss ☐ UI tabs.
**DoD:** D1 and D3 show scenarios and news exactly as golden; empty news table causes no errors.
**Dependencies:** P3.
**Common problems:** district spelling variants → keep a canonical list (team-maintained) and normalise case/whitespace; scenario start date in past → default to `as_of`.

**End-of-phase answers:** (1) Supplier dependency, scenarios, news signals. (2) `risk_scenarios`, `news_events`. (3) See what-ifs and relevant news with sources. (4) Golden + matching tests. (5) Snapshot builder needs scenario/news JSON shapes fixed (API §5).

---

## 8. Phase P5 — Consent and lender review

**Objective:** working lender workflow with consent, snapshot, audit, expiry and revocation.
**Prerequisites:** P3 DoD (P4 for optional sections); SUG-21 approved.

| Task | What | Files | Verify |
|---|---|---|---|
| P5-T01 | `POST /lender/access-requests` (generic 202, rate limit, audit) | `lender_service`, `api/lender.py` | SEC-13 |
| P5-T02 | Owner consents list/approve/decline/revoke/reshare/activity | `consent_service`, `api/consents.py` | FR-CON-02..09 |
| P5-T03 | `snapshot_service.build(consent, sections)` per API §5; supplier label mapping; canonical JSON + SHA-256; store `shared_reports` | services | SEC-12; hash recomputation test |
| P5-T04 | `get_authorized_consent` guard + case list + case file + read audit | core/deps, lender_service | SEC-08/09/10/11 |
| P5-T05 | Lender events: status_change, note (private), info_request (owner-visible), decision (+reason); `lender_reviews` upsert | lender_service | FR-LEN-04..06 |
| P5-T06 | Frontend owner: SCR-O14 Sharing (code, requests, approve sheet, active shares, revoke, messages) | pages/owner | manual |
| P5-T07 | Frontend lender: SCR-L01 list (tabs), SCR-L02 request, SCR-L03 case file + review panel, CIB notice, decision banner | pages/lender | manual desktop |
| P5-T08 | Seed: second org officer for isolation tests (already in seed) | — | SEC-09 |

**Tests:** FR-CON-*, FR-LEN-*, SEC-06..13; expiry with clock override (inject `now` provider in service).
**Deliverable:** full owner → lender flow.
**Completion checklist:** ☐ request ☐ approve with subset ☐ snapshot hash ☐ lender read logged ☐ info request reaches owner ☐ decision banner ☐ revoke/expiry block access ☐ other org blocked.
**DoD:** E2E: D1 owner shares with DEMO Bank; officer reviews and records "refer" with reason; owner revokes; officer blocked. KS-2 checkpoint met.
**Dependencies:** P3, (P4).
**Common problems:** snapshot includes unapproved keys → build from allowlist dict; timezone in `valid_until` → store UTC, display Asia/Dhaka.

**End-of-phase answers:** (1) Consent + lender portal. (2) `consents`, `shared_reports`, `lender_reviews`, `lender_review_events`, audit rows. (3) Owner controls sharing; lender reviews and records a demo decision. (4) SEC + E2E. (5) Advisor tools can read consent status for "who viewed my report?" (optional).

---

## 9. Phase P6 — AI integration

**Objective:** add useful, safe AI on top of a working system; everything degrades gracefully.
**Prerequisites:** P5 DoD (or KS-2 reduced scope); GAP-05 resolved by team verification of provider terms/limits; SUG-15/22/23 approved; `GEMINI_API_KEY` in server env.

| Task | What | Files | Verify |
|---|---|---|---|
| P6-T01 | `ai/provider.py` protocol, `none_provider.py`, `gemini_provider.py`, timeout, output token limit, error mapping | ai | provider contract tests with fake provider |
| P6-T02 | `ai/budget.py` daily caps from `ai_interactions`; metadata logging | ai | cap test (31st advisor msg → 429) |
| P6-T03 | Documents upload (validation, re-encode, private storage, content endpoint) | `document_service`, `api/documents.py` | SEC-17; FR-EXT-01 |
| P6-T04 | Receipt extraction → draft; confirm/discard; supplier name mapping; duplicate-photo warning | `ai/extraction.py`, `api/extraction.py` | FR-EXT-02..05 with mocked provider; SEC-20 |
| P6-T05 | Purpose parse → unconfirmed items (no prices); cache by text hash | `ai/purpose.py` | FR-FIN-03 |
| P6-T06 | Advisor: tools registry (AI doc §8.1), tool loop (≤ 3 rounds), system prompt, grounding validator, templates, help topics JSON | `ai/advisor.py`, `ai/tools.py`, `ai/grounding.py`, `help/help_topics.json` | FR-ADV-01..08; SEC-19; grounding unit tests |
| P6-T07 | Frontend: SCR-O05 photo + draft review; wizard "Make list from my text"; SCR-O15 advisor with chips & fallback mode; AI consent text; settings privacy note | pages | manual with AI on and with `LLM_PROVIDER=none` |
| P6-T08 | Build E2 receipt set (≥ 15, target 30) and E10 gold questions (20); run and record results honestly | `tests/ai/` | report file with N and pass counts |

**Tests:** all AI features with fake provider (deterministic); NFR-03 full run with `none`; E2/E10 measured (not pass/fail gates, but must be reported truthfully).
**Deliverable:** AI-assisted entry, purpose structuring, grounded advisor.
**Completion checklist:** ☐ provider switch by env ☐ caps ☐ uploads safe ☐ drafts never auto-saved ☐ AI never sets prices ☐ advisor grounded ☐ fallbacks work ☐ E2/E10 results recorded.
**DoD:** app passes the full E2E with AI on and with AI off.
**Dependencies:** P2 (ledger), P3 (assessment), P4 (news tools).
**Common problems:** provider returns prose instead of JSON → enforce schema/JSON mode in adapter and validate; Bangla digits in amounts → normalise before Decimal; large photos slow → downscale before sending.

**End-of-phase answers:** (1) Photo drafts, purpose parsing, advisor. (2) `documents`, `extraction_drafts`, `ai_interactions`. (3) Snap receipts, list items from text, ask questions in Bangla/English. (4) Fake-provider tests + E2/E10 reports. (5) Freeze features; move to P7.

---

## 10. Phase P7 — Integration, testing, deployment, demo

**Objective:** stable deployed build, verified security, rehearsed honest demo.
**Prerequisites:** P1–P6 DoD (or documented kill-switch reductions).

| Task | What | Verify |
|---|---|---|
| P7-T01 | i18n completeness: every key in bn/en; Bangla copy review by a native speaker; number formatting | CI parity + review sign-off |
| P7-T02 | Accessibility & mobile pass (360 px, touch targets, labels, contrast) | UI checklist |
| P7-T03 | Run full test suite + SEC-01..20 + DB constraint script on staging DB | all green |
| P7-T04 | Security checklist (Security doc §6) signed | checklist |
| P7-T05 | Deploy per TRD §8 (host GAP-07); HTTPS; env secrets; `alembic upgrade`; `seed-demo` | `/health` ok on URL |
| P7-T06 | E2E scripts (Testing §8): Shop D1, Farm D3, Lender, Exceptions | pass on deployed URL |
| P7-T07 | Demo rehearsal ×3 with timer; backup screen recording of full demo | recording saved |
| P7-T08 | Update `HACKATHON_DEMO_AND_HANDOFF.md` "What is real" list with measured facts only | review |
| P7-T09 | Bug triage: only P0/P1 bugs fixed after 20 Dec (KS-3) | issue list |

**DoD:** all critical tests pass on deployed build; demo runs in ≤ 4 min per path without DB edits; demo readiness checklist complete.

**End-of-phase answers:** (1) Everything in MVP scope, deployed. (2) Real + demo data separated. (3) Full journeys for shop, farm, lender. (4) E2E + SEC + golden. (5) Post-hackathon: backlog BL-xx, GAP closure.

---

## 11. The actual first development task

**P0-T01** — approve/change/reject the SUG register (one meeting, ~1 hour), immediately followed by **P0-T02…P0-T05** (repo, Postgres, backend skeleton with `/health`, Alembic migration from `schema.sql`). First code commit target: `GET /api/v1/health` returning `{"status":"ok","db":"ok"}` against the migrated database.
