# Bonik Bondhu (বণিক বন্ধু) — Hackathon MVP Blueprint

**Version:** 1.0 · **Date:** 12 Nov 2026 · **Status:** Draft for team approval
**Project:** SME Capital Engine (FinSphere AI) · International AI Builders Congress 2026, Idea to Unicorn track `[SRC: S1 header]`
**Pitch:** *Loans that move with your money* `[SRC: S1 §1.1]`

---

## 1. What this is

A buildable development blueprint that turns the finalized Bonik Bondhu concept (v3.1 team plan and companions) into a **small, fully connected, working MVP**. Central rule: *build a small system that actually works from beginning to end* `[SRC: MP §1]`.

Bonik Bondhu helps Bangladeshi shop owners and crop farmers record money correctly, see a simple forecast, describe a financing need, test whether a proposed repayment fits their cash under stated assumptions, see supplier/news what-if risks, and share a consent-scoped case with a lender officer who records the lender's own review. **Bonik Bondhu never lends, approves or scores; the lender decides** `[SRC: MP §3; S1 §1.1]`.

## 2. MVP objective (one sentence)

A judge can follow **Registration → Financial entry → Forecast → Financing assessment → Risk explanation → Authorised lender review** on a deployed build, for a shop and a crop farm, with every number calculated by tested code and every simulated item labelled `[SRC: MP §15 File 13; S5]`.

## 3. Source basis and rules used

| ID | Source | Status |
|---|---|---|
| MP | `Bonik_Bondhu_Master_Prompt_Updated.md` | read in full; overrides older scope |
| S1 | `Bonik_Bondhu_v3_1_Team_Plan_cleaned.docx` | read in full; authoritative concept |
| S2 | `Bonik_Bondhu_One_Page_Summary.docx` | read in full |
| S5 | `Bonik_Bondhu_3min_Video_Script.docx` | read in full |
| S6 | `Bonik_Bondhu_Complete_Source_Based_Architecture.md` | read in full |
| S3, S4 | `EVENT.txt`, `judge.txt` | **unavailable** (referenced by S6, not in ZIP) |

Every project-specific statement carries a tag: `[SRC: …]` (from a source), `[DERIVED: …]` (implements a sourced requirement), or **`[SUG-xx]` — Suggestion, Not Approved, Outside Current Sources** (MP §23 rule 3). SUG items are pending defaults: **nothing tagged SUG may be implemented until approved** in Phase 0 task P0-T01. No web research was done (MP §23 rule 4); provider free-tier limits are therefore **not verified** (GAP-05).

## 4. Document structure

```text
Bonik_Bondhu_MVP_Blueprint/
├── README.md                                   ← you are here
├── 01_Product/
│   ├── MVP_SCOPE_AND_SOURCE_MAPPING.md         BB-DOC-01  what is in/simplified/deferred and why
│   └── PRD.md                                  BB-DOC-02  requirements FR-*, user stories, permissions
├── 02_Experience/
│   ├── APP_FLOW.md                             BB-DOC-03  flows for owner, farmer, lender, multi-profile + exceptions
│   └── UI_UX_SPECIFICATION.md                  BB-DOC-04  tokens, screens SCR-*, wireframes, bn/en microcopy
├── 03_Technical/
│   ├── TRD.md                                  BB-DOC-05  stack, repo layout, env, local dev, deployment
│   ├── SYSTEM_ARCHITECTURE.md                  BB-DOC-06  components, modules M-*, algorithms, RBAC, fallbacks
│   ├── DATABASE_SCHEMA.md                      BB-DOC-07  ER diagram, data dictionary, ownership, migrations
│   ├── schema.sql                              migration 0001 (tested on PostgreSQL 16)
│   ├── seed_demo.sql                           DEMO data D1–D4 (fictional, relative dates)
│   └── API_SPECIFICATION.md                    BB-DOC-08  58 endpoints, errors, examples, snapshot format
├── 04_AI_and_Security/
│   ├── AI_AND_DATA_STRATEGY.md                 BB-DOC-09  real vs simulated, provider adapter, prompts, privacy
│   └── SECURITY_AND_PRIVACY.md                 BB-DOC-10  threats→controls, consent model, SEC-01..20
├── 05_Development/
│   ├── IMPLEMENTATION_PLAN.md                  BB-DOC-11  phases P0–P7, task IDs, DoD, kill switches
│   ├── TESTING_AND_ACCEPTANCE.md               BB-DOC-12  golden cases, test IDs, traceability
│   └── reference_calculations.py               executable oracle for all money rules
└── 06_Handoff/
    ├── HACKATHON_DEMO_AND_HANDOFF.md           BB-DOC-13  demo scripts, honesty table, checklists
    └── DECISIONS_ASSUMPTIONS_AND_BACKLOG.md    BB-DOC-14  DEC/SUG/ASM/CON/GAP/BL register
```

## 5. Chosen stack

React + Vite + Tailwind (frontend) · Python FastAPI modular monolith (backend) · PostgreSQL (database) · phone + password auth with server sessions · Gemini behind a provider adapter with a non-LLM fallback `[SRC: S1 §8; S2; MP §10–11; DEC-01, DEC-02, DEC-22]`. Library-level choices are SUG items (TRD §1).

## 6. MVP at a glance

| In MVP | Simplified | Deferred (backlog) |
|---|---|---|
| Accounts, multi-profile, ledger (12 types), debts, suppliers, crop seasons, forecast baseline, funding gap, due-date & harvest checks, consent + lender review | F1 (manual + photo draft), F7 (no stock-turnover check), L1 (curated list), L2 (stage 1), F12 (text, tools, static help), F10 (snapshot + hash) | Voice, statements, Monte Carlo, optimizer, Business Health card, repayment gate, capital-use history, early warning, ZKP, GNN, poultry/fish/cattle, Buy/Sell, OTP/reset |

Full mapping: `01_Product/MVP_SCOPE_AND_SOURCE_MAPPING.md`.

## 7. Development order

P0 Foundation & approvals → **P1 Auth + profiles + first vertical slice** → P2 Financial data engine → P3 Assessment → P4 Supplier & news (deterministic) → P5 Consent & lender → P6 AI → P7 Integration, deployment, demo. AI comes after the lender flow so that the core financial thread is safe even if AI slips (DEC-23; S1 §12.2 kill switch).

**First development task:** P0-T01 approve the SUG register, then P0-T02…T05 to reach `GET /api/v1/health` → `{"status":"ok","db":"ok"}` on the migrated schema.

## 8. How to use this blueprint

| You are… | Read in this order |
|---|---|
| Product/research lead | README → Scope map → PRD → Decisions → Demo |
| Backend developer / coding AI | PRD §6 → Database schema + `schema.sql` → API spec → Architecture §5 → `reference_calculations.py` → Implementation plan (your phase) → Testing |
| Frontend developer | PRD → App flow → UI/UX spec → API spec → Implementation plan |
| Security reviewer | Security doc → Architecture §8–9 → API spec §1/§3 → DB doc §8 |
| AI/data lead | AI strategy → API spec §4.5/§4.10/§4.13 → Testing §5 |

Coding-AI instruction: implement one task ID at a time from `IMPLEMENTATION_PLAN.md`, use the exact names from `DATABASE_SCHEMA.md` / `API_SPECIFICATION.md`, and make the related tests in `TESTING_AND_ACCEPTANCE.md` pass before moving on.

## 9. What was verified while writing

- `schema.sql` (24 tables) and `seed_demo.sql` executed on PostgreSQL 16; 18 constraint negative tests rejected as expected; seed aggregates equal golden values.
- `reference_calculations.py` executed; its outputs are the golden numbers in Testing §4.
- Nothing else is claimed as built or measured.

## 10. Final consistency and feasibility review (MP §21)

| Check | Answer | Evidence |
|---|---|---|
| Can users register and log in? | Yes | PRD FR-AUTH-*; API §4.2; P1 |
| Does data persist correctly? | Yes (PostgreSQL, no local-storage data) | DB doc; TRD §3 |
| Are records isolated between users? | Yes — service ownership checks + composite FKs | Security T2; DB doc §1, §8; SEC-03..05 |
| Can shop owners enter and review records? | Yes | FR-LED-*; SCR-O04/O06/O07 |
| Can a crop farmer use a seasonal workflow? | Yes (crop only) | FR-SEA-*; SCR-F01..F05; D3 |
| Can one user manage multiple profiles without mixing data? | Yes | DEC-04; App flow §5 |
| Can the platform calculate a simple forecast? | Yes (rolling weekly baseline) | Architecture §5.1; golden D1 |
| Can it explain a financing request? | Yes — gap, request−gap prompt, how-calculated tab | FR-FIN-*, FR-ASM-08 |
| Bounded assessment without inventing approval? | Yes — three statuses; forbidden-words test | DEC-10; AT-20 |
| Are L1/L2 meaningfully connected to the analysis? | Yes — they create dated what-if scenarios on the same projection; never change status | Architecture §5.5–5.6; DEC-30 |
| Can the AI advisor answer from authorised data? | Yes — read-only, session-bound tools + grounding check | AI doc §8; SEC-19 |
| Can a lender view only consented information? | Yes — snapshot of approved sections, org-bound, expiring, revocable | Security §4; SEC-08..13 |
| Are missing data and failed APIs handled? | Yes | App flow §7; Architecture §9; Testing §9 |
| Is every main screen connected to a backend action? | Yes — UI inventory lists endpoint per screen; no Buy/Sell screen | UI §5 |
| Can a small team implement it? | Yes with kill switches; AI is last and optional | Plan §1.1 |
| Does each phase end in something testable? | Yes | Plan + Testing §12 gates |
| Are PRD, TRD, schema, APIs and flows consistent? | Checked by script: all DEC/SUG/GAP/BL/FR/SCR/test IDs resolve; endpoint paths match API index; 17 Mermaid diagrams parse | this review |

## 11. Open items that need people, not code

GAP-01 (event files), GAP-02 (real lender terms), GAP-03 (price/yield data), GAP-04 (real news curation), **GAP-05 (provider limits — needs your approval for web research)**, GAP-06 (team roles), GAP-07 (host), GAP-08 (preliminary round status), GAP-09 (lender interviews), GAP-10 (legal review). Details: `06_Handoff/DECISIONS_ASSUMPTIONS_AND_BACKLOG.md` §5.
