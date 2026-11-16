# Bonik Bondhu — Plan Ultra (final, 16 Nov 2026)

**Status: approved.** On 16 Nov 2026 the owner delegated the decisions to the AI developer ("tumr onomoti
diba, tumr mote best akta system vanao") and set the limit: **submission deadline 20 Nov, work as much as
possible today.** Recorded in DECISIONS §2.1 (SUG-55). P0–P7 is done and live at
https://bonik-bondhu.onrender.com; this plan is what we add on top.

Assumption to confirm: "20 tarikh" = 20 November 2026 (4 days). If it is 20 December, the cut line simply moves down.

## 1. Product — what wins, measured against the judging criteria

Challenge: **SME Capital Engine** — faster capital access, lower defaults; cash-flow modeling + risk + integrations.

| Criterion (weight) | What a judge sees | Built by |
|---|---|---|
| Innovation & problem clarity (25) | A shop owner and a farmer whose loan request is tested against their own cash before a lender sees it | existing flow + F3 landing story |
| Feasibility & working execution (30/25) | Live URL, real data flow, 248+ tests, golden numbers, a schedule that is *found* to fit | **F1 Fit Finder**, existing engine |
| Business potential & thoughtful AI (20–25) | AI reads receipts and news, explains with grounded numbers, never calculates; real economic data | existing AI + **F2 World Bank**, F7 News NLP |
| Scalability & originality (15) | Risk traced through a supply graph; proof to a lender without the ledger | **F4 Supply Graph**, **F6 Benchmark Proof** |
| Responsible & inclusive AI (15) | Bangla-first, consent per section, "how was this calculated?", honest labels, no score, no approval | existing + labels on every new feature |

One sentence for the pitch: *"Loans that move with your money — checked against cash flow, explained in
Bangla, shared with proof instead of paperwork."* We never say "reduces defaults"; we say repayments are
checked against cash flow before the lender sees the case.

## 2. Rules that do not change

1. Bonik Bondhu never lends, approves, scores or computes probability of default. The lender decides.
2. Code calculates every money figure (Decimal, golden-tested). AI reads, drafts, explains; the owner confirms.
3. Everything works with `LLM_PROVIDER=none`. Golden numbers D1–D4 / E1 stay exact.
4. Each feature is named for what it is: a schedule *search* (not RL), a hash *commitment* (not zero-knowledge),
   a *file import* (not a bank connection), yearly national data (not "live").
5. Supplier names and personal details never go to an LLM. No secrets in the frontend.

## 3. Features (in build order — see §8)

**F0 Right examples per profile.** Farm profiles saw shop examples in the wizard and entry form
("rice, lentils and oil before Eid", "Rice (50 kg sack)", "Grocery"). Farm versions added.

**F1 Repayment Fit Finder** (challenge prompt 3). Tries weekly / monthly / single schedules through the existing
projection and crop engines and returns up to three that leave no shortfall — *safest*, *fastest*, *smallest
installment*; if none fits it says so. One tap copies an option into the wizard. Still "Your proposal — not a
lender offer". `engine/schedule_search.py` (pure) · `POST …/financing-requests/{rid}/schedule-options`.

**F2 World Bank Open Data** (data source). Inflation, lending rate, GDP growth, private credit for Bangladesh
(free API, no key, verified 16 Nov). In-memory daily refresh with a committed snapshot as fallback — no schema
change. Shown as "Economy context" to owner and lender with year and source; an advisor tool; one extra what-if
"prices rise at last year's inflation". Never changes the status.

**F3 Look and motion.** Landing page with the story, illustrated scenes (shop, farm, loan, lender) as inline SVG
with emoji accents, page and card motion, numbers that count up, an interactive cash-flow chart where a what-if
redraws the line. CSS only, reduced-motion respected, no real bank logos, 360 px phone first.

**F4 Supply Graph** (prompt 1). Per-profile graph: business → suppliers → areas → commodities → news. Tap an area
or commodity: the affected purchase share goes through the existing scenario engine and returns a tested number.
`engine/graph.py` (pure) · `GET …/supply-graph`. Not a cross-business network; GNN is roadmap.

**F5 Applicant details.** Asked only at sharing time, step by step with a completeness bar: date of birth, NID
number, address, nominee, trade licence, years in business. Masked on screen, never logged, never sent to an LLM,
shared only through the consent section `applicant_details`. "Declared by the owner — not verified."

**F6 Benchmark Proof** (prompt 5). Lender asks yes/no benchmarks (average weekly sales ≥ X, weeks recorded ≥ N, no
overdue loan). With consent the answer is yes/no plus a Merkle-root commitment over the confirmed entries — no
transaction list is shared. Selective disclosure, not zero-knowledge.

**F7 News NLP** (prompt 2). LLM classifies Bangla and English headlines into event type / place / commodity
(validated JSON); keyword rules remain fallback and cross-check; disagreement → "AI-classified — not confirmed".
Measured on ~40 labelled headlines, reported with N.

**F8 Statement import** (stand-in for Plaid). Bank / bKash CSV → draft rows → owner confirms. *First to be cut.*

**F9 Story and handoff.** "What is real" table, criteria-mapped deck notes, federated-learning design page
(prompt 4, no code), new demo script, recording, merge to `main`. *Never cut.*

## 4. Experience

- Owner: same five-tab navigation; new entry points are inside existing screens (wizard step 4 "Find a schedule
  that fits", Risks tab "Supply graph", Sharing "Your details", Home "Economy context").
- Lender: case file gains Economy context, Supply graph (Supplier 1/2/3 labels), Benchmark answers, Applicant details.
- Every new number keeps a "How was this calculated?" link; every assumption is written in words.
- Bangla and English keys added together (CI parity check); new Bangla text goes into the review CSV.

## 5. Technical

- Layer rule unchanged: `api → services → (engine | models | ai)`; new engine modules are pure and mirror the
  golden-test style.
- No schema change for F1, F2, F4, F6 (computed on request; F6 stored inside the snapshot JSON).
  **Migration 0002** only for F5 (`applicant_details`) and F8 if built; table-count tests updated with it.
- New consent section keys: `applicant_details`, `benchmark_proofs`, `supply_graph`, `economy_context`.
- Frontend: no chart or animation library; SVG + CSS. New components `Scene`, `CashChart`, `GraphView`, `CountUp`.

## 6. AI and external data

| Use | Provider | Fallback | Honesty label |
|---|---|---|---|
| Receipt draft, purpose list, advisor (existing) | Gemini → Groq (text) | manual form / fixed answers | "AI suggestion — you confirm" |
| News headline classification (F7) | Gemini → Groq | keyword rules | "AI-classified — not confirmed" |
| Advisor tool `get_economy_context` (F2) | World Bank API | committed snapshot | "World Bank, year YYYY" |
| Schedule search, graph, benchmark answers | none — deterministic code | — | "Estimate" / "Your proposal" |

AI never sets a price, an amount or a status. Daily caps apply to F7 before it runs on the live app.

## 7. Security and privacy

- F5: NID and date of birth are sensitive — masked in UI and API lists, excluded from logs and LLM tools,
  shared only in the consented snapshot; DEMO accounts carry fictional values; legal review (GAP-10) before real users.
- F6: commitment uses a per-proof random salt; answers are booleans only; each request is audited like a case read.
- F2/F7: outbound calls carry no user data; they never run inside a request.
- Ownership (404), CSRF header, consent checks and the route-guard audit test cover every new route.

## 8. Implementation order and cut line

Backend first, tests green, then the screen, then live check. One phase at a time.

| Phase | Work | Target | Cut? |
|---|---|---|---|
| F0 | Decisions recorded · farm examples | 16 Nov | no |
| F1 | Repayment Fit Finder (engine, API, wizard) | 16 Nov | no |
| F2 | World Bank context (service, tool, cards, what-if) | 16–17 Nov | no |
| F3 | Landing, scenes, motion, cash-flow chart | 17 Nov | no |
| — | **Must-have line** | | |
| F4 | Supply Graph | 18 Nov | after F5–F8 |
| F5 | Applicant details (migration 0002) | 18 Nov | 3rd |
| F6 | Benchmark Proof | 19 Nov | 2nd |
| F7 | News NLP + measured set | 19 Nov | 1st after F8 |
| F8 | Statement import | only if time | first |
| F9 | Story, docs, recording, merge | 19–20 Nov | never |

## 9. Tests and validation

- Each engine module: unit + golden tests on the DEMO fixtures (D1 fits already; D2's 12 × 7,000 fails — the
  finder must return only schedules the existing check accepts; D3 single payment after harvest).
- Each endpoint: API tests incl. other-owner 404 and farm/shop mismatch; route-guard audit stays green.
- Property the suite enforces: **every option the finder returns passes the unchanged affordability check.**
- Browser: one walkthrough per phase on the live URL; accessibility audit (axe, 320 px) re-run after F3.
- AI: F7 measured with N; E2/E10 numbers unchanged unless re-run.
- Gate before submission: full pytest, build, i18n parity, dist secret scan, live E2E-1..4, CI green.

## 10. Handoff

- Status of each phase is written into `docs/06_Handoff/P7_STATUS.md` (new "Plan Ultra" section) as it lands.
- `HACKATHON_DEMO_AND_HANDOFF.md` §2 "what is real" gets one row per new feature with its honest label.
- Decisions: SUG-55 (this plan) and one SUG per feature in DECISIONS §2.1.
- Open: event round format and video length; who supplies illustrations beyond the SVG scenes made here.
