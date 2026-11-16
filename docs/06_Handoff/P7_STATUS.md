# P7 status — integration, security, deployment (15–16 Nov 2026)

First written from runs on the development machine (Windows, PostgreSQL 16, Edge). **16 Nov 2026: deployed**
to https://bonik-bondhu.onrender.com (Render free Docker + Neon free PostgreSQL) and re-verified there —
see "Live verification" at the end.

## Tasks (Implementation Plan §10)

| Task | Status | Evidence / what is left |
|---|---|---|
| P7-T01 i18n | ✔ | parity 818 keys; native review done by the team (`review/bn_review_.csv`, 75 corrections applied 16 Nov, placeholders checked) |
| P7-T02 accessibility & mobile | ✔ automated (16 Nov) · phone check by team | Live URL, Bangla UI, 12 screens: **axe-core WCAG 2.1 A/AA = 0 violations**; reflow at 320 px = 0 px sideways scroll everywhere; keyboard order follows the screen, focus ring on every stop. Fixed: inputs had only a 1 px border on focus (now 2 px ring), header overflowed 11 px at 320 px, faded (opacity) closed/inactive cards fell below 4.5:1. Known P2: at 200 % zoom (180 px) money rows on Home/Entries/wizard/result scroll 8–44 px sideways; the native date field's inner segments show no ring. TalkBack + low-cost Android Bangla rendering still need a person (review/README.md) |
| P7-T03 tests | ✔ local | 248 backend tests incl. SEC-01..20, the 18-case DB constraint script (`tests/db/test_constraints.py`) and a route-guard audit; deployed DB ☐ |
| P7-T04 security checklist | see below | team sign-off |
| P7-T05 deploy | ✔ 16 Nov | Render Blueprint from `feature/p7`; Neon at `0001_initial (head)`, 24 tables; `seed-demo` + `import-news` (7 events, 0 rejected) + `fetch-news` |
| P7-T06 E2E-1..4 | ✔ local + ✔ live | E2E-1 + E2E-4 `frontend/e2e/p7-e2e.mjs`; E2E-2 = p3 + p4; E2E-3 = p5; AI on = p6-ai-on (real Gemini on the live URL); AI off = p6-walkthrough (local) |
| FS-01..06 | ✔ local | FS-01/03 `tests/api/test_failures_p7.py`; FS-02 = AI-03 (+ live check with an invalid key: Gemini 400 / Groq 401 → `AIUnavailable` → 503 `AI_UNAVAILABLE` + fallback); FS-04 import-news test; FS-05 in p7-e2e; FS-06 debt tests |
| P7-T07 rehearsal + backup recording | ✔ automated · team ☐ | 3 timed rounds on the live URL, all 12 steps green (SLOW_MO 350 ms): step 1 shop register → entries → forecast → financing → risks + E2E-4 ≈ 56–58 s · step 2 supplier/news ≈ 17–19 s · step 3 AI receipt/purpose/advisor ≈ 19–20 s · step 4 lender consent/review ≈ 29–30 s. 15 `.webm` videos (~37 MB) kept **offline outside the repo** in `D:\Bonik_Bondhu(Main)\demo-recordings\` (+ `timings.csv`). `RECORD_DIR`/`SLOW_MO` hook in `frontend/e2e/rec.mjs`. The team still rehearses the spoken demo (≤ 8 min) themselves |
| P7-T08 "what is real" | ✔ | HACKATHON_DEMO_AND_HANDOFF.md §2 filled with measured facts |
| P7-T09 bug triage | ✔ so far | bugs found in P7 were fixed (below); no open P0/P1 |

## Bugs found and fixed in P7

- **Logs could carry personal data**: PostgreSQL error text repeats row values ("Failing row contains
  (… phone, email …)") and the 500 handler logged it → database errors are now logged as type +
  SQLSTATE only (`core/errors.py`, test). `hide_parameters=True` on the engine as well.
- **Alembic disabled the app's loggers** when run in-process (tests) → `disable_existing_loggers=False`.
- **Empty `SECRET_SALT` in production** made audit IP hashes reversible → the app refuses to start.
- **Behind the host proxy every user shared one IP** → one busy user could block all logins (per-IP auth
  limit) and audit IPs were the proxy's → uvicorn trusts proxy headers in the container (trade-off in DEPLOY.md).
- **Upload folder not writable → 500** → 503 `doc.err.storage`; manual entry still works (FS-03).
- **Photo file missing after a redeploy → 500** → 404.
- **Session expiry lost the user's place** → after login the owner returns to the same screen (FS-05).
- **Docker build context included dev uploads** (`backend/uploads`) → excluded; `data/` (news CSV) now copied.

## Security checklist (Security doc §6)

| Item | Status | Evidence |
|---|---|---|
| Argon2id; no plaintext; generic login errors; lockout | ✔ | test_auth, SEC-14, E2E-4 |
| Cookie flags in production; logout revokes; expiry | ✔ code + tests | `api/auth.py` `secure=is_production`; SEC tests; check flags on the URL ☐ |
| CSRF header; CORS restricted | ✔ | middleware tests (CSRF_HEADER_MISSING); same-origin SPA |
| Every `/profiles/{pid}/**` route uses `get_owned_profile` | ✔ automated | `tests/security/test_sec_p7_routes.py` walks all 67 routes (55 profile routes) |
| Every child lookup filters by `profile_id` | ✔ reviewed | `db.get` uses checked: ownership/org checked right after, or composite FKs / global tables |
| `/lender/**` uses `require_lender` + `get_authorized_consent` | ✔ automated + SEC-08..11 | route audit (4 lender routes) |
| Snapshot = approved sections only; supplier labels | ✔ | SEC-12, scrub tests |
| Upload validation, private dir, no public URL | ✔ | SEC-17 |
| AI payload minimisation, per-upload consent, caps, timeout | ✔ | AI-04, AI-07, tool label tests, purpose scrub test |
| Advisor read-only, session-bound, grounding on | ✔ | SEC-19, UT-11, E10 (0 leaks) |
| Security headers + CSP | ✔ | header tests (unit/app shell); HSTS only in production |
| Logs: no tokens/passwords/phones/AI content | ✔ after fix | request log = method/path/status; AI log = metadata; DB errors = code only |
| `dist/` contains no API keys | ✔ | `scripts/check_dist_secrets.py` in CI |
| HTTPS + HSTS on deployed URL | ✔ live | http → 301 https; HSTS `max-age=31536000; includeSubDomains`; CSP, DENY, nosniff, same-origin |
| SEC-01..SEC-20 pass | ✔ local | pytest (248) |
| DB constraint tests on deployed DB | ✔ by migration | Neon runs the same migration (`alembic current` = `0001_initial (head)`, 24 tables). `pytest tests/db` is **never** pointed at Neon: the test suite drops the schema |

## Live verification (16 Nov 2026, https://bonik-bondhu.onrender.com)

- Health `{"status":"ok","db":"ok","llm":"configured"}`.
- Security on the URL: HTTPS redirect + headers above; session cookie `HttpOnly; Secure; SameSite=lax`;
  no `X-BB-Client` → 403 `CSRF_HEADER_MISSING`; no session → 401; register with `role: admin` → owner (SEC-15);
  `/auth/me` `Cache-Control: no-store`; foreign origin gets no CORS allow; logout → next call 401.
- Browser E2E on the URL (Edge, 360 px owner / 1280 px lender), `reset-demo` before each:
  p7-e2e (E2E-1 new shop → ready for lender review; E2E-4 lockout, D4 missing list, FS-05) ✔ 30 s ·
  p3 (D1–D4 golden numbers, wizard) ✔ 27 s · p4 (supplier 65/25/10, scenarios 9,376.90 / 12,377.35 / 4,465.12,
  D3 53,260 / 49,480 / 1,275, DEMO news) ✔ 10 s · p5 (E2E-3 lender flow, revoke, other org) ✔ 19 s ·
  p6-ai-on (real Gemini: receipt Tk 3,450.00 → photo_assisted; AI list without prices, counted after owner
  price 1,50,000 → 1,52,500; advisor "Supplier 1 … 65.0%", "Tk ২,৮২,৫০০", grounded) ✔ 13 s.
- Fixed during the live run: E2E scripts waited for `networkidle`, too early on the slow free host (now poll);
  the automatic news search kept a foreign story ("Onion prices in Tajikistan rise") → national searches now
  keep Bangladeshi publishers / headlines naming Bangladesh only (SUG-54); the bad row was removed from Neon
  together with one proposed scenario on an E2E test account.
- First request after the free host sleeps shows Render's "waking up" page (~1 min) — open the URL before the demo.
