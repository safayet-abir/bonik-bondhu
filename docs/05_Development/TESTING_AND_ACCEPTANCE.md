# TESTING AND ACCEPTANCE — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-12 · **Version:** 1.0 (12 Nov 2026)
**Tools:** pytest + FastAPI TestClient; optional Vitest/Playwright `[SUG-20]`
**Oracle:** `05_Development/reference_calculations.py` (run `python3 -I reference_calculations.py`; output verified 12 Nov 2026).

A phase cannot be marked complete if its critical tests fail `[SRC: MP §16]`.

---

## 1. Test layers

| Layer | Folder | Runs | Critical? |
|---|---|---|---|
| Engine unit + golden | `backend/tests/unit`, `backend/tests/golden` | every commit | Yes |
| API (functional) | `backend/tests/api` | every commit | Yes |
| Security negative | `backend/tests/security` | every commit | Yes |
| DB constraints | `backend/tests/db/test_constraints.py` (cases from DB doc §8) | every commit | Yes |
| AI (fake provider) | `backend/tests/ai` | every commit | Yes (behaviour), measured E2/E10 = reported |
| Frontend | build + i18n parity (+ optional Vitest) | every commit | Yes (build/parity) |
| E2E | Playwright or manual script (§8) | before each phase sign-off, on staging/deployed | Yes for P7 |

Fixture rule: tests that depend on dates pass an explicit `as_of_date` (default `2026-12-01` for golden cases) and seed rows relative to it.

---

## 2. Unit tests (engine)

| ID | Function | Cases |
|---|---|---|
| UT-01 | `accounting.summarize` | E1 fixture (§4.1); voided excluded; empty list → zeros |
| UT-02 | `baseline.weekly_baseline` | 8 weeks (D1); 6 of 8 (D2); 2 weeks → insufficient (D4); weeks without records counted as missing not zero |
| UT-03 | `schedules.new_loan_schedule` | 12 weekly 216,000 → 12×18,000; rounding remainder in last (e.g. 100,000/3 → 33,333.33, 33,333.33, 33,333.34); single payment; monthly from 31 Jan → 28/29 Feb |
| UT-04 | `schedules.existing_debt_schedule` | weekly 2,500 until 60,000; monthly 3,000 from as_of+10; single; skip dates before as_of; stops at horizon |
| UT-05 | `funding.funding_gap` | D1 150,000; D2 70,000; D3 40,000; negative → 0 |
| UT-06 | `projection.shop_due_date_checks` | D1 base, D2 base, D1 scenarios (§4) ; due date beyond as_of+89 → listed in `beyond_horizon` |
| UT-07 | `crop.crop_check` | D3 base + 3 scenarios; due before harvest → insufficient |
| UT-08 | `concentration` | 65/25/10 → flag true; single supplier 100%; equal 50/50 → flag true at 0.50 threshold |
| UT-09 | `units.to_acres` | 150 decimal → 1.5; 21,780 sq ft → 0.5; 2 bigha @33 → 0.66; bigha without factor → error |
| UT-10 | money rounding | ROUND_HALF_UP: 0.005 → 0.01 |
| UT-11 | grounding validator | reply with tool numbers passes; invented number fails; Bangla digits "১৮,০০০" parsed as 18000 |
| UT-12 | phone normalisation | `01712345678`, `+8801712345678`, `8801712345678` → `+8801712345678`; `01212345678` rejected |

---

## 3. API, authentication and role tests

| ID | Area | Test | Expected |
|---|---|---|---|
| AT-01 | Auth | register valid | 201, role owner |
| AT-02 | Auth | duplicate phone / email | 409 PHONE_TAKEN / EMAIL_TAKEN |
| AT-03 | Auth | login correct / wrong / unknown phone | 200+cookie / 401 / 401 (same body) |
| AT-04 | Auth | lockout after 5 failures | 429 ACCOUNT_LOCKED |
| AT-05 | Auth | logout then call /auth/me | 401 SESSION_EXPIRED |
| AT-06 | Auth | expired session (clock override) | 401 |
| AT-07 | Auth | `password_hash` never in any response | assertion over all endpoints' schemas |
| AT-08 | Profiles | create shop + farm under one user; list shows both | 200 |
| AT-09 | Ledger | create each of 12 types; link rules violations → 422 | per type |
| AT-10 | Ledger | duplicate → 409; with confirm → 201 | |
| AT-11 | Ledger | same client_request_id twice → one row | |
| AT-12 | Ledger | void → excluded from summary | |
| AT-13 | Ledger | future date (today+2) → 422 | |
| AT-14 | Seasons | create with bigha no factor → 422 BIGHA_FACTOR_REQUIRED | |
| AT-15 | Seasons | season endpoints on shop profile → 403 PROFILE_TYPE_MISMATCH | |
| AT-16 | Forecast | D4 → insufficient_history; D1 → ok values §4 | |
| AT-17 | Financing | preview gap and installments on PATCH | §4 values |
| AT-18 | Assessment | D1 ready, D2 not affordable, D3 ready, D4 insufficient (6 codes) | §4 |
| AT-19 | Assessment | change any input → latest `is_stale=true`; approve consent → 409 ASSESSMENT_STALE | |
| AT-20 | Assessment | payload contains none of: "approved", "eligible", "credit score", "probability of default" | FR-ASM-07 |
| AT-21 | Scenarios | news scenario confirm → computed; status of assessment unchanged | DEC-30 |
| AT-22 | News | empty news table → `[]`, assessment still 201 | FR-NEWS-06 |
| AT-23 | Consent | lender request → owner approves subset → lender reads only those sections | FR-CON-03/06 |
| AT-24 | Consent | reshare → version 2; lender sees latest | FR-CON-09 |
| AT-25 | Lender | info_request visible in owner activity; note not visible | FR-LEN-04/05 |
| AT-26 | Lender | decision without reason → 422; with reason → banner key | FR-LEN-06 |
| RBAC | Roles | SEC-01…SEC-16 (Security doc §7) | as listed |

---

## 4. Golden financial cases (expected outputs)

Produced by `reference_calculations.py` with `as_of = 2026-12-01`; the same records are created by `seed_demo.sql` with `as_of = CURRENT_DATE`. Dates below are written as offsets so they hold for any seed date.

### 4.1 E1 accounting fixture `[S1 Appendix A4]`
Input (confirmed unless noted): sale_cash 5,000; sale_credit 2,000; loan_received 50,000; purchase_cash 3,000; loan_principal_repayment 4,000; loan_interest_fee_payment 500; receivable_collection 1,500; owner_withdrawal 1,000; sale_cash 7,000 **voided**.

| Output | Expected | Rule proven |
|---|---|---|
| sales_recorded | 7,000.00 | credit sale counted as sales; loan not counted; voided ignored |
| cash_sales / credit_sales | 5,000.00 / 2,000.00 | |
| operating_cash_in | 6,500.00 | baki not cash until collected |
| operating_cash_out | 3,000.00 | principal and interest are not operating expense |
| net_operating_cash | 3,500.00 | |
| receivables_outstanding | 500.00 | 2,000 − 1,500 |
| financing_received | 50,000.00 | loan = financing, not sales |
| principal_repaid / interest_fees_paid | 4,000.00 / 500.00 | tracked separately |
| owner_withdrawals | 1,000.00 | separate from business cost |
| cash_net_change | 48,000.00 | 5,000 + 50,000 − 3,000 − 4,000 − 500 + 1,500 − 1,000 |

### 4.2 D1 Rahim Store (shop) — expected `ready_for_lender_review`
| Item | Expected |
|---|---|
| Weekly net operating cash (8 weeks) expected / low / high | 32,312.50 / 25,000.00 / 41,000.00 |
| Weekly collections / payments / purchases expected | 144,312.50 / 112,000.00 / 94,000.00 |
| Forecast horizons low / expected: 7 d; 30 d; 60 d; 90 d | 25,000.00 / 32,312.50; 107,142.86 / 138,482.14; 214,285.71 / 276,964.29; 321,428.57 / 415,446.43 |
| Supplier shares (56 days) | A 65.0%, B 25.0%, C 10.0%; total 752,000.00; high_dependency = true |
| Purpose items total; funding gap; request − gap | 150,000.00; 150,000.00; 50,000.00 (flag `request_exceeds_gap`) |
| New schedule | 12 weekly × 18,000.00, first as_of+7, last as_of+84 |
| Start balance; reserve | 15,000.00 (45,000 − 30,000); 10,000.00 |
| Base: payment dates checked; shortfall; min balance after payment | 12; none; 21,626.22 (at as_of+7) |
| Scenario supplier delay 7 d (share 0.65, start as_of) | shortfall: first at as_of+7, balance 623.10, shortfall 9,376.90 |
| Scenario supplier delay 14 d | first at as_of+7, balance −2,377.35, shortfall 12,377.35; min balance −16,832.08 |
| Scenario input price +15% | first at as_of+14, balance 5,534.88, shortfall 4,465.12; min balance −50,635.67 |
| Flags | `request_exceeds_gap`, `high_supplier_dependency`, `scenario_shortfall` |
| News | DEMO road blockade (Kaliakair) matched via supplier location → proposed `supplier_delay` 7 d; DEMO Dhamrai flood **not** matched |

### 4.3 D2 Karim Variety Store (shop with debts) — expected `not_affordable_base_case`
| Item | Expected |
|---|---|
| Weeks with records | 6 of 8 (2 missing weeks not zero) |
| Weekly net expected / low / high | 8,666.67 / 6,000.00 / 11,000.00 |
| Funding gap; request − gap | 70,000.00; 10,000.00 (`weak_price_evidence`: all items owner_estimate) |
| Existing installments | MFI 2,500 weekly from as_of+3 (13 in horizon); samity 3,000 monthly from as_of+10 (3 in horizon) |
| New schedule | 12 weekly × 7,000.00 from as_of+7 |
| Payment dates checked | 27 |
| First shortfall | as_of+7: balance −746.97, shortfall vs reserve 2,746.97 |
| Min balance after payment | −69,216.63 |

### 4.4 D3 Rahim Rice Farm (crop, same user as D1) — expected `ready_for_lender_review`
| Item | Expected |
|---|---|
| Area | 150 decimal = 1.5 acres |
| Income range low / expected / high | 75,600.00 / 105,600.00 / 131,250.00 |
| Planned cost; paid so far | 65,000.00; 4,500.00 (seed) |
| Funding gap; request − gap | 40,000.00; 0.00 |
| Repayment | single payment 42,400.00 on 2027-05-20 (harvest 2027-05-05) |
| Remaining costs outside request; start balance | 8,500.00; 8,500.00 (23,500 − 15,000) |
| Base: pre-harvest balance; available at due; surplus | 0.00; 64,600.00; 22,200.00 (covered) |
| Break-even price; loan-cover price | 19.70 Tk/kg; 19.78 Tk/kg |
| Harvest price −15% | available 53,260.00; covered (surplus 10,860.00) |
| Yield −20% | available 49,480.00; covered (surplus 7,080.00); loan-cover 24.72 |
| Inputs +15% | pre-harvest shortfall 1,275.00 (flag `pre_harvest_cash_shortfall`); available 63,325.00; covered |
| News | DEMO Dhamrai flood matched via farm upazila → proposed `yield_shortfall` 20% |

### 4.5 D4 Selina Tailoring — expected `insufficient_information`
Weeks with records 2 (< 4) → forecast `insufficient_history`. Missing items (exact set): `debts_not_declared`, `household_withdrawal_not_declared`, `purpose_items_missing`, `gap_inputs_missing`, `terms_incomplete`, `forecast_insufficient_history`. `funding_gap` = null.

### 4.6 Land units
1 acre = 100 decimal; 150 decimal = 1.5 acres; 21,780 sq ft = 0.5 acre; 2 bigha at 33 decimal/bigha = 0.66 acre (factor owner-entered, SUG-14).

---

## 5. AI extraction validation (E2)

| ID | Test | Expected |
|---|---|---|
| AI-01 | Fake provider returns valid JSON | draft `pending`, no transaction created |
| AI-02 | Fake provider returns prose / invalid JSON | 422 `EXTRACTION_FAILED`, draft `failed`, manual path |
| AI-03 | Provider timeout | 503 `AI_UNAVAILABLE` |
| AI-04 | `ai_consent=false` | 422 |
| AI-05 | Confirm edited draft | transaction `photo_assisted` + `document_attached` with edited values |
| AI-06 | Confirm twice | 409 `DRAFT_ALREADY_RESOLVED` |
| AI-07 | 11th extraction in a day | 429 `AI_DAILY_LIMIT` |
| AI-08 | Purpose parse returns prices | prices discarded; items unconfirmed |
| AI-09 | `LLM_PROVIDER=none` full app run | every non-AI feature works (NFR-03) |
| E2 (measured) | 15–30 labelled receipts, real provider | report: N, amount exact-match %, date %, type %, % needing correction, failures — no pass threshold claimed |

## 6. Forecast tests
UT-02 + AT-16 + staleness: add an entry after a forecast → `GET /forecasts/latest` `is_stale=true`. Weekly-only recorder (one entry per week for 4 weeks) → `ok`. **E3 (measured, optional):** chronological holdout vs "last week repeated" on any consented history; label synthetic results as synthetic.

## 7. Lender consent tests
AT-23…AT-26 + SEC-08…SEC-13 + snapshot integrity: recompute SHA-256 from stored snapshot equals stored hash; modify snapshot in a test DB copy → mismatch detected by `verify_snapshot()` helper.

---

## 8. End-to-end scripts (run on deployed build in P7)

**E2E-1 Shop (D1-like, new account, not seed):** register → login → create shop profile → add 4 weeks of weekly entries (sales, purchases linked to 2 suppliers, expense) → summary correct → forecast ok → declare household + no loans → financing request with 1 item (supplier quote) → terms 6 weekly → assessment shows status + how-calculated → risk tab shows delay scenario → logout.

**E2E-2 Farm (D3 seed):** login as Rahim (DEMO) → switch to Rahim Rice Farm → season summary shows 19.70 / 19.78 → open financing → run assessment → ready; news tab shows DEMO flood → confirm → yield scenario covered (surplus 7,080.00).

**E2E-3 Lender:** login Nasrin (DEMO) → request access with D1 share code → (owner tab) Rahim approves 5 sections for 14 days → lender opens case, hash visible, supplier labels only → info request → owner sees it → lender records `refer` with reason → banner → owner revokes → lender gets "access revoked".

**E2E-4 Exceptions:** wrong password ×6 → lock; duplicate entry warning; D4 shows checklist; AI off → photo screen falls back to manual; news table empty → no errors.

---

## 9. Failure scenarios

| ID | Scenario | Expected |
|---|---|---|
| FS-01 | DB stopped | `/health` 503; UI shows connection error; no partial writes |
| FS-02 | LLM key invalid | `AI_UNAVAILABLE`; fallbacks |
| FS-03 | Upload dir unwritable | 503 on upload; manual entry works |
| FS-04 | Malformed news CSV row | row rejected with line number; others imported |
| FS-05 | Session expires during wizard | 401 → login → wizard resumes from saved step |
| FS-06 | Debt `next_due_date` in the past | past dates skipped; flag `existing_debt_dates_outdated` |

## 10. Security checks
SEC-01…SEC-20 (Security doc §7) + DB constraint script (DB doc §8) + checklist (Security doc §6) + `dist/` secret grep.

---

## 11. Traceability matrix (requirements → tests)

| Requirement(s) | Tests |
|---|---|
| FR-AUTH-01..03 | AT-01, AT-02, AT-07, UT-12 |
| FR-AUTH-04..06 | AT-03..AT-06, SEC-01, SEC-02, SEC-14 |
| FR-AUTH-07 | SEC-15 |
| FR-AUTH-08/09 | manual UI check P1; absence of reset endpoint (route list test) |
| FR-PROF-01..04 | AT-08, E2E-2 |
| FR-PROF-05 | SEC-03, SEC-04, SEC-05 |
| FR-PROF-06/07 | E2E-1, E2E-3 |
| FR-LED-01..07, 10 | AT-09..AT-13, UT-01 |
| FR-LED-08/09 | UT-01, E1 (§4.1) |
| FR-EXT-01..05 | AI-01..AI-07, SEC-17, SEC-20 |
| FR-DEBT-01..04 | UT-04, D2 (§4.3) |
| FR-SEA-01..08 | AT-14, AT-15, UT-07, UT-09, D3 (§4.4) |
| FR-SUP-01..06 | UT-08, D1 shares |
| FR-FC-01..06 | UT-02, AT-16, §6 |
| FR-FIN-01..09 | UT-03, UT-05, AT-17, AI-08 |
| FR-ASM-01..09 | UT-06, UT-07, AT-18..AT-20, D1–D4 |
| FR-SCN-01..04 | D1/D3 scenarios, AT-21 |
| FR-NEWS-01..06 | AT-21, AT-22, FS-04, D1/D3 news rows |
| FR-ADV-01..08 | UT-11, SEC-19, AI-09, E10 |
| FR-CON-01..09 | AT-23, AT-24, SEC-08..SEC-13, §7 |
| FR-LEN-01..07 | AT-25, AT-26, SEC-06, SEC-07, SEC-09, E2E-3 |
| FR-I18N-01..04 | CI parity, P7-T01/T02 review |
| FR-DEMO-01..03 | seed CLI test, E2E-2 |
| NFR-01..07 | P7 checklist, AI-09, SEC suite, UT golden, audit row tests |

## 12. Phase acceptance gates

| Phase | Must be green |
|---|---|
| P1 | AT-01..08, SEC-01/02/03/06/07/15/16, slice summary |
| P2 | UT-01, UT-04, UT-09, AT-09..AT-15, E1, SEC-04/05/18 |
| P3 | UT-02, UT-03, UT-05..UT-07, UT-10, AT-16..AT-20, D1–D4 base |
| P4 | UT-08, D1/D3 scenarios, AT-21, AT-22 |
| P5 | AT-23..AT-26, SEC-08..SEC-13, §7 |
| P6 | AI-01..AI-09, UT-11, SEC-17, SEC-19, SEC-20; E2/E10 reported |
| P7 | everything above on deployed build + E2E-1..4 + FS-01..06 + security checklist |
