# Bonik Bondhu (বণিক বন্ধু)

*Loans that move with your money.* A mobile-first, bilingual web app that helps Bangladeshi
shop owners and crop farmers record money correctly, see a forecast, test whether a proposed
repayment fits their cash, and share a consent-scoped case with a lender officer.
**Bonik Bondhu never lends, approves or scores — the lender decides.**

The full development blueprint is in [`docs/`](docs/README.md). Start there.

## Status

| Phase | State |
|---|---|
| P0 Foundation & approvals | Done — all SUG items approved (14 Nov 2026), schema migrated, `/health` OK, golden tests green |
| P1 Auth, profiles, first vertical slice | Done — register/login/lockout/logout, profiles, cash sale + expense, money summary, lender role routing; 74 backend tests + browser E2E (`frontend/e2e/p1-slice.mjs`) |
| P2 Financial data engine | Done — all 12 entry types with supplier/loan/season links, duplicate warning, void, E1 golden summary, debts + "no current loans", suppliers, crop seasons (acre/decimal/sq ft/bigha), cost items, harvest, season summary; shop + farm screens; 143 backend tests + browser walkthrough (`frontend/e2e/p2-walkthrough.mjs`) |
| P3 First working financial assessment | Done — forecast baseline (shop), financing requests + items + live gap preview, 5-step wizard with autosave, deterministic assessment (3 statuses, missing items, flags, "how calculated", inputs hash, stale detection), farm harvest check + loan-cover price, `seed-demo` / `reset-demo` CLI; D1–D4 golden through the API; 190 backend tests + browser walkthrough (`frontend/e2e/p3-walkthrough.mjs`). New suggestions SUG-30..36 await team approval (DECISIONS §2.1) |
| P4 Deterministic risk signals (L1/L2) | Done — supplier concentration + dependency bars, auto what-ifs (shop delay 7/14 d, price +15%; farm price −15%, yield −20%, inputs +15%) that never change the status, curated news import (`import-news`) + matching + proposed scenarios with confirm/dismiss, Risks and News tabs; 7 real news events (10 sources, pending second-person review) in `data/news/`; 208 backend tests + browser walkthrough (`frontend/e2e/p4-walkthrough.mjs`). SUG-30..40 approved (DECISIONS §2.1) |
| P5 Consent & lender review | Done — lender access request by share code (identical 202, rate limit), owner approves chosen sections for 7/14/30 days, immutable snapshot + SHA-256 (supplier names → Supplier 1/2/3), lender case file with read audit, private notes, information requests, demo decision with reason, reshare (new version), revoke/expiry block access, other organisations get 404; owner Sharing screen + lender portal (case list, request access, case file); 221 backend tests + browser E2E-3 (`frontend/e2e/p5-walkthrough.mjs`) |
| P6 AI (receipt draft, purpose parse, grounded advisor) | Built — Gemini + Groq through one OpenAI-compatible adapter with automatic fallback (SUG-47); receipt photo → draft → owner confirms (photo kept as evidence, EXIF stripped); purpose text → item list without prices; advisor with 10 read-only tools, grounding check and fixed answers from the records when AI is off; daily caps; Advisor in the nav. 238 backend tests (fake provider) + browser walkthrough with AI off (`frontend/e2e/p6-walkthrough.mjs`). **Still to do: run with real API keys (E2 receipts, E10 questions — P6-T08)** |

## Stack

React + Vite + Tailwind + TypeScript · Python FastAPI (modular monolith) · PostgreSQL 16 ·
Gemini behind a provider adapter, with a non-LLM fallback (`LLM_PROVIDER=none`).

## Local setup

**1. Database** — either Docker:

```bash
docker compose up -d db
```

or a native PostgreSQL 16 install, then as the `postgres` superuser:

```sql
CREATE ROLE bb LOGIN PASSWORD 'bb';
CREATE DATABASE bonik_bondhu      OWNER bb ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE bonik_bondhu_test OWNER bb ENCODING 'UTF8' TEMPLATE template0;
```

**2. Backend** (Python 3.11+)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: . .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # set SECRET_SALT; LLM_PROVIDER=none is fine
alembic upgrade head
uvicorn app.main:create_app --factory --reload --port 8000
```

Windows only: if importing SQLAlchemy fails with *"An Application Control policy has blocked
this file"*, install the pure-Python wheel (see the note in `backend/requirements.txt`).

**3. Frontend** (Node 20+)

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api to :8000)
```

**4. Tests**

```bash
cd backend && python -m pytest    # needs TEST_DATABASE_URL in .env (that DB is wiped by tests)
cd frontend && npm run check:i18n && npm run build
python scripts/check_dist_secrets.py frontend/dist
```

Health check: `GET http://localhost:8000/api/v1/health` → `{"status":"ok","db":"ok","llm":"disabled"}`.

**5. Browser E2E (optional, Windows with Microsoft Edge)** — build the frontend, start the
backend on :8000 (it serves `frontend/dist`), then:

```bash
cd frontend && node e2e/p1-slice.mjs http://localhost:8000 e2e-shots [lenderPhone] [lenderPassword]
cd frontend && node e2e/p2-walkthrough.mjs http://localhost:8000 e2e-shots-p2   # shop + farm
# P3/P4 use the DEMO seed: run `python -m app.cli reset-demo` first; password from DEMO_PASSWORD
cd frontend && node e2e/p3-walkthrough.mjs http://localhost:8000 e2e-shots-p3
cd frontend && node e2e/p4-walkthrough.mjs http://localhost:8000 e2e-shots-p4
cd frontend && node e2e/p5-walkthrough.mjs http://localhost:8000 e2e-shots-p5   # owner + lender (E2E-3)
cd frontend && node e2e/p6-walkthrough.mjs http://localhost:8000 e2e-shots-p6   # AI features with LLM_PROVIDER=none
```

## Admin CLI

```bash
cd backend
python -m app.cli create-lender --org "DEMO Bank Ltd (fictional)" --org-type bank \
    --name "Nasrin Officer (DEMO)" --phone 01900000101 --email l1.nasrin@demo.invalid --demo
python -m app.cli reset-password --phone 01712345678     # after an offline identity check
python -m app.cli seed-demo | reset-demo                 # fictional DEMO data (DEMO_PASSWORD)
python -m app.cli import-news ../data/news/curated_news.csv   # curated news (see data/news/README.md)
```

Passwords are typed at a hidden prompt (or read from `BB_NEW_PASSWORD` for scripts).

## Repository layout

```
backend/   FastAPI app (api → services → engine | models | ai), Alembic, tests
  db/      schema.sql + seed_demo.sql (copies of the reviewed files in docs/03_Technical; CI checks they match)
frontend/  React app (owner app mobile-first, lender portal desktop)
data/news/ Curated news CSV (real items with links + rules; imported by the CLI)
docs/      The MVP blueprint (PRD, flows, UI spec, API, schema, plan, tests, decisions)
scripts/   CI helpers
```

## Working rules

Implement one task ID at a time from `docs/05_Development/IMPLEMENTATION_PLAN.md`, use the exact
names from `docs/03_Technical/DATABASE_SCHEMA.md` and `API_SPECIFICATION.md`, and make the related
tests in `docs/05_Development/TESTING_AND_ACCEPTANCE.md` pass before moving on.
