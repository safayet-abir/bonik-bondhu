# HACKATHON DEMO AND HANDOFF — Bonik Bondhu MVP

**Document ID:** BB-DOC-13 · **Version:** 1.0 (12 Nov 2026)
**Honesty rules for every demo** `[SRC: S5 "Three rules"; S1 §13]`: show only numbers the running system calculates; label everything ("DEMO", "Estimate", "What-if", "Your proposal — not a lender offer"); a working text demo beats a broken voice demo.

---

## 1. Demo goal

Show one honest, working journey: **Registration → Financial entry → Forecast → Financing assessment → Risk explanation → Authorised lender review** `[SRC: MP §15 File 13]` — once for a shop owner and once for a crop farmer, ending with a lender review that the owner controls.

## 2. What is real, what is simulated, what is not built

Fill the "Status on demo day" column only with what the team has verified in P7. Do not claim a row that fails.

| Item | Planned status | Status on demo day |
|---|---|---|
| Register / login / logout / lockout | Working | ✔ local 15 Nov (AT/SEC tests, E2E-1, E2E-4) · deployed ☐ |
| Multi-profile (shop + farm under one user) | Working | ✔ local (P2–P4 walkthroughs) · deployed ☐ |
| Ledger with S1 accounting rules (12 types) | Working, golden-tested | ✔ local (E1 golden, E2E-1 summary) · deployed ☐ |
| Summary, forecast baseline | Working (estimate, not validated on BD data) | ✔ local (D1 golden, E2E-1) · deployed ☐ |
| Funding gap, due-date check, crop check, statuses | Working, golden-tested | ✔ local (D1–D4 golden via API) · deployed ☐ |
| Supplier concentration + delay/price scenarios | Working; severities are **assumptions** | ✔ local (D1/D3 golden, E2E-1 Risks tab) · deployed ☐ |
| News signals | Working rule matching on a **curated** list + a daily automatic news search (labelled "collected automatically — not checked by a person", SUG-45); DEMO events **fictional** | ✔ local · deployed ☐ |
| Consent, snapshot hash, lender review, revoke/expiry | Working | ✔ local (E2E-3 = p5 walkthrough, SEC-08..13) · deployed ☐ |
| Receipt photo → draft → confirm | Working if AI on; accuracy = measured E2 numbers only | ✔ local with Gemini (p6-ai-on). E2: 19/20 fully correct on **20 synthetic receipts** after tuning on the same set (17/20 before) — no real receipts measured |
| Purpose text → item list | Working if AI on | ✔ local with Gemini (p6-ai-on) |
| Advisor (bn/en, grounded) | Working if AI on; template fallback otherwise | ✔ local. E10: 16/20 passed (10 bn + 10 en), fact present 19/20, 0 forbidden phrases, 0 cross-profile leaks; varies run to run |
| Demo users, lender organisations, news events | **Simulated (DEMO)** | — |
| Voice, statements import, Monte Carlo, optimizer, Business Health card, GNN, ZK proof, poultry/fish/cattle, Buy/Sell | **Not built** (backlog) — mention only as roadmap | — |

### What not to say `[SRC: S1 §13.1; MP §17]`
- "We reduce defaults" / "probability of default" / "credit score" / "approved" / "eligible".
- "Live prices", "real-time news", "we know all suppliers".
- "Bank partner", "Bangladesh Bank integration", "CIB check".
- Any accuracy number not measured and reported with N.

---

## 3. Before the demo (setup, T-60 minutes)

1. Deployed URL `/api/v1/health` → `{"status":"ok","db":"ok"}`.
2. `python -m app.cli reset-demo` (fresh relative dates) with `DEMO_PASSWORD` set.
3. Log in once as each demo account (below) to confirm.
4. Decide AI mode: if the provider check fails, set `LLM_PROVIDER=none` and use fallback lines (§7).
5. Open two browsers: **A** = phone-size (owner), **B** = desktop (lender).
6. Play backup recording file locally ready (P7-T07).

Demo accounts (fictional; password = `DEMO_PASSWORD`, never shown on screen):

| Account | Phone | Role | Data |
|---|---|---|---|
| Rahim Uddin (DEMO) | 01900000001 | owner | Rahim Store (shop, D1) + Rahim Rice Farm (farm, D3) |
| Karim Mia (DEMO) | 01900000002 | owner | Karim Variety Store (D2) |
| Selina Akter (DEMO) | 01900000004 | owner | Selina Tailoring (D4) |
| Nasrin Officer (DEMO) | 01900000101 | lender | DEMO Bank Ltd (fictional) |
| Other-Org Officer (DEMO) | 01900000103 | lender | DEMO MFI (fictional) — for isolation proof |

---

## 4. Shop-owner demo (≈ 4 minutes)

| Time | Browser | Action | What the audience sees | Say |
|---|---|---|---|---|
| 0:00 | A | Register a **new** account (name, phone, email, password) | Only 4 fields; note "number not verified yet" | "Registration is deliberately simple." |
| 0:20 | A | Create shop profile → Path A → add cash sale 8,500 + rent 1,500 | Saved; home shows today in/out | "Records first, no loan form needed." |
| 0:40 | A | Logout → login as **Rahim (DEMO)** → Rahim Store | DEMO badge; 8 weeks of weekly records | "This is fictional demo data." |
| 0:55 | A | Money summary (last 8 weeks) | Sales vs operating cash; loan not counted as income | "Accounting rules are enforced in code." |
| 1:10 | A | Forecast | Weekly net low 25,000 / expected 32,312.50; "estimate" label | "A simple estimate from recent weeks, not a guarantee." |
| 1:30 | A | Financing → open DEMO request → step 5 → Check | Status **Ready for lender review**; "not a loan approval" | "Funding gap 1,50,000; he asked 2,00,000 — the app asks why, without accusing." |
| 2:00 | A | How-calculated tab | Formula, inputs, sources | "Every number is explainable." |
| 2:15 | A | Risks tab | 65% Supplier A; 7-day delay → shortfall on day 7 (Tk 9,376.90 below reserve); "what-if only" | "Supplier dependency becomes a concrete date-level risk." |
| 2:35 | A | News tab → DEMO road blockade → Test this risk | Single-source, DEMO label; scenario computed; status unchanged | "News suggests a test; it never judges the borrower." |
| 2:55 | A | (optional, AI on) Advisor: "আগামী সপ্তাহে কিস্তি কত?" | Grounded Bangla answer | "The advisor reads tool results; it cannot invent numbers." |
| 3:15 | A | Sharing → show share code | Code + explanation | Hand over to lender part (§6). |

## 5. Farmer demo (≈ 2.5 minutes)

| Time | Browser | Action | What they see | Say |
|---|---|---|---|---|
| 0:00 | A | Switch profile → Rahim Rice Farm | Same user, separate data | "One person, two businesses, no mixing." |
| 0:15 | A | Season: Boro, 150 decimal = 1.5 acres | Unit conversion | "Farmers use their own land units; bigha needs the local value." |
| 0:35 | A | Season summary | Income range 75,600 / 1,05,600 / 1,31,250; break-even 19.70; loan-cover 19.78 Tk/kg | "Owner estimates, clearly labelled." |
| 1:00 | A | Financing → assessment | Single payment after harvest; Ready for lender review | "Repayment follows the harvest in this proposal." |
| 1:25 | A | Risks: yield −20% still covered (+7,080); inputs +15% → pre-harvest shortfall 1,275 | Flags | "Shows a cash crunch before harvest, not just at repayment." |
| 1:50 | A | News: DEMO Dhamrai flood → test | Yield scenario | "Weather-related risk only where an event is recorded." |

Optional contrast (30 s): log in as Karim (D2) → **These terms may cause a cash shortfall** on day 7; or Selina (D4) → **More information needed** with checklist. "The app says no or not-yet honestly."

## 6. Lender part (≈ 1.5 minutes)

| Browser | Action | Shows |
|---|---|---|
| B | Login Nasrin (DEMO) → Request access with Rahim Store code, 5 sections | Generic "if valid" confirmation |
| A | Rahim → Sharing → approve 5 sections, 14 days | Snapshot hash |
| B | Open case | Only approved sections; Supplier 1/2/3 (no names); CIB notice; scenarios labelled what-if |
| B | Request info: "Please share supplier quotation" | — |
| A | Owner sees the request | — |
| B | Record decision "refer" + reason | Banner: demo decision by lender; Bonik Bondhu does not issue loans |
| A | Revoke | — |
| B | Refresh case | "Access revoked" |
| (opt.) | Login other-org officer → case invisible | Isolation |

---

## 7. If something breaks (fallbacks) `[SRC: S5 fallback table]`

| Not working | Show instead | Say |
|---|---|---|
| AI provider | `LLM_PROVIDER=none`: manual entry, help-menu advisor | "AI is optional; the core works without it." |
| News tab | Skip; show supplier scenario only | "News signals come from a small curated list." |
| Deployment | Local run with same seed, or backup recording | "This is a recording of the same build." |
| Lender browser | Show case file via owner's shared snapshot hash + recording | — |

---

## 8. Self-guided path for judges

1. Open the URL → choose language.
2. Log in as Rahim (DEMO) (credentials given privately by the team).
3. Rahim Store → Forecast → Financing → open request → Check → read the three tabs.
4. Switch to Rahim Rice Farm → Season summary → Financing → Check.
5. Log in as Nasrin (DEMO) → Cases → open the case Rahim shared (team pre-approves one consent before judging).
Every screen carries DEMO labels; nothing here represents a real borrower or lender.

---

## 9. Developer handoff checklist

- [ ] Repo README points to this blueprint; TRD §7 local setup works on a clean machine
- [ ] `.env.example` complete; secrets documented (not committed)
- [ ] SUG register outcomes recorded (P0-T01)
- [ ] Migrations reproducible from zero; `seed-demo`/`reset-demo` work
- [ ] Golden tests + SEC tests + DB constraint tests green in CI
- [ ] `reference_calculations.py` and engine agree (golden test)
- [ ] Curated news CSV with source URLs and curator names committed
- [ ] E2/E10 measured results file committed (with N and date)
- [ ] Known limitations (Decisions §6) and backlog (Decisions §7) reviewed
- [ ] Deployment notes: host, env vars, how to rotate keys, how to reset demo
- [ ] Admin CLI usage documented (`create-lender`, `reset-password`, `seed-demo`, `reset-demo`, `import-news`)

## 10. Final demo readiness checklist

- [ ] `/health` OK on deployed URL with HTTPS
- [ ] `reset-demo` run within the last hour
- [ ] All demo logins tested
- [ ] D1–D4 statuses match Testing §4
- [ ] DEMO badges visible on every demo profile, lender and news item
- [ ] AI mode decided (on/off) and the matching script lines rehearsed
- [ ] No API keys visible in screens, terminals or recordings
- [ ] "What is real" table (§2) filled honestly
- [ ] Backup recording available offline
- [ ] Timer rehearsal ≤ 8 minutes total (shop + farm + lender)
- [ ] One team member assigned to answer "what is not built yet" using backlog IDs
