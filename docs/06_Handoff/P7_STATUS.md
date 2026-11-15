# P7 status — integration, security, deployment (15 Nov 2026)

Everything below was run on the development machine (Windows, PostgreSQL 16, Edge). Nothing has been
deployed yet; items marked "deployed ☐" must be repeated on the deployed URL (DEPLOY.md).

## Tasks (Implementation Plan §10)

| Task | Status | Evidence / what is left |
|---|---|---|
| P7-T01 i18n | parity ✔ (818 keys bn = en) | **native-speaker review of the Bangla text: team** |
| P7-T02 accessibility & mobile | partly | all walkthroughs run at 360 px; inputs have labels (scripts select by label); 48 px targets used in components. **No dedicated contrast/screen-reader audit yet** |
| P7-T03 tests | ✔ local | 248 backend tests incl. SEC-01..20, the 18-case DB constraint script (`tests/db/test_constraints.py`) and a route-guard audit; deployed DB ☐ |
| P7-T04 security checklist | see below | team sign-off |
| P7-T05 deploy | prepared | `render.yaml`, `docs/06_Handoff/DEPLOY.md` (Render + Neon), Dockerfile fixes, CI builds and starts the image. **Needs: host accounts, pushing the branch** |
| P7-T06 E2E-1..4 | ✔ local | E2E-1 + E2E-4 `frontend/e2e/p7-e2e.mjs`; E2E-2 = p3 + p4; E2E-3 = p5; AI on = p6-ai-on; AI off = p6-walkthrough. Deployed ☐ |
| FS-01..06 | ✔ local | FS-01/03 `tests/api/test_failures_p7.py`; FS-02 = AI-03 (+ live check with an invalid key: Gemini 400 / Groq 401 → `AIUnavailable` → 503 `AI_UNAVAILABLE` + fallback); FS-04 import-news test; FS-05 in p7-e2e; FS-06 debt tests |
| P7-T07 rehearsal + backup recording | ☐ | team (Playwright can record the walkthroughs as video if wanted) |
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
| HTTPS + HSTS on deployed URL | ☐ | after deploy |
| SEC-01..SEC-20 pass | ✔ local | pytest |
| DB constraint tests on deployed DB | ☐ | run `pytest tests/db` against the deployed DB copy |
