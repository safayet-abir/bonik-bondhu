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
| P4 Deterministic risk signals (L1/L2) | Next |

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
```

## Admin CLI

```bash
cd backend
python -m app.cli create-lender --org "DEMO Bank Ltd (fictional)" --org-type bank \
    --name "Nasrin Officer (DEMO)" --phone 01900000101 --email l1.nasrin@demo.invalid --demo
python -m app.cli reset-password --phone 01712345678     # after an offline identity check
```

Passwords are typed at a hidden prompt (or read from `BB_NEW_PASSWORD` for scripts).

## Repository layout

```
backend/   FastAPI app (api → services → engine | models | ai), Alembic, tests
  db/      schema.sql + seed_demo.sql (copies of the reviewed files in docs/03_Technical; CI checks they match)
frontend/  React app (owner app mobile-first, lender portal desktop)
docs/      The MVP blueprint (PRD, flows, UI spec, API, schema, plan, tests, decisions)
scripts/   CI helpers
```

## Working rules

Implement one task ID at a time from `docs/05_Development/IMPLEMENTATION_PLAN.md`, use the exact
names from `docs/03_Technical/DATABASE_SCHEMA.md` and `API_SPECIFICATION.md`, and make the related
tests in `docs/05_Development/TESTING_AND_ACCEPTANCE.md` pass before moving on.
