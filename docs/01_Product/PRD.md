# PRODUCT REQUIREMENTS DOCUMENT (PRD) — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-02 · **Version:** 1.0 (12 Nov 2026) · **Status:** Draft for team approval
**Depends on:** `MVP_SCOPE_AND_SOURCE_MAPPING.md` · **Referenced by:** every later document
Tags (`[SRC]`, `[DERIVED]`, `[SUG-xx]`, `[GAP-xx]`) are defined in `06_Handoff/DECISIONS_ASSUMPTIONS_AND_BACKLOG.md` §0.

---

## 1. Product overview

Bonik Bondhu (বণিক বন্ধু) is a mobile-first, bilingual (Bangla/English) web application that helps Bangladeshi micro/small shop owners and crop farmers record their money, see a correct financial summary, forecast near-term cash, describe a financing need, test whether a proposed repayment fits their cash under stated assumptions, see supplier and news-based what-if risks, and share a consent-scoped case file with an authorised lender officer who records the lender's own review. `[SRC: S1 §1.1, §2; MP §3]`

**Pitch line:** *Loans that move with your money* `[SRC: S1 §1.1; S2]`

**Core boundary:** Bonik Bondhu assesses readiness and scenarios. **The lender makes the lending decision.** Bonik Bondhu never lends, never approves, never disburses, never calculates a credit score or probability of default. `[SRC: MP §3; S1 §1.1, §7, §13.1]`

## 2. Problem statement

- Collections of small businesses arrive in waves (Eid peaks, monsoon dips, harvests) while many loans are repaid in fixed amounts. `[SRC: S2 "Problem"; S1 §1.1]`
- Owners often carry samity, mohajon, supplier and dealer debt that no single lender sees in full. `[SRC: S2; S1 §3, §5.1]`
- One late supplier or a local disruption can empty their cash. `[SRC: S2; S1 L2]`
- Cited context (always with source and year): ShopUp (2021) reported about 27.5% of small businesses with formal-finance access and about 4.5 million neighbourhood shops. `[SRC: S1 §1.2]` These are 2021-attributed figures, not current statistics.

## 3. Target users

| Persona | Description | Main need in MVP | Source |
|---|---|---|---|
| **P1 Shop owner** ("Rahim-type", DEMO) | Grocery / small retail / local trader / small service business | Record money simply; see summary and forecast; check if a financing request fits | MP §4A; S1 §2 |
| **P2 Crop farmer** | Seasonal crop producer (e.g. Boro rice) | Plan a season, record costs and sales, check harvest-aligned repayment | MP §4B; S1 §5 |
| **P3 Multi-activity owner** | One person with a shop and farmland | Switch between profiles without mixing data | MP §5 |
| **P4 Lender officer** (bank/MFI, manually provisioned) | Reviews consented case files | See structured, honest case; request info; record own decision | MP §4C; S1 §7 |
| Admin (internal) | Team operator | Provision lenders, seed demo, reset passwords via CLI | S1 §2; DEC-24 |

## 4. Goals and non-goals

### 4.1 Goals (MVP)
- G1: One complete, working end-to-end path: register → record → summary → forecast → financing request → assessment → risk scenarios → consent → lender review. `[SRC: MP §1, §22]`
- G2: Correct accounting under S1's rules, verified by automated tests. `[SRC: S1 F2, A4; MP §7]`
- G3: Honest outcomes: insufficient information, base-case stress, ready for lender review — never a fabricated approval. `[SRC: MP §3]`
- G4: Bilingual, low-literacy-friendly UI. `[SRC: MP §9]`
- G5: Secure defaults: hashed passwords, ownership checks on every endpoint, consent-scoped lender access, audit log. `[SRC: MP §13]`

### 4.2 Non-goals (MVP)
Real lending, disbursement, collections, CIB access, credit scoring, probability of default, optimizer-generated loan offers, Monte Carlo, ZKP, GNN, voice, statement import, poultry/fish/cattle, Buy/Sell marketplace, OTP verification, password-reset self-service, NID collection, production compliance claims. `[SRC: MP §17; S1 §12.1; scope map §2]`

## 5. MVP feature list

| Feature | Short description | Scope ref |
|---|---|---|
| Accounts & sessions | Register (name, phone, email, password), phone+password login, logout, expiry | MP §8 |
| Profiles | Many profiles per owner; shop or crop farm; switcher | MP §5 |
| F1 Entry | Manual entries; optional receipt-photo AI draft with confirmation | MP §6 F1 |
| Ledger & summary (F2 internal) | Accounting-correct totals | MP §7 |
| Debts (internal) | Declared existing obligations | MP §7 |
| Crop seasons | Season plan, costs, harvest/sales, income range, break-even, loan-cover price | MP §4B |
| F3 Forecast | Weekly baseline expected/low/high, insufficient history | MP §6 F3 |
| F7 Financing request & gap | Purpose items with price source, gap, request−gap prompt, proposed terms | MP §6 F7 |
| Assessment | Due-date affordability (shop) / harvest check (farm), statuses, flags | MP §3 |
| L2 Supplier intelligence | Suppliers, concentration, delay/price scenarios | MP §6 L2 |
| L1 News radar | Curated events matched to profile; scenario proposals | MP §6 L1 |
| F12 Advisor | Bilingual grounded text chat | MP §6 F12 |
| Consent & report | Lender requests, owner approves scope/validity, snapshot, revoke | MP §7 |
| Lender portal | Case list, case file, notes, info requests, demo decision | MP §4C |

## 6. Functional requirements

Each requirement is testable. Test IDs are in `05_Development/TESTING_AND_ACCEPTANCE.md` traceability matrix.

### 6.1 Authentication & accounts (AUTH)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-AUTH-01 | Owner can register with full name, phone, email, password | Valid input → 201, user role `owner`, user can log in immediately | MP §8 |
| FR-AUTH-02 | Phone and email must be unique | Second registration with same normalised phone or same email (case-insensitive) → 409 `PHONE_TAKEN` / `EMAIL_TAKEN` | MP §8 |
| FR-AUTH-03 | Password stored only as a strong hash | DB contains no plaintext; hash verifies; algorithm per SUG-02 | MP §8, §13 |
| FR-AUTH-04 | Login with phone + password | Correct → session cookie; wrong → 401 `INVALID_CREDENTIALS` (same message whether phone exists or not) | MP §8 |
| FR-AUTH-05 | Repeated failed logins are throttled | After 5 failures for a phone, further attempts → 429 for 15 minutes `[SUG-05]` | MP §13 |
| FR-AUTH-06 | Session expires and logout revokes it | Expired or logged-out token → 401 `SESSION_EXPIRED`; UI returns to login with message | MP §8, §14 |
| FR-AUTH-07 | Lender accounts cannot self-register | `/auth/register` always creates `owner`; lender created only by CLI | MP §4C; DEC-24 |
| FR-AUTH-08 | User can choose UI language `bn` or `en`; stored on account | `PATCH /auth/me` updates `preferred_language`; persists after relogin | MP §9 |
| FR-AUTH-09 | No self-service password reset | Login screen shows "contact support" text; no reset endpoint exists | MP §8; DEC-21 |

### 6.2 Profiles (PROF)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-PROF-01 | Owner can create multiple profiles of type `shop` or `crop_farm` | Two profiles of different types under one user both listed | MP §5 |
| FR-PROF-02 | Minimum to create a profile: display name + activity type | Other fields optional at creation | MP §8 progressive |
| FR-PROF-03 | Every owner data record belongs to exactly one profile | All owner tables have NOT NULL `profile_id` FK | MP §5 |
| FR-PROF-04 | Active profile is always visible | Header shows profile name + type icon on every owner screen | MP §5 |
| FR-PROF-05 | Owner cannot read/modify another user's profile or its children | Any `profile_id` not owned → 404 `NOT_FOUND` (no existence leak) | MP §12, §13 |
| FR-PROF-06 | Financing fields (district, upazila, business category, household withdrawal) are requested only when starting a financing request or sharing | Path A users are never forced to fill them | MP §8 |
| FR-PROF-07 | Each profile has a random **share code** used by lenders as a locator | 10-character code; regenerable by owner; regeneration does not affect existing consents | S1 F10; DEC-18 |

### 6.3 Ledger & entries (LED) — F1 + F2 internal

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-LED-01 | Owner can add a manual entry with type, amount, date, optional supplier, optional debt link, optional note | Saved entry appears in list and summary after reload | MP §6 F1 |
| FR-LED-02 | Supported entry types (12): `sale_cash`, `sale_credit`, `receivable_collection`, `purchase_cash`, `purchase_credit`, `payable_payment`, `operating_expense`, `loan_received`, `loan_principal_repayment`, `loan_interest_fee_payment`, `owner_withdrawal`, `owner_contribution` | UI shows simple bilingual labels (UI spec §7.3) | S1 F2 `[DERIVED]` |
| FR-LED-03 | Accounting effects follow S1 rules | Golden fixture E1 in Testing §4.1 passes exactly | S1 F2, A4 |
| FR-LED-04 | Amount > 0, ≤ 99,999,999,999.99; date not more than 1 day in the future; currency BDT | Invalid → 422 with field error in user's language | MP §13 |
| FR-LED-05 | Possible duplicate entries trigger a warning | Same profile+type+amount+date(+supplier) as existing confirmed entry → 409 `POSSIBLE_DUPLICATE`; resubmit with `confirm_duplicate=true` saves `[SUG-28]` | S1 A4 |
| FR-LED-06 | Entries are never hard-deleted by users; they can be voided with a reason | Voided entries excluded from all calculations, still visible as "voided" | S1 A1 `[DERIVED]` |
| FR-LED-07 | Every entry has evidence state `declared` or `document_attached` | Entry from confirmed photo draft = `document_attached` | S1 F1; DEC-25 |
| FR-LED-08 | Money summary for a date range shows: sales recorded, cash sales, credit sales, operating cash in/out, net operating cash, receivables outstanding, payables outstanding, financing received, principal repaid, interest/fees paid, owner withdrawals, owner contributions, cash net change | Values match reference implementation | S1 F2 |
| FR-LED-09 | Summary works with zero entries | Shows zeros and "No entries yet" guidance; no errors | MP §14 exceptions |
| FR-LED-10 | Idempotent creation | Same `client_request_id` twice → one row | MP §14 duplicate |

### 6.4 Receipt photo extraction (EXT) — F1 AI part

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-EXT-01 | Owner can upload one receipt photo (JPEG/PNG ≤ 5 MB) | Other types/sizes → 415/413 | MP §13; SUG-18 |
| FR-EXT-02 | AI returns a **draft** with proposed type, amount, date, supplier name, note and per-field confidence | Draft stored in `extraction_drafts`, **no transaction created** | MP §6 F1 |
| FR-EXT-03 | Owner edits and confirms the draft to create a transaction | Confirm → transaction with `entry_method=photo_assisted`, `evidence_state=document_attached` | MP §6 F1 |
| FR-EXT-04 | AI failure or quota exhaustion falls back to manual entry form with the photo attached | Error code `AI_UNAVAILABLE`; form pre-opened; app continues | MP §11, §14 |
| FR-EXT-05 | Owner is told before upload that the photo will be sent to the AI provider | Consent checkbox required once per upload | MP §11 |

### 6.5 Debts (DEBT) — F2 internal

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-DEBT-01 | Owner can declare an existing obligation: lender type (bank, mfi, ngo, samity, mohajon, supplier_credit, dealer_credit, other), label, original principal, outstanding balance, installment amount, frequency (weekly, monthly, single), next due date, overdue flag & amount | Saved and listed | S1 §3, §5.1 |
| FR-DEBT-02 | Owner can explicitly declare "no current loans" | Stored timestamp; required (either ≥1 debt or this declaration) before assessment | S1 F6 ("absence … not proof of no debt") |
| FR-DEBT-03 | Declared debts generate dated installments inside the forecast horizon | Matches reference `existing_debt_schedule` | S1 F3 |
| FR-DEBT-04 | Debts are labelled "declared by owner"; CIB placeholder text shown | "Official credit checks are done by the lender outside Bonik Bondhu" | S1 F9 |

### 6.6 Crop seasons (SEA)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-SEA-01 | Farm profile can create a season: crop name, variety (optional), season name (Aman/Boro/Aus/Winter vegetables/Other), area value + unit (acre, decimal, sq_ft, bigha), sowing date, expected harvest date | Saved; area converted to acres and shown | MP §4B; S1 §5 |
| FR-SEA-02 | Bigha requires owner-entered factor "1 bigha = N decimal" | Missing factor → 422 `BIGHA_FACTOR_REQUIRED` | MP §4B; SUG-14 |
| FR-SEA-03 | Season stores expected output low/expected/high (kg) and expected price low/expected/high (Tk/kg), labelled "your estimate" | Income range = output × price for each case | S1 §5 crop row; ASM-02 |
| FR-SEA-04 | Season plan cost items (seed, fertilizer, pesticide, irrigation, labour, land lease, transport, other) with quantity, unit, unit cost | Total planned cost shown | S1 §5 |
| FR-SEA-05 | Actual farm costs and sales are recorded as ledger entries linked to the season | Season summary shows planned vs actual paid | DEC-27 |
| FR-SEA-06 | Record harvest: actual date, actual output | Season status → `harvested`; summary shows actual vs expected | S1 §5.1 stage 4 |
| FR-SEA-07 | Season summary shows income range, total planned cost, actual cost paid, actual sales, break-even price, loan-cover price (when a financing request exists) | Matches reference `crop_check` | S1 §5.1; SUG-13 |
| FR-SEA-08 | Farmer is never asked for daily entries | Season screens do not require daily records; forecast screen not shown for farm profiles | MP §4B |

### 6.7 Suppliers (SUP) — L2

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-SUP-01 | Owner can add suppliers: name, goods supplied, district/upazila, optional declared purchase share % | Saved per profile | MP §6 L2; S1 §3 |
| FR-SUP-02 | Purchase entries can be linked to a supplier | `supplier_id` on transaction | S1 L2 |
| FR-SUP-03 | Concentration = each supplier's share of linked purchase payments over the last 8 weeks; if < 2 linked purchases exist, use declared shares and label "owner-reported" | Values match reference `concentration` | S1 L2; S5 fallback |
| FR-SUP-04 | Top-supplier share ≥ threshold shows "high dependency" flag with explanation | Threshold `[SUG-10]` | S1 L2 |
| FR-SUP-05 | No suppliers → message "Add your main suppliers to see dependency risk"; assessment still works | No error | MP §14 |
| FR-SUP-06 | Sparse data is never shown as low risk | Text: "Few suppliers recorded — this does not mean low risk" | S1 L2 cold-start rule |

### 6.8 Forecast (FC) — F3

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-FC-01 | Shop profile can generate a forecast | Stored `forecast_runs` row with method version and assumptions | MP §6 F3 |
| FR-FC-02 | Baseline per SUG-07: weekly net operating cash expected/low/high; collections and payments expected shown separately | Matches reference `weekly_baseline` | S1 F3 |
| FR-FC-03 | Fewer than 4 weeks with records → status `insufficient_history` with "N of 4 weeks recorded" message | No numbers shown as forecast | S1 F3; MP §6 F3 |
| FR-FC-04 | Horizons shown: 7, 30, 60, 90 days (expected and low cumulative net cash, and known scheduled debt payments in each horizon) | Values = daily baseline × days; debts from schedule | S1 F3 |
| FR-FC-05 | Every forecast screen shows "This is an estimate, not guaranteed income" | Text present in both languages | MP §6 F3 |
| FR-FC-06 | Record coverage displayed: weeks with records / 8 | Not called a score | DEC-13 |

### 6.9 Financing request (FIN) — F7

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-FIN-01 | Owner creates a financing request: requested amount, purpose text, purpose category (inventory, farm inputs, equipment, other), desired start date | Draft saved | MP §6 F7 |
| FR-FIN-02 | Owner adds purpose items: name, quantity, unit, unit price, price source type (`supplier_quote`, `own_purchase_history`, `reference_market_price`, `public_listing`, `owner_estimate`), price date, source note | Line total = qty × unit price | S1 F7 price evidence order |
| FR-FIN-03 | Optional AI parsing of purpose text into proposed items; owner must confirm each | Unconfirmed AI items excluded from gap | S1 F7 step 1; MP §6 F7 |
| FR-FIN-04 | Owner enters associated necessary expenses, liquidity buffer + justification, cash safely available, already committed financing | Required before assessment | S1 F7 formula |
| FR-FIN-05 | Funding gap = max(0, items + associated expenses + buffer − cash safely available − committed financing) | Matches reference `funding_gap` | S1 F7, A2 |
| FR-FIN-06 | If request > gap, show difference and ask for an explanation (free text), without negative wording | Flag `request_exceeds_gap` | S1 F7; SUG-11 |
| FR-FIN-07 | Owner enters proposed repayment: schedule type, number of installments, frequency, first due date, total interest+fees (may be "unknown" → flag), current cash balance (optional), minimum cash reserve | Label "Your proposal — not a lender offer" | DEC-11, DEC-28, DEC-35 |
| FR-FIN-08 | Farm request may be linked to a season and can copy unfunded season cost items as purpose items | Copied items editable | DEC-27 |
| FR-FIN-09 | Weak price evidence flagged when all items are `owner_estimate` | Flag `weak_price_evidence` | S1 F7 |

### 6.10 Assessment (ASM)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-ASM-01 | Owner can run an assessment on a financing request | Stored `financial_assessments` row, inputs snapshot hash | MP §14 |
| FR-ASM-02 | Status `insufficient_information` when any of: no debt declaration, household withdrawal not declared, no confirmed purpose items, terms incomplete, forecast insufficient (shop), season incomplete (farm), due date beyond 90-day horizon (shop), repayment due before expected harvest (farm) | `missing_items` lists codes; UI shows bilingual fix-it actions | MP §3; DEC-33 |
| FR-ASM-03 | Shop: daily projection in low base case checked at every due date (existing + new); shortfall if balance after payment < reserve | Matches reference `shop_due_date_checks` | S1 A2; DEC-29 |
| FR-ASM-04 | Farm: harvest check (pre-harvest balance, available at due date) | Matches reference `crop_check` | S1 §5.1 |
| FR-ASM-05 | Status `not_affordable_base_case` when base case has any shortfall (shop) or not covered / pre-harvest shortfall (farm); show first shortfall date and amount | Golden case D2 | MP §3 |
| FR-ASM-06 | Status `ready_for_lender_review` otherwise, with flags listed | Golden cases D1, D3 | MP §3 |
| FR-ASM-07 | Assessment never shows approval language, credit score, eligibility % or probability of default | UI copy review + test asserting forbidden words absent from API payload | MP §17 rules 12, 14 |
| FR-ASM-08 | Assessment shows formulas, assumptions and each input's source/evidence state | "How we calculated" section | MP §3; S1 F2 |
| FR-ASM-09 | Changing inputs makes the previous assessment `stale`; new run required before sharing | `is_stale` true after any change | S1 A4 "changed loan terms re-evaluated" |

### 6.11 Scenarios (SCN) — L1/L2 connection

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-SCN-01 | Shop scenarios: supplier delay 7 or 14 days, input price rise 15% (on top supplier share) | Results match reference D1 | S1 L2 |
| FR-SCN-02 | Farm scenarios: harvest price fall, yield shortfall, input price rise 15% | Results match reference D3 | S1 §5; SUG-12 |
| FR-SCN-03 | Scenario results shown next to base case; **status unchanged** | Scenario shortfall adds a flag only | DEC-30 |
| FR-SCN-04 | Every scenario shows its assumption in plain words | e.g. "We assumed 65% of your weekly net cash stops for 7 days" | S1 L1 step 6 |

### 6.12 News signals (NEWS) — L1

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-NEWS-01 | System holds curated news events with headline, source name, URL, published date, event date, event type, districts, upazila, sectors, commodities, source count, `is_demo` | Imported via CLI from a CSV/JSON file | MP §6 L1; DEC-15 |
| FR-NEWS-02 | Profile sees events matching its district/upazila, its business category/commodity, or a supplier's district, within the last 30 days or upcoming | Each match shows the reason ("same district as your supplier") | S1 L1 step 4 |
| FR-NEWS-03 | Each card shows source, date, location, single-source vs corroborated, DEMO label if fictional | All fields visible | MP §6 L1 |
| FR-NEWS-04 | A matched event can **propose** a scenario; owner must confirm before it runs | Proposed → confirmed/dismissed | S1 L1 step 6 |
| FR-NEWS-05 | Only headline, link, short team-written summary stored; no full article text | Schema has no article body column | S1 L1 step 1, §11 copyright |
| FR-NEWS-06 | If news data is empty/unavailable, every other feature works | Test with empty table | MP §6 L1 |

### 6.13 AI advisor (ADV) — F12

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-ADV-01 | Owner can chat in Bangla or English about the active profile | Reply in the user's language | MP §6 F12 |
| FR-ADV-02 | Advisor answers only via read-only tools scoped to the active profile from the session | Tool layer ignores any profile id in model output | MP §6 F12, §13 |
| FR-ADV-03 | Every number in a reply must appear in tool output of the same turn | Violations replaced by safe template `[SUG-23]` | S1 F12 |
| FR-ADV-04 | Missing data → advisor names the missing item and the screen to fill it | Gold questions in E10 set | S1 F12 |
| FR-ADV-05 | Advisor never says a loan is approved/eligible; refers to lender | Forbidden-phrase test | S1 F12 |
| FR-ADV-06 | News answers cite source and say "reported", not "confirmed" | E10 check | S1 F12 |
| FR-ADV-07 | LLM unavailable → button-based help menu with deterministic explanations | Works with `LLM_PROVIDER=none` | MP §11 |
| FR-ADV-08 | Daily per-user message cap | 31st message → friendly limit message `[SUG-05]` | MP §11 |

### 6.14 Consent & sharing (CON)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-CON-01 | Lender officer submits an access request with an owner's share code, requested sections and message | Response is identical whether or not code exists ("If the code is valid, the owner will see your request") | S1 F10; MP §13 |
| FR-CON-02 | Owner sees pending requests with lender organisation name, officer name, requested sections | Listed on Sharing screen | S1 F10 |
| FR-CON-03 | Owner approves with chosen sections (subset allowed), chosen financing request, validity 7/14/30 days | Creates consent `approved` + snapshot; requires a non-stale assessment | S1 F10; SUG-21 |
| FR-CON-04 | Owner can decline or revoke at any time | Lender access stops immediately → 403 `CONSENT_REVOKED` | S1 F10 |
| FR-CON-05 | Access after `valid_until` → 403 `CONSENT_EXPIRED` | Test with clock override | MP §14 |
| FR-CON-06 | Snapshot contains only approved sections; SHA-256 shown to both sides | Unapproved section keys absent from JSON | S1 F10; DEC-19 |
| FR-CON-07 | Every lender read is logged in `audit_logs` and visible to the owner as "viewed on <date> by <org>" | Log row per read | S1 F10 |
| FR-CON-08 | Owner warned that information already seen cannot be "unseen" | Warning text at approval | S1 F10 |
| FR-CON-09 | Owner can share an updated snapshot (new version) to the same lender | Version number increments; lender sees latest | S1 F10 |

### 6.15 Lender portal (LEN)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-LEN-01 | Only `lender_officer` users access `/lender/*` | Owner → 403 | MP §4C |
| FR-LEN-02 | Case list shows only cases with consents created by the officer's organisation | Other orgs' cases invisible | MP §4C |
| FR-LEN-03 | Case file shows approved snapshot sections, consent validity, snapshot hash, evidence mix, and the CIB placeholder | Matches S1 §7 sections listed in scope map §2.4 | S1 §7 |
| FR-LEN-04 | Officer can set review status `under_review` / `info_requested` and add notes (private to lender org) | Stored in `lender_review_events` | MP §4C |
| FR-LEN-05 | Officer can request information; owner sees the request text | Owner Sharing screen shows it | MP §4C |
| FR-LEN-06 | Officer can record a **demo decision** (`proceed`, `decline`, `refer`) with mandatory reason | Banner "Demo decision recorded by lender. Bonik Bondhu does not issue loans." | MP §4C; S1 §7 |
| FR-LEN-07 | Lender UI has no transaction-entry or farm screens | Route guard | MP §9 |

### 6.16 Bilingual UI & accessibility (I18N)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-I18N-01 | All labels, errors, onboarding, financial explanations exist in `bn` and `en` | CI check: no missing keys in either file | MP §9 |
| FR-I18N-02 | Language switch on every screen header (owner) and settings | Instant switch without reload | MP §9 |
| FR-I18N-03 | Icons always paired with text labels; touch targets ≥ 44 px | UI review checklist | MP §9 |
| FR-I18N-04 | Numbers shown with Tk and grouping; Bangla digits in `bn` mode for display only | Inputs accept both digit sets | MP §9 `[DERIVED]` |

### 6.17 Demo data (DEMO)

| ID | Requirement | Acceptance criteria | Source |
|---|---|---|---|
| FR-DEMO-01 | Seed command creates DEMO users D1–D4, demo lender org and officers, demo news events | All rows `is_demo=true`; UI shows "DEMO" badge | MP §18 |
| FR-DEMO-02 | Demo data dates are relative to seed date so the forecast always has history | Re-seed works on any date | MP §18 |
| FR-DEMO-03 | Demo users cannot be used to view real users' data and vice versa | Normal ownership rules | MP §12 |

## 7. Non-functional requirements

| ID | Requirement | Measure | Source |
|---|---|---|---|
| NFR-01 | Mobile-first: usable at 360 px width | Manual check all owner screens | MP §9 |
| NFR-02 | Fast: owner pages interactive < 3 s on a mid-range phone over 4G for demo data | Lighthouse/manual timing | MP §9 |
| NFR-03 | Core features work with AI disabled | Full E2E with `LLM_PROVIDER=none` | MP §11, §17 rule 5 |
| NFR-04 | All protected endpoints enforce auth + role + ownership server-side | Negative tests SEC-* | MP §12, §13 |
| NFR-05 | No secrets in frontend bundle | Build grep check | MP §11 |
| NFR-06 | Deterministic engine: same inputs → same outputs | Golden tests | S1 A3 |
| NFR-07 | Audit log for auth events, consent changes, lender reads, lender decisions | Rows present | S1 §11, F10 |

## 8. User stories (with acceptance)

| ID | As a… | I want… | So that… | Accept when |
|---|---|---|---|---|
| US-01 | shop owner | to register with only name, phone, email, password | I can start fast | FR-AUTH-01 passes |
| US-02 | shop owner | to record today's sales and rent in under a minute | I keep records | 2 entries saved from Home in ≤ 6 taps each |
| US-03 | shop owner | to see how much came in and went out this month | I understand my money | Summary correct (FR-LED-08) |
| US-04 | shop owner | to snap a receipt and fix the amount before saving | I avoid typing | FR-EXT-02/03 |
| US-05 | shop owner | to know if a Tk 2 lakh request fits my cash | I avoid over-borrowing | Assessment status + reasons shown |
| US-06 | shop owner | to know why the request is higher than my need | I can explain to the lender | Request−gap prompt (FR-FIN-06) |
| US-07 | shop owner | to see what happens if my main supplier is late | I can prepare | 7/14-day scenario (FR-SCN-01) |
| US-08 | farmer | to plan Boro season costs on 1.5 acres entered as 150 decimal | My unit is understood | FR-SEA-01 |
| US-09 | farmer | to know the minimum price per kg needed to repay | I can decide when to sell | Loan-cover price (FR-SEA-07) |
| US-10 | owner with shop and farm | to switch between them | records don't mix | FR-PROF-01/04 |
| US-11 | owner | to choose exactly what a lender sees and for how long | I keep control | FR-CON-03/04 |
| US-12 | lender officer | to see a structured case with limitations stated | I can review faster | FR-LEN-03 |
| US-13 | lender officer | to ask for a supplier quotation | I get missing evidence | FR-LEN-05 |
| US-14 | lender officer | to record my institution's decision and reason | the review is documented | FR-LEN-06 |
| US-15 | owner | to ask "how much do I owe next week?" in Bangla | I understand without reports | FR-ADV-01/03 |

## 9. Permissions matrix

| Capability | Owner (own profiles) | Owner (other's profiles) | Lender officer | Admin (CLI) |
|---|---|---|---|---|
| Register / login | ✔ | — | login only | — |
| Profiles CRUD | ✔ | ✘ (404) | ✘ | — |
| Transactions, debts, suppliers, seasons, requests | ✔ | ✘ (404) | ✘ | — |
| Forecast, assessment, scenarios | ✔ | ✘ | ✘ | — |
| Advisor | ✔ (active profile only) | ✘ | ✘ | — |
| Approve / revoke consent | ✔ | ✘ | ✘ | — |
| Request access (share code) | ✘ | ✘ | ✔ | — |
| Read case snapshot | ✘ | ✘ | ✔ only own org + approved + valid | — |
| Review events / demo decision | read info requests | ✘ | ✔ own org cases | — |
| Create lender org/officer, reset password, seed, import news | ✘ | ✘ | ✘ | ✔ |

## 10. Product constraints

- Budget: free/open-source tools; free LLM tier assumed but **not verified** (GAP-05). `[MP §11]`
- No paid SMS/email/identity services. `[MP §8]`
- Team: small student team; roles per S1 §12.4 merged as needed (GAP-06).
- Time: remaining S1 build window to 25 Dec 2026 (SUG-27; CON-10).
- Honesty: every demo number from the system or labelled (S5).

## 11. Edge cases (must be handled)

| Case | Expected behaviour | Req |
|---|---|---|
| New user, no entries | Empty states with "Add first entry" | FR-LED-09 |
| 2 weeks of history | Forecast `insufficient_history`; assessment insufficient | FR-FC-03 |
| Weekly-only recorder | Forecast works (weeks, not days) | ASM-01 |
| Credit sale then collection | Cash only on collection | FR-LED-03 |
| Loan received recorded | Not sales | FR-LED-03 |
| Duplicate entry | Warning; explicit confirm | FR-LED-05 |
| Wrong entry | Void with reason | FR-LED-06 |
| Request less than gap | No over-request flag; assessment still runs | FR-FIN-06 |
| Interest/fees unknown | Treated as 0 with flag `interest_fees_unknown` | FR-FIN-07 |
| Term > 90 days (shop) | Insufficient: `term_beyond_forecast_horizon` | DEC-33 |
| Due before harvest (farm) | Insufficient: `repayment_due_before_expected_harvest` | FR-ASM-02 |
| Bigha without factor | 422 | FR-SEA-02 |
| No suppliers | Message; no scenario for supplier | FR-SUP-05 |
| News API/data empty | Section hidden with note | FR-NEWS-06 |
| AI down | Manual path | FR-EXT-04, FR-ADV-07 |
| Lender with wrong code | Same generic reply | FR-CON-01 |
| Consent expired/revoked | 403 with message | FR-CON-04/05 |
| Inputs changed after assessment | Stale; must rerun before sharing | FR-ASM-09 |

## 12. Success criteria (hackathon)

1. All Must-pass tests in `TESTING_AND_ACCEPTANCE.md` green (golden cases D1–D4, E1 fixture, SEC-*).
2. Two scripted demos (shop D1, farm D3) run end-to-end on the deployed system in ≤ 4 minutes each without manual DB edits.
3. Lender sees only consented sections; revoke takes effect on next request.
4. App fully usable with AI disabled.
5. No screen exists without a working backend action.
6. No claim in the demo beyond what is in `HACKATHON_DEMO_AND_HANDOFF.md` §2 "What is real".
