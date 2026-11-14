# TECHNICAL REQUIREMENTS DOCUMENT (TRD) — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-05 · **Version:** 1.0 (12 Nov 2026)
**Depends on:** `PRD.md`, `DATABASE_SCHEMA.md` · **Referenced by:** `SYSTEM_ARCHITECTURE.md`, `API_SPECIFICATION.md`, `IMPLEMENTATION_PLAN.md`

---

## 1. Selected stack (one recommendation)

| Layer | Choice | Status | Why |
|---|---|---|---|
| Frontend | **React + Vite**, **Tailwind CSS**, TypeScript | React/Vite: MP §10; Tailwind: S1 §8; TypeScript: **SUG-16** | Fast dev server, simple static build, students know React |
| Frontend libs | `react-router`, `react-i18next`, `lucide-react` | **SUG-16** | Routing, bilingual UI, icons; no chart library |
| Backend | **Python FastAPI** (modular monolith) | S1 §8; S2; MP §10; DEC-02 | Python suits finance/AI code; automatic OpenAPI |
| Validation | Pydantic v2 | SUG-01 | FastAPI native |
| DB access | SQLAlchemy 2.x + Alembic; driver `psycopg` | SUG-01 | Parameterized queries, migrations |
| Database | **PostgreSQL** (13+, tested 16) | S1 §8; S2 | Relational integrity, JSONB, arrays |
| Auth | Phone + password, Argon2id, opaque server sessions in HttpOnly cookie | MP §8; SUG-02, SUG-03 | Revocable, simple |
| File handling | Local private disk directory + Pillow validation/re-encode | SUG-18 | No extra service |
| AI | Provider adapter; primary **Gemini**; fallback `none` (non-LLM) | S1 §8; MP §11; DEC-22; SUG-15 | One vendor, switchable |
| News | Curated CSV/JSON → `news_events` via CLI | DEC-15 | No crawler |
| Testing | pytest + TestClient; optional Vitest/Playwright | SUG-20 | Standard |
| Runtime | Python 3.11+, Node 20 LTS for build | SUG-16/19 (versions are suggestions) | Current LTS lines |
| Deployment | One container (FastAPI serves API + built frontend) + PostgreSQL | SUG-19; host = GAP-07 | Simplest |

Not used (by decision): Next.js, microservices, Kubernetes, message brokers, Redis, vector DB, multi-agent frameworks, ML training pipelines `[MP §10, §11, §17]`.

---

## 2. Repository structure

```text
bonik-bondhu/
├── backend/
│   ├── app/
│   │   ├── main.py                  # create_app(): routers, middleware, static files
│   │   ├── config.py                # Settings (env vars, §6)
│   │   ├── db.py                    # engine, SessionLocal, transaction helper
│   │   ├── models/                  # SQLAlchemy models mirroring schema.sql
│   │   │   ├── user.py  profile.py  ledger.py  season.py  financing.py
│   │   │   ├── forecast.py  assessment.py  news.py  consent.py  lender.py  audit.py  ai.py
│   │   ├── schemas/                 # Pydantic request/response models (names = API spec)
│   │   ├── core/
│   │   │   ├── security.py          # hash/verify password, session token create/verify
│   │   │   ├── deps.py              # current_user, require_owner, require_lender, get_owned_profile
│   │   │   ├── errors.py            # AppError(code, http_status, message_key) + handlers
│   │   │   ├── rate_limit.py        # in-process limiter (single instance)
│   │   │   ├── audit.py             # audit(action, outcome, …)
│   │   │   └── csrf.py              # X-BB-Client header check (SUG-04)
│   │   ├── engine/                  # PURE functions, no DB/IO (mirror reference_calculations.py)
│   │   │   ├── money.py  accounting.py  baseline.py  schedules.py
│   │   │   ├── projection.py  funding.py  crop.py  concentration.py  units.py
│   │   ├── services/                # DB + engine orchestration
│   │   │   ├── auth_service.py  profile_service.py  ledger_service.py  summary_service.py
│   │   │   ├── supplier_service.py  debt_service.py  season_service.py  forecast_service.py
│   │   │   ├── financing_service.py  assessment_service.py  scenario_service.py
│   │   │   ├── news_service.py  consent_service.py  snapshot_service.py  lender_service.py
│   │   │   └── document_service.py
│   │   ├── ai/
│   │   │   ├── provider.py          # LLMProvider protocol + get_provider()
│   │   │   ├── gemini_provider.py   # only file importing the Gemini SDK/HTTP
│   │   │   ├── none_provider.py     # always raises AIUnavailable → fallbacks
│   │   │   ├── extraction.py        # receipt → draft
│   │   │   ├── purpose.py           # purpose text → proposed items
│   │   │   ├── advisor.py           # tool loop, grounding check, fallback templates
│   │   │   ├── tools.py             # read-only tool registry (profile-scoped)
│   │   │   ├── grounding.py         # numeric grounding validator (SUG-23)
│   │   │   ├── budget.py            # daily caps using ai_interactions
│   │   │   └── prompts/             # versioned prompt text files
│   │   ├── api/                     # one router per area (see API spec §2)
│   │   ├── help/help_topics.json    # bilingual static help (DEC-17)
│   │   └── cli.py                   # create-lender, reset-password, seed-demo, reset-demo, import-news
│   ├── migrations/                  # Alembic (0001 = schema.sql)
│   ├── tests/  unit/ golden/ api/ security/ ai/
│   ├── requirements.txt             # pinned versions
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx  App.tsx  router.tsx
│   │   ├── api/client.ts            # fetch wrapper: credentials, X-BB-Client, error mapping
│   │   ├── i18n/bn.json  en.json  index.ts
│   │   ├── components/              # Button, Field, AmountInput, Card, StatusBanner, DemoBadge, …
│   │   ├── pages/auth/  pages/owner/  pages/farm/  pages/lender/
│   │   ├── state/ActiveProfile.tsx  # active profile context (id in URL)
│   │   └── styles/tokens.css
│   ├── index.html  vite.config.ts  tailwind.config.ts  package.json
├── data/news/curated_news.csv      # team-curated + DEMO events
├── docker-compose.yml              # local PostgreSQL only
├── Dockerfile                      # production: build frontend, run uvicorn
└── docs/                           # this blueprint
```

Layer rule: `api → services → (engine | models | ai)`. `engine` imports nothing from the project except `money`. `ai` never imports `models` directly — it calls `services` through `ai/tools.py`. Frontend never contains business formulas except **display-only** previews (e.g. line total) that the server recomputes.

---

## 3. Frontend architecture

- **Routing:** `/` welcome · `/register` · `/login` · `/profiles` · `/p/:pid/home` · `/p/:pid/entries` · `/p/:pid/entries/new` · `/p/:pid/photo` · `/p/:pid/summary` · `/p/:pid/suppliers` · `/p/:pid/debts` · `/p/:pid/forecast` · `/p/:pid/financing/:rid?/step/:n` · `/p/:pid/assessment/:aid` · `/p/:pid/sharing` · `/p/:pid/advisor` · `/p/:pid/seasons` · `/p/:pid/seasons/:sid` · `/settings` · `/lender/cases` · `/lender/request` · `/lender/cases/:cid`.
- **Guards:** on load call `GET /auth/me`; owner routes require `role=owner`; `/lender/*` requires `lender_officer`. Server enforces regardless.
- **Active profile:** `pid` in URL (shareable, reload-safe); header shows name/type; `ActiveProfile` context fetches `GET /profiles/{pid}`; on 404 redirect to `/profiles`.
- **State:** server is the source of truth; no financial data in `localStorage`; only `lang` may be stored in `localStorage` before login.
- **API client:** `fetch` with `credentials: "include"`, header `X-BB-Client: web`, JSON; maps `{"error":{"code","message_key","fields"}}` to translated messages; on 401 `SESSION_EXPIRED` → `/login`.
- **Idempotency:** client generates `client_request_id` (UUID) per new-entry form instance.
- **i18n:** `react-i18next`, namespaces per area; Bangla digits display helper; CI script compares key sets.
- **Build:** `vite build` → `frontend/dist`, served by FastAPI `StaticFiles` at `/` with SPA fallback; API at `/api/v1`.

## 4. Backend architecture

- **App factory** `create_app()` registers routers under `/api/v1`, exception handlers, CORS (allowlist), CSRF header check middleware, security headers middleware, request-id middleware.
- **Dependencies:** `current_user` (cookie → session lookup by SHA-256 → user; updates `last_seen_at`), `require_owner`, `require_lender` (loads `lender_officers` row), `get_owned_profile(pid)` (404 if not owned or archived).
- **Transactions:** one DB transaction per request (`with session.begin()`); services raise `AppError`; no partial writes.
- **Service contract:** every owner service function signature starts `(db, user, profile, …)` where `profile` came from `get_owned_profile`. No service accepts a bare `profile_id` from the client.
- **Data version:** services that change assessment inputs call `bump_data_version(profile)` (FR-ASM-09).
- **Engine:** pure functions with `Decimal`, unit-tested against golden cases (`tests/golden`).
- **Errors:** stable codes (API spec §3) + `message_key` for i18n; no stack traces to clients.
- **Logging:** JSON logs with request id, route, status, latency; never request bodies, passwords, tokens, phone numbers or AI content.

## 5. Authentication implementation

| Item | Implementation | Ref |
|---|---|---|
| Registration | Validate (SUG-24/25), normalise phone to `+8801…`, lower-case email, Argon2id hash, insert user role `owner`, audit `auth.register` | FR-AUTH-01..03 |
| Login | Look up by phone; if locked → 429; verify hash (constant-time library); on fail increment counter, lock after 5 for 15 min; on success reset counter, create session (32 random bytes, base64url) → store SHA-256, set cookie `bb_session` (`HttpOnly; Secure` in prod; `SameSite=Lax`; `Path=/`) | FR-AUTH-04/05; SUG-03/05 |
| Dummy verify | When phone not found, still run a hash verify against a fixed dummy hash (timing equalisation) | MP §13 `[DERIVED]` |
| Session expiry | Owner 7 days, lender 8 hours absolute (SUG-03); expired → 401 `SESSION_EXPIRED` | FR-AUTH-06 |
| Logout | Set `revoked_at`, clear cookie | FR-AUTH-06 |
| Lender creation | `python -m app.cli create-lender --org "…" --name … --phone … --email …` prompts for a temporary password; audit `admin.create_lender` | DEC-24 |
| Password reset | Admin CLI `reset-password --phone …` after offline identity check; revokes all sessions | DEC-21 |

## 6. Environment configuration (`backend/.env.example`)

| Variable | Example | Notes |
|---|---|---|
| `APP_ENV` | `development` | `production` enables secure cookies, HSTS |
| `DATABASE_URL` | `postgresql+psycopg://bb:bb@localhost:5432/bonik_bondhu` | never commit real credentials |
| `SECRET_SALT` | 32+ random bytes (hex) | salt for IP hashing |
| `CORS_ORIGINS` | `http://localhost:5173` | comma list; production = app origin only |
| `OWNER_SESSION_DAYS` | `7` | SUG-03 |
| `LENDER_SESSION_HOURS` | `8` | SUG-03 |
| `LLM_PROVIDER` | `gemini` or `none` | DEC-22 |
| `GEMINI_API_KEY` | — | server only; never in frontend |
| `LLM_MODEL` | (set at setup) | SUG-15, GAP-05 |
| `LLM_TIMEOUT_SECONDS` | `20` | fallback after timeout |
| `AI_DAILY_LIMIT_ADVISOR` / `_EXTRACTION` / `_PURPOSE` | `30` / `10` / `10` | SUG-05 |
| `UPLOAD_DIR` | `/var/lib/bonik/uploads` | outside web root |
| `MAX_UPLOAD_MB` | `5` | SUG-18 |
| `FORECAST_WINDOW_WEEKS` / `FORECAST_MIN_WEEKS` | `8` / `4` | SUG-07 |
| `HIGH_DEPENDENCY_SHARE` | `0.50` | SUG-10 |
| `DEMO_PASSWORD` | — | only for `seed-demo` |
| `LOG_LEVEL` | `INFO` | |

## 7. Local development

```bash
# 1. Database
docker compose up -d db            # postgres:16 on localhost:5432 (user bb / db bonik_bondhu)
# 2. Backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # fill values; LLM_PROVIDER=none is fine for most work
alembic upgrade head
python -m app.cli seed-demo        # optional DEMO data
uvicorn app.main:create_app --factory --reload --port 8000
# 3. Frontend
cd ../frontend && npm install && npm run dev   # http://localhost:5173, proxy /api → :8000
# 4. Tests
cd ../backend && pytest -q
```

Vite dev proxy forwards `/api` to `localhost:8000` so cookies are same-origin in development.

## 8. Deployment approach `[SUG-19]`

1. Multi-stage `Dockerfile`: stage 1 `node` builds `frontend/dist`; stage 2 `python` installs backend, copies dist, runs `alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000`.
2. One managed or self-hosted PostgreSQL; `DATABASE_URL` via platform secret store.
3. HTTPS terminated by the hosting platform; `APP_ENV=production` sets `Secure` cookies and HSTS.
4. Persistent volume for `UPLOAD_DIR` (or disable photo upload if the host has no volume).
5. Single instance only (in-process rate limiter assumes one process; documented limitation).
6. Smoke test after deploy: `GET /api/v1/health` → `{"status":"ok","db":"ok","llm":"configured|disabled"}`.

Host choice is open (GAP-07). Any host that runs one container + PostgreSQL with HTTPS works.

## 9. External integrations

| Integration | Purpose | Status | Failure behaviour |
|---|---|---|---|
| Gemini (LLM, multimodal) | Receipt extraction, purpose parsing, advisor | Provider sourced; **free-tier limits and data terms NOT VERIFIED** (GAP-05) | `AI_UNAVAILABLE` → manual/template paths (AI doc §9) |
| Curated news file | L1 | Team-curated; no live API | Empty table → section shows "no matching news" |
| No SMS / email / identity / bank / CIB / payment APIs | — | Excluded (MP §8, S1 F9) | — |

## 10. Performance considerations

- Demo scale: < 50 users, < 10,000 transactions. Forecast = one aggregate query over ≤ 56 days; projection loop ≤ 90 days × few outflows → milliseconds.
- Indexes on `(profile_id, value_date)` and duplicate-check columns (schema).
- Advisor latency bounded by `LLM_TIMEOUT_SECONDS`; UI shows typing indicator.
- Frontend bundle: avoid heavy libraries; lazy-load lender pages and advisor.
- Images re-encoded to max 1600 px longest side before sending to AI (smaller payload) `[SUG-18 extension]`.

## 11. Technical constraints

- No paid services; free-tier AI only (unverified, GAP-05).
- No web research in planning (MP §23); provider details must be checked by the team at setup.
- Single instance; no background workers — all computations are synchronous and fast.
- Bangla text must be UTF-8 end-to-end; PostgreSQL database encoding `UTF8`.
- Dates are local calendar dates (Asia/Dhaka) for business logic; timestamps stored `timestamptz` UTC.

## 12. Testing requirements (summary; details in Testing doc)

| Layer | Requirement |
|---|---|
| Engine | 100% of golden cases (D1–D4, E1, units) pass; Decimal only |
| API | Every endpoint: happy path + validation error + auth missing + wrong owner/role |
| Security | SEC-01…SEC-20 negative tests pass before Phase 7 sign-off |
| AI | Works with `LLM_PROVIDER=none`; mocked provider tests for extraction/purpose/advisor; grounding validator tests |
| E2E | Shop and farm demo scripts pass on deployed build |
| CI | `pytest`, i18n key parity, frontend build, secret grep in `dist/` |
