# Bonik Bondhu — Full status report (17 Nov 2026)

Live app: **https://bonik-bondhu.onrender.com** (Render, branch `feature/p7`).
Everything below was checked today against the code, the local build and the live site. Where something was
not checked, the report says so.

---

## 1. In one paragraph

Bonik Bondhu is a Bangla-first web app for small shop owners and crop farmers in Bangladesh. An owner records
money in and out (typed or from a receipt photo), sees a summary and a cautious forecast, describes a loan they
want, and the app checks **every repayment date against the owner's own cash**. Supplier and news risks are shown as
what-ifs. The owner can share a fixed, fingerprinted case with a lender, who reads it, asks for more and records
their own decision. **Bonik Bondhu never lends, approves or scores — the lender decides.** Code calculates every
money figure; AI only reads, drafts and explains, and every AI feature works with AI switched off.

**Verdict today: the system works end to end — shop, farm and lender flows, data entry, all six AI features,
live and locally. All automated tests pass. 7 problems were found during this audit; all were fixed and
re-tested (section 6).**

---

## 2. How the system works (the flows)

```
SHOP OWNER                     FARMER                          LENDER OFFICER
register / log in              register / log in              account made by admin (CLI)
  │                              │                                 │
choose business (shop)         choose business (crop farm)        │
  │                              │                                 │
Entries: 12 money types,       Seasons: area, costs, yield,       │
receipt photo → AI draft       price; costs + sales as entries     │
  │                              │                                 │
Home / Summary / Forecast      Season summary, break-even         │
(8-week, cautious low case)    (no forecast for farms)            │
  │                              │                                 │
Financing wizard (5 steps): what to buy (AI can list items, owner prices them) → own cash →
existing loans → repayment terms (Fit Finder suggests schedules that fit) → CHECK
  │                              │
Result: ready_for_lender_review / not_affordable_base_case / insufficient_information
+ risks (supplier delay, price rise / harvest price, yield) + news signals + World Bank context
  │                              │                                 │
Sharing: owner sees the lender's request, picks sections, ──► lender's case file (snapshot +
approves 7/14/30 days; revoke any time                        SHA-256, Supplier 1/2/3 only)
                                                                   │
owner sees "lender asks…" ◄────────────────── info request / note / decision (proceed/decline/refer)
Advisor (any time): questions about the owner's own records, answered from read-only tools, numbers checked
```

---

## 3. Feature status

| Area | What works | Evidence today | Honest limits |
|---|---|---|---|
| Accounts & sessions | Register, login, logout, lockout after 5 tries, sessions 7 d (owner) / 8 h (lender), Bangla/English | E2E p1, p7; SEC tests | No phone/email verification, no self-service password reset (admin CLI) |
| Multi-business | One owner, shop + farm profiles, switcher | E2E p1, p2; Rahim has both | Poultry/fish/cattle not supported (DEC-05) |
| Ledger (data entry) | 12 money types, duplicates asked, void with reason, suppliers, debts, "no debts" declaration | E2E p1/p2, API tests AT-09..15 | Bank/bKash statement import not built (F8) |
| Receipt photo → draft (AI) | Photo → AI draft → owner confirms; photo deleted after save, data kept | E2E p6 (AI on, live today); E2 eval | E2 measured on 20 synthetic receipts only |
| Summary & forecast | Today/month, 8-week cautious forecast, "how calculated" | Golden D1 numbers, E2E p3 | Not validated on real Bangladeshi shop data |
| Crop seasons | Area units (bigha needs local factor), costs, harvest, break-even, loan-cover price | Golden D3, E2E p2/p3 | Crop farms only |
| Financing wizard | 5 steps with autosave, funding gap, AI item list (no prices), Fit Finder | E2E p3, p7, ultra-fit | Terms are the owner's proposal, not an offer |
| Check (assessment) | 3 honest results, missing items listed, flags | Golden D1–D4, API tests | Deterministic rules, not a probability of default |
| Risks & news | Supplier delay 7/14 d, price +15 %, harvest −15 %, yield −20 %, curated + daily auto news | E2E p4; live news collector ran today | Scenario sizes are assumptions; auto news is unchecked by a person |
| World Bank context | Inflation, lending rate, GDP growth, credit; inflation what-if | ultra-fit E2E | Yearly national data, not live prices |
| Sharing & lender | Request by share code → owner approves → snapshot + SHA-256 → lender reads, asks, decides; revoke/expiry block | E2E p5 (local + live today), SEC-08..13 | Hash proves "unchanged", not "true" |
| Advisor (AI) | Grounded answers in Bangla/English from read-only tools, template fallback | E2E p6 AI on/off (live today); E10 eval | E10: 16/20, varies run to run |
| Design | Logo, 16 credited photos, shop vs farm world, desktop/tablet/phone frames | axe 0 violations (21 screens × 2 widths, local + live) | Human accessibility review (TalkBack, 200 % zoom) still open |

---

## 4. The six AI features

| # | Feature | Type | Status today |
|---|---|---|---|
| F1 | Receipt photo → draft entry | Gemini vision, owner confirms | Live test passed (draft saved as photo-assisted after the owner confirmed). E2: amount 20/20, date 19/20, type 20/20 on 20 synthetic receipts |
| F3 | Cash-flow forecast | Deterministic code | Golden numbers exact; feeds every shop check |
| F7 | Loan purpose → item list | Gemini → Groq fallback; items have no prices until the owner adds them | Live test passed |
| L1 | News risk radar | Keyword/location rules + daily auto collection | 12 auto + 7 curated + 2 DEMO events on live; newest auto item dated today |
| L2 | Supplier dependency | Deterministic | Golden D1 65/25/10 %; shown as Supplier 1/2/3 to lenders and the AI |
| F12 | Advisor | Gemini → Groq, grounding check, template fallback | Live test passed (Bangla + English answers with checked numbers). E10: 16/20 passed, 19/20 contained the fact, 0 leaks, 0 forbidden words |

Every AI path also works with `LLM_PROVIDER=none` (E2E p6 AI-off passed today).

---

## 5. Verification run today

| Check | Result |
|---|---|
| Backend tests (pytest) | **264 passed** (incl. 4 new tests for the demo personas) |
| Frontend type-check + production build | pass |
| Bangla/English text keys | 971 = 971 |
| Secret scan of the built frontend | clean |
| Browser E2E on the production build | p1, p2, p3, p4, p5, p6 (AI off), p6 (AI on, real Gemini), p7 (E2E-1, E2E-4, session expiry), ultra-fit — **all pass** |
| Accessibility (axe-core, WCAG 2.1 AA) | **0 violations**, 21 screens at 1440 px and 360 px, local and live |
| Live site | p4, p5, ultra-fit, p6 AI-on pass; axe 0; demo data reset afterwards |
| Not checked | GitHub CI run (repo is private — check the Actions tab); p3/p7 on live (they create test users in the live database, so not run on purpose) |

---

## 6. Problems found in this audit — all fixed

| # | Problem | Fix |
|---|---|---|
| 1 | Logo subtitle "BONIK BONDHU" on the teal wall had 3.1:1 contrast (fails AA) | Lighter "wall mist" colour, 4.8:1 |
| 2 | Landing page had two "Create a new account" buttons → automated tests could not tell them apart | Bottom one is a link |
| 3 | New tip button "Next tip" collided with the wizard's "Next" in tests (p2, p3, p7 failed) | Renamed "Show another tip" / "আরেকটি পরামর্শ" |
| 4 | AI-off test still expected the old "photo stays attached" text (photo is deleted since SUG-52) | Test updated to the current text |
| 5 | AI-on test did not wait for the language switch on a slow (live) page | Test now waits |
| 6 | Farmers saw bazaar photos and shop wording in some sections | Farm photos + farm wording; lender sees both |
| 7 | Phones/tablets looked empty below the header (photo and tips only on desktop) | Photo + tips under every page, tile tab bar, tablet side nav |

---

## 7. Demo accounts (all fictional; password = the team's `DEMO_PASSWORD`, never shown on screen)

| Phone | Who | Business (share code) | What it shows |
|---|---|---|---|
| 01900000001 | Rahim Uddin | Rahim Store, grocery (7KQ2M-9XA4P) + Rahim Rice Farm (R3FAR-M8DMB) | Golden D1 (ready, supplier risk, news) and D3 (farm, ready) |
| 01900000002 | Karim Mia | Karim Variety Store (KRM2D-7XQ5A) | Golden D2: existing loans → not affordable |
| 01900000004 | Selina Akter | Selina Tailoring (SLN4T-8WQ3Z) | Golden D4: not enough information, lists what is missing |
| **01900000201** | Hasan Ali | Hasan General Store, grocery, Mirpur (HSN4M-D7K2Q) | Repaying a samity loan weekly; 8 weeks of sales, baki, purchases; no new request |
| **01900000202** | Nasima Begum | Nasima Bostro Bitan, clothing, Keraniganj (NSM8K-PR3XB) | Eid stock loan Tk 2,00,000 → ready; shared with the bank; bank asked for the saree quotation |
| **01900000203** | Jamal Uddin | Jamal Fol Bhandar, fruit, Rajshahi (JML6F-RT9WA) | Only checking a mango-season loan → not affordable; Fit Finder says whether any schedule fits (or the closest miss) |
| **01900000204** | Rokeya Khatun | Rokeya Sobji Khet, Brahmanbaria (RKY5S-BZ2LC) | Leased land, winter vegetables, stuck mid-season → ready; shared with the samity; lease paper asked |
| **01900000205** | Abdul Karim | Abdul Dhan Khet, Mymensingh (ABD7B-RD4HN) | Village rice farmer: Aman harvested and sold, NGO crop loan being repaid, Boro planned |
| **01900000206** | Monir Hossain | Monir Dhan Khet, Dinajpur (MNR3M-NS8EV) | About to start Boro → ready; the bank's request is waiting for his approval |
| 01900000101 / 102 | Nasrin / Tanvir | DEMO Bank Ltd (fictional) | Golden lender demo (E2E-3) — starts with no cases |
| 01900000103 | Other-Org Officer | DEMO MFI (fictional) | Proves another organisation cannot open a case |
| **01900000111** | Rafiq | DEMO Shonali Samity (fictional) — local installment lender | Rokeya's case: approved, info requested |
| **01900000112** | Shirin | DEMO Krishi o Babsa Bank (fictional) | Nasima's case (approved, info requested) + Monir's request (waiting) |

Reset all demo data (local or live) with `python -m app.cli reset-demo` (live: load `DATABASE_URL` from
`backend/neon.env.local` into the shell first, remove it after). Asked for but **not included**: poultry and fish
farms (out of scope, DEC-05 — crop farms only) and "which bank is best" (the app never recommends a lender).

### Suggested demo paths
- **Shop, 3 min:** Nasima → Home → Financing → result "ready" → Risks (supplier 70 %) → Sharing (bank asked for the
  quotation). Then Jamal → same check says "not affordable" → Fit Finder (step 5) answers honestly.
- **Farm, 2 min:** Rokeya → Seasons (costs paid vs left) → Financing → harvest check with loan-cover price → Sharing.
  Abdul → Loans I owe (NGO loan, next due).
- **Lender, 1.5 min:** Shirin → Cases (Nasima approved, Monir waiting) → case file (SHA-256, Supplier 1/2) →
  record a note or decision. Rafiq → Rokeya's farm case.

---

## 8. Known limits to say honestly

Free Render plan sleeps after 15 min (open the URL 2–3 min before a demo). Forecast and checks are not validated
on real Bangladeshi data. Scenario sizes are assumptions. AI accuracy numbers are small samples (N = 20) and E2
receipts are synthetic. Auto-collected news is not checked by a person. The free Gemini tier may use data (only
DEMO data is sent in demos). No phone verification, no CIB check, no real lending.

## 9. Update later on 17 Nov — Plan Ultra F4 Supply graph DONE and live (`cf19352`)

Suppliers → **Supply graph** shows the business's own suppliers, the areas they sit in, the goods they supply and the
news that touches them; every node shows the share of the last 8 weeks' purchases that passes through it. A shop
can ask "what if supply from here stops for 7 or 14 days?" — the existing supplier-delay scenario answers on the
latest check's inputs (what-if only, never stored, never changes the result). Lenders see the same graph in the
case file with Supplier 1/2/3 labels. Verified: 5 unit + 5 API tests (the Kaliakair node reproduces the golden D1
delay: short by Tk 9,376.90 on day 7), browser walkthrough `e2e/f4-graph.mjs` local and live, axe 0 on the new
pages, backend **274 passed**, all other E2E suites green. Limits: one business only (not a network), farm graphs
have no purchase what-if.

## 10. What comes next (approved Plan Ultra order, deadline 20 Nov)

F5 Applicant details → F6 Benchmark Proof → F7 News NLP (F8 statement import dropped first);
F9 story, deck, recording and merge to `main` on 19–20 Nov (owner approval before the merge).
