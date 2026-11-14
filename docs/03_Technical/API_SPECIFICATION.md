# API SPECIFICATION — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-08 · **Version:** 1.0 (12 Nov 2026) · **Style:** REST/JSON
**Base URL:** `/api/v1` · **Framework:** FastAPI `[DEC-01]`
**OpenAPI:** FastAPI generates `/api/v1/openapi.json` and `/docs` from the Pydantic models. The Pydantic model names below are the contract; the generated OpenAPI file is exported to `docs/openapi.json` in CI (no hand-written YAML, to avoid drift).

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Auth | Cookie `bb_session` (HttpOnly). All endpoints except `POST /auth/register`, `POST /auth/login`, `GET /health` require it `[SUG-03]` |
| CSRF | Every non-GET request must send `X-BB-Client: web`; missing → 403 `CSRF_HEADER_MISSING` `[SUG-04]` |
| Content | `application/json; charset=utf-8` (uploads: `multipart/form-data`) |
| Money | **Strings** with 2 decimals, e.g. `"150000.00"` (no floats). Inputs accept numbers or strings; Bangla digits normalised server-side |
| Dates | `YYYY-MM-DD` (Asia/Dhaka business date); timestamps ISO 8601 UTC |
| IDs | UUID strings |
| Lists | `?limit=50&offset=0` (max 200); response `{"items":[…],"total":n}` |
| Language | Error `message_key` is translated by the client; `Accept-Language` not required |
| Ownership | Any `{pid}` not owned by the caller → **404** (never 403) to avoid leaking existence |
| Idempotency | `client_request_id` on transaction creation |

### Error envelope
```json
{ "error": { "code": "VALIDATION_ERROR", "message_key": "err.validation",
             "fields": { "amount": "entry.err.amount" }, "request_id": "a1b2c3" } }
```

---

## 2. Endpoint index

| # | Method | Path | Role | PRD |
|---|---|---|---|---|
| 1 | GET | `/health` | public | NFR |
| 2 | POST | `/auth/register` | public | FR-AUTH-01..03 |
| 3 | POST | `/auth/login` | public | FR-AUTH-04/05 |
| 4 | POST | `/auth/logout` | any | FR-AUTH-06 |
| 5 | GET | `/auth/me` | any | — |
| 6 | PATCH | `/auth/me` | any | FR-AUTH-08 |
| 7 | GET | `/profiles` | owner | FR-PROF-01 |
| 8 | POST | `/profiles` | owner | FR-PROF-01/02 |
| 9 | GET | `/profiles/{pid}` | owner | FR-PROF-04 |
| 10 | PATCH | `/profiles/{pid}` | owner | FR-PROF-06 |
| 11 | POST | `/profiles/{pid}/share-code/regenerate` | owner | FR-PROF-07 |
| 12 | GET | `/profiles/{pid}/transactions` | owner | FR-LED |
| 13 | POST | `/profiles/{pid}/transactions` | owner | FR-LED-01..07,10 |
| 14 | GET | `/profiles/{pid}/transactions/{tid}` | owner | FR-LED |
| 15 | POST | `/profiles/{pid}/transactions/{tid}/void` | owner | FR-LED-06 |
| 16 | GET | `/profiles/{pid}/summary` | owner | FR-LED-08/09 |
| 17 | POST | `/profiles/{pid}/documents` | owner | FR-EXT-01 |
| 18 | GET | `/profiles/{pid}/documents/{did}/content` | owner | FR-EXT |
| 19 | POST | `/profiles/{pid}/extraction-drafts` | owner | FR-EXT-02/04/05 |
| 20 | POST | `/profiles/{pid}/extraction-drafts/{xid}/confirm` | owner | FR-EXT-03 |
| 21 | POST | `/profiles/{pid}/extraction-drafts/{xid}/discard` | owner | FR-EXT |
| 22 | GET / POST | `/profiles/{pid}/suppliers` | owner | FR-SUP-01 |
| 23 | PATCH | `/profiles/{pid}/suppliers/{sid}` | owner | FR-SUP-01 |
| 24 | GET | `/profiles/{pid}/supplier-concentration` | owner | FR-SUP-03..06 |
| 25 | GET / POST | `/profiles/{pid}/debts` | owner | FR-DEBT-01 |
| 26 | PATCH | `/profiles/{pid}/debts/{did}` | owner | FR-DEBT-01 |
| 27 | POST | `/profiles/{pid}/debts/declare-none` | owner | FR-DEBT-02 |
| 28 | GET / POST | `/profiles/{pid}/seasons` | owner (farm) | FR-SEA-01..03 |
| 29 | GET / PATCH | `/profiles/{pid}/seasons/{sid}` | owner (farm) | FR-SEA |
| 30 | POST | `/profiles/{pid}/seasons/{sid}/cost-items` | owner (farm) | FR-SEA-04 |
| 31 | PATCH / DELETE | `/profiles/{pid}/seasons/{sid}/cost-items/{iid}` | owner (farm) | FR-SEA-04 |
| 32 | POST | `/profiles/{pid}/seasons/{sid}/harvest` | owner (farm) | FR-SEA-06 |
| 33 | GET | `/profiles/{pid}/seasons/{sid}/summary` | owner (farm) | FR-SEA-07 |
| 34 | POST | `/profiles/{pid}/forecasts` | owner (shop) | FR-FC-01..06 |
| 35 | GET | `/profiles/{pid}/forecasts/latest` | owner (shop) | FR-FC |
| 36 | GET / POST | `/profiles/{pid}/financing-requests` | owner | FR-FIN-01 |
| 37 | GET / PATCH | `/profiles/{pid}/financing-requests/{rid}` | owner | FR-FIN-04/06/07 |
| 38 | POST | `/profiles/{pid}/financing-requests/{rid}/items` | owner | FR-FIN-02/08 |
| 39 | PATCH / DELETE | `/profiles/{pid}/financing-requests/{rid}/items/{iid}` | owner | FR-FIN-02/03 |
| 40 | POST | `/profiles/{pid}/financing-requests/{rid}/parse-purpose` | owner | FR-FIN-03 |
| 41 | POST | `/profiles/{pid}/financing-requests/{rid}/assessments` | owner | FR-ASM-01..09 |
| 42 | GET | `/profiles/{pid}/financing-requests/{rid}/assessments/latest` | owner | FR-ASM |
| 43 | GET | `/profiles/{pid}/assessments/{aid}/scenarios` | owner | FR-SCN |
| 44 | POST | `/profiles/{pid}/scenarios/{scid}/confirm` | owner | FR-NEWS-04 |
| 45 | POST | `/profiles/{pid}/scenarios/{scid}/dismiss` | owner | FR-NEWS-04 |
| 46 | GET | `/profiles/{pid}/news-signals` | owner | FR-NEWS-02/03/06 |
| 47 | POST | `/profiles/{pid}/advisor/messages` | owner | FR-ADV |
| 48 | GET | `/profiles/{pid}/advisor/help-topics` | owner | FR-ADV-07 |
| 49 | GET | `/profiles/{pid}/consents` | owner | FR-CON-02 |
| 50 | POST | `/profiles/{pid}/consents/{cid}/approve` | owner | FR-CON-03/06 |
| 51 | POST | `/profiles/{pid}/consents/{cid}/decline` | owner | FR-CON-04 |
| 52 | POST | `/profiles/{pid}/consents/{cid}/revoke` | owner | FR-CON-04 |
| 53 | POST | `/profiles/{pid}/consents/{cid}/reshare` | owner | FR-CON-09 |
| 54 | GET | `/profiles/{pid}/consents/{cid}/activity` | owner | FR-CON-07, FR-LEN-05 |
| 55 | POST | `/lender/access-requests` | lender | FR-CON-01 |
| 56 | GET | `/lender/cases` | lender | FR-LEN-02 |
| 57 | GET | `/lender/cases/{cid}` | lender | FR-LEN-03, FR-CON-05/07 |
| 58 | POST | `/lender/cases/{cid}/events` | lender | FR-LEN-04..06 |

---

## 3. Error codes

| HTTP | Code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | malformed JSON |
| 401 | `AUTH_REQUIRED` / `SESSION_EXPIRED` / `INVALID_CREDENTIALS` | no cookie / expired or revoked / login failure |
| 403 | `FORBIDDEN_ROLE`, `CSRF_HEADER_MISSING`, `CONSENT_REQUIRED`, `CONSENT_REVOKED`, `CONSENT_EXPIRED`, `PROFILE_TYPE_MISMATCH` | role/consent/CSRF; shop-only or farm-only endpoint on wrong profile type |
| 404 | `NOT_FOUND` | not found **or not owned** |
| 409 | `PHONE_TAKEN`, `EMAIL_TAKEN`, `POSSIBLE_DUPLICATE`, `ASSESSMENT_STALE`, `CONSENT_STATE_INVALID`, `DRAFT_ALREADY_RESOLVED`, `CONFLICT` | conflicts; `CONFLICT` is the generic state conflict with a specific `message_key` (P2: `entry.err.already_voided`, `debt.err.active_exists`, `season.err.cost_item_in_use`) |
| 413 | `FILE_TOO_LARGE` | > 5 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | not JPEG/PNG (magic bytes) |
| 422 | `VALIDATION_ERROR` (with `fields`), `BIGHA_FACTOR_REQUIRED`, `EXTRACTION_FAILED` | invalid input / unreadable AI output |
| 429 | `RATE_LIMITED`, `ACCOUNT_LOCKED`, `AI_DAILY_LIMIT` | limits (SUG-05) |
| 503 | `AI_UNAVAILABLE`, `SERVICE_UNAVAILABLE` | provider/DB down |

---

## 4. Endpoint details

Template: **Purpose · Auth/Role · Request · Example · Success · Validation · Errors · DB operations**.

### 4.1 Health

**GET `/health`** — liveness. Public. `200 {"status":"ok","db":"ok","llm":"configured"|"disabled"}`; DB down → `503 {"status":"degraded","db":"down"}`. DB: `SELECT 1`.

### 4.2 Auth

**POST `/auth/register`** — create owner account. Public.
- Request `RegisterIn`: `full_name` (2–100), `phone` (SUG-24), `email`, `password` (SUG-25).
- Example: `{"full_name":"মোঃ রহিম উদ্দিন","phone":"01712345678","email":"rahim@example.com","password":"bazar-2026!"}`
- Success `201 UserOut`: `{"id":"…","full_name":"মোঃ রহিম উদ্দিন","phone":"+8801712345678","email":"rahim@example.com","role":"owner","preferred_language":"bn"}` (no auto-login; client calls login).
- Errors: 422 field errors; 409 `PHONE_TAKEN` / `EMAIL_TAKEN`; 429 `RATE_LIMITED`.
- DB: SELECT duplicates; INSERT `users`; INSERT `audit_logs(auth.register)`.

**POST `/auth/login`** — Public.
- Request `LoginIn`: `phone`, `password`. Example `{"phone":"01712345678","password":"bazar-2026!"}`
- Success `200 UserOut` + `Set-Cookie: bb_session=…; HttpOnly; SameSite=Lax; Path=/; Secure(prod)`.
- Errors: 401 `INVALID_CREDENTIALS` (same for unknown phone); 429 `ACCOUNT_LOCKED` (`retry_after_seconds`); 429 `RATE_LIMITED` (per IP).
- DB: SELECT user; UPDATE `failed_login_count`/`locked_until`/`last_login_at`; INSERT `user_sessions`; INSERT `audit_logs`.

**POST `/auth/logout`** — revoke current session. `204`. DB: UPDATE `user_sessions.revoked_at`; audit.

**GET `/auth/me`** — `200 MeOut`: `UserOut` + `lender` block for officers `{"organization":{"id","name","is_demo"},"designation"}`.

**PATCH `/auth/me`** — `{"preferred_language":"en"}` → `200 UserOut`. Only `preferred_language` and `full_name` editable.

### 4.3 Profiles (owner)

**GET `/profiles`** → `200 {"items":[ProfileOut]}`; `ProfileOut`: `id, activity_type, display_name, business_category, district, upazila, market_area, household_withdrawal_monthly, household_declared, no_debt_declared, share_code, is_demo, financing_fields_complete`.

**POST `/profiles`** — Request `ProfileCreate`: `display_name` (2–80), `activity_type` (`shop|crop_farm`), optional progressive fields. Example `{"display_name":"Rahim Store","activity_type":"shop"}` → `201 ProfileOut` (server generates `share_code`). DB: INSERT `business_profiles`.

**GET `/profiles/{pid}`** → `200 ProfileOut`; 404 if not owned.

**PATCH `/profiles/{pid}`** — any of: `display_name, business_category, district, upazila, market_area, household_withdrawal_monthly` (≥ 0; setting it records `household_declared_at`). → `200`. DB: UPDATE; bump `data_version`.

**POST `/profiles/{pid}/share-code/regenerate`** → `200 {"share_code":"R7PQ2M9XAB"}`. Existing consents unaffected. DB: UPDATE.

### 4.4 Transactions (owner)

**GET `/profiles/{pid}/transactions`** — filters `from`, `to`, `txn_type` (repeatable, e.g. `?txn_type=loan_received&txn_type=loan_principal_repayment`), `status`, `season_id`, `supplier_id`. → `{"items":[TransactionOut],"total":n}` sorted by `value_date desc, created_at desc`.
- Implementation notes (P2): a `season_cost_item_id` implies its season (must match `season_id` if both are sent) and is allowed only on `purchase_cash|purchase_credit|payable_payment|operating_expense`; `POSSIBLE_DUPLICATE.existing` also carries `txn_type`; a confirmed duplicate is stored with `duplicate_confirmed=true`.

**POST `/profiles/{pid}/transactions`**
- Request `TransactionCreate`: `txn_type` (12 values), `amount`, `value_date`, optional `settlement_date`, `category`, `note` (≤ 300), `supplier_id` (purchase types only), `debt_facility_id` (loan types only), `season_id`, `season_cost_item_id` (farm profiles only), `client_request_id` (UUID), `confirm_duplicate` (bool, default false).
- Example: `{"txn_type":"purchase_cash","amount":"65000","value_date":"2026-11-10","supplier_id":"…","client_request_id":"5f0c…"}`
- Success `201 TransactionOut`: `{"id","txn_type","amount":"65000.00","value_date","supplier":{"id","display_name"},"entry_method":"manual","evidence_state":"declared","status":"confirmed","created_at"}`. Same `client_request_id` again → `200` with the existing row.
- Validation: amount > 0 and ≤ 99,999,999,999.99; `value_date ≤ today+1`; links must belong to `pid` (else 404); type/link compatibility (else 422); season fields only for `crop_farm`.
- Errors: 409 `POSSIBLE_DUPLICATE` with `{"existing":{"id","amount","value_date"}}` (SUG-28); 422.
- DB: SELECT duplicate candidates; INSERT `transactions`; bump `data_version`.

**GET `/profiles/{pid}/transactions/{tid}`** → `TransactionOut` (+ `document_id` if any).

**POST `/profiles/{pid}/transactions/{tid}/void`** — `{"reason":"ভুল পরিমাণ লিখেছিলাম"}` (3–200 chars) → `200 TransactionOut(status="voided")`. Already voided → 409. DB: UPDATE status, `voided_at`, `void_reason`; bump `data_version`.

**GET `/profiles/{pid}/summary?from=YYYY-MM-DD&to=YYYY-MM-DD`** (default: current month)
- Success `200 SummaryOut`: `{"from","to","has_data":true,"sales_recorded","cash_sales","credit_sales","operating_cash_in","operating_cash_out","net_operating_cash","receivables_outstanding","payables_outstanding","financing_received","principal_repaid","interest_fees_paid","owner_withdrawals","owner_contributions","cash_net_change","evidence_mix":{"declared_pct":"100.0","document_attached_pct":"0.0"},"record_coverage":{"weeks_with_records":8,"window_weeks":8}}` (outstanding receivables/payables are all-time up to `to`).
- DB: aggregate SELECT over confirmed rows (engine.accounting mapping).

### 4.5 Documents and extraction (owner)

**POST `/profiles/{pid}/documents`** (multipart: `file`, `purpose`) → `201 {"id","mime_type","size_bytes","sha256","duplicate_of":null|"<document_id>"}`. Validation: magic bytes JPEG/PNG, ≤ 5 MB, re-encode with Pillow (EXIF removed), max 1600 px stored. Errors 413/415. DB: INSERT `documents`; file write to `UPLOAD_DIR`.

**GET `/profiles/{pid}/documents/{did}/content`** → image bytes with `Content-Disposition: inline`, `Cache-Control: private, no-store`. Owner only.

**POST `/profiles/{pid}/extraction-drafts`** — `{"document_id":"…","ai_consent":true}`; `ai_consent` must be true (else 422).
- Success `201 ExtractionDraftOut`: `{"id","status":"pending","proposed":{"txn_type":{"value":"purchase_cash","confidence":0.62},"amount":{"value":"12450.00","confidence":0.93},"value_date":{"value":"2026-11-10","confidence":0.55},"supplier_name":{"value":"Supplier A","confidence":0.7},"note":{"value":"চাল ২ বস্তা","confidence":0.6}},"matched_supplier_id":null}`
- Errors: 503 `AI_UNAVAILABLE`; 429 `AI_DAILY_LIMIT`; 422 `EXTRACTION_FAILED` (draft stored with `status=failed`).
- DB: INSERT `extraction_drafts`; INSERT `ai_interactions`.

**POST `/profiles/{pid}/extraction-drafts/{xid}/confirm`** — body = `TransactionCreate` (owner-edited values) → `201 TransactionOut` with `entry_method=photo_assisted`, `evidence_state=document_attached`, `document_id` set. Draft not pending → 409 `DRAFT_ALREADY_RESOLVED`. DB: INSERT transaction; UPDATE draft `confirmed`.

**POST `/profiles/{pid}/extraction-drafts/{xid}/discard`** → `204`. DB: UPDATE draft `discarded`.

### 4.6 Suppliers (owner)

**GET / POST `/profiles/{pid}/suppliers`** — `SupplierCreate`: `display_name`, `goods_supplied`, `district`, `upazila`, `declared_purchase_share_pct` (0–100, optional). Example `{"display_name":"Supplier A (DEMO wholesaler)","goods_supplied":"rice, oil","district":"Gazipur","upazila":"Kaliakair"}` → `201 SupplierOut`. DB: INSERT; bump `data_version`.

**PATCH `/profiles/{pid}/suppliers/{sid}`** — same fields + `is_active`.

**GET `/profiles/{pid}/supplier-concentration`**
- Success: `{"window_days":56,"basis":"linked_purchases","total_purchases":"752000.00","suppliers":[{"supplier_id","display_name":"Supplier A (DEMO wholesaler)","amount":"488800.00","share_pct":"65.0"},…],"top_share_pct":"65.0","high_dependency":true,"threshold_pct":"50.0","note_key":null}`; no suppliers → `basis:"none"`, `note_key:"supplier.add_prompt"`; sparse → `note_key:"supplier.sparse"`.

### 4.7 Debts (owner)

**GET / POST `/profiles/{pid}/debts`** — `DebtCreate`: `lender_type`, `lender_label`, `original_principal`, `outstanding_balance`, `outstanding_as_of`, `installment_amount` (required unless `single`), `installment_frequency`, `next_due_date`, `is_overdue`, `overdue_amount`, `season_id` (farm), `interest_fee_note`.
- Example: `{"lender_type":"mfi","lender_label":"DEMO NGO weekly loan","original_principal":"100000","outstanding_balance":"60000","outstanding_as_of":"2026-12-01","installment_amount":"2500","installment_frequency":"weekly","next_due_date":"2026-12-04"}`
- Success `201 DebtOut` incl. `next_installments` (first 3 dates within horizon) and `evidence_state`. Creating a debt clears nothing; `no_debt_declared` becomes false automatically. DB: INSERT; bump `data_version`.

**PATCH `/profiles/{pid}/debts/{did}`** — update fields or `status:"closed"`.
- Implementation notes (P2): GET list returns `{"items","total","no_debt_declared"}`; `outstanding_as_of` defaults to today; `DebtOut.dates_outdated` is true when an active debt's `next_due_date` is in the past (schedule skips past dates without using up the outstanding balance — the cautious reading; assessment flag `existing_debt_dates_outdated`); creating a debt clears `no_debt_declared_at`.

**POST `/profiles/{pid}/debts/declare-none`** → `200 {"no_debt_declared":true}`; 409 if active debts exist. DB: UPDATE `no_debt_declared_at`.

### 4.8 Seasons (owner, `crop_farm` only — else 403 `PROFILE_TYPE_MISMATCH`)

**POST `/profiles/{pid}/seasons`** — `SeasonCreate`: `crop_name`, `variety?`, `season_name`, `season_label?`, `area_value`, `area_unit`, `decimals_per_bigha?`, `sowing_date`, `expected_harvest_date`, `expected_output_low/expected/high`, `expected_price_low/expected/high`.
- Example: `{"crop_name":"Rice","season_name":"boro","season_label":"2026-27","area_value":"150","area_unit":"decimal","sowing_date":"2027-01-10","expected_harvest_date":"2027-05-05","expected_output_low":"2700","expected_output_expected":"3300","expected_output_high":"3750","expected_price_low":"28","expected_price_expected":"32","expected_price_high":"35"}`
- Success `201 SeasonOut` with `area_acres:"1.5000"`, `income_range:{"low":"75600.00","expected":"105600.00","high":"131250.00"}`.
- Errors: 422 `BIGHA_FACTOR_REQUIRED`; 422 ordering (low ≤ expected ≤ high; sowing < harvest).
- DB: INSERT `farming_seasons`; bump `data_version`.

**GET / PATCH `/profiles/{pid}/seasons/{sid}`**; **GET `/profiles/{pid}/seasons`** list. (P2: GET one also returns `cost_items` with each item's `paid_total`; PATCH `status` accepts `planned|growing|closed` — `harvested` only via `/harvest`.)

**POST `/profiles/{pid}/seasons/{sid}/cost-items`** — `{"category":"fertilizer","item_name":"Fertilizer","quantity":"1","unit":"lot","unit_cost":"18000","price_source_type":"owner_estimate"}` → `201 CostItemOut` (`total_cost`). PATCH/DELETE `…/{iid}` (DELETE → 409 if referenced by a transaction or request item).

**POST `/profiles/{pid}/seasons/{sid}/harvest`** — `{"actual_harvest_date":"2027-05-06","actual_output":"3100"}` → `200 SeasonOut(status="harvested")`.

**GET `/profiles/{pid}/seasons/{sid}/summary`** → `{"season":SeasonOut,"planned_cost_total":"65000.00","paid_cost_total":"4500.00","actual_sales_total":"0.00","income_range":{…},"break_even_price_per_kg":"19.70","loan_cover_price_per_kg":"19.78"|null,"loan_cover_basis":{"financing_request_id","repayment_total":"42400.00"}|null,"labels":["owner_estimates"]}`.

### 4.9 Forecast (owner, `shop` only)

**POST `/profiles/{pid}/forecasts`** — body optional `{"as_of_date":"2026-12-01"}` (defaults today; admin/test may set).
- Success `201 ForecastOut` (ok):
```json
{"id":"…","status":"ok","as_of_date":"2026-12-01","method_version":"weekly-baseline-v1",
 "weeks_with_records":8,"window_weeks":8,"min_weeks_required":4,
 "weekly":{"net":{"low":"25000.00","expected":"32312.50","high":"41000.00"},
           "collections_expected":"144312.50","payments_expected":"112000.00","purchases_expected":"94000.00"},
 "horizons":{"7":{"low":"25000.00","expected":"32312.50","known_debt_service":"0.00"},
             "30":{"low":"107142.86","expected":"138482.14","known_debt_service":"0.00"},
             "60":{"low":"214285.71","expected":"276964.29","known_debt_service":"0.00"},
             "90":{"low":"321428.57","expected":"415446.43","known_debt_service":"0.00"}},
 "disclaimer_key":"forecast.estimate"}
```
- Insufficient: `{"status":"insufficient_history","weeks_with_records":2,"min_weeks_required":4,"weekly":null,"horizons":{}}`
- DB: SELECT 8 weekly aggregates; SELECT debts; INSERT `forecast_runs`.

**GET `/profiles/{pid}/forecasts/latest`** → latest `ForecastOut` + `"is_stale": bool` (data_version changed).

### 4.10 Financing requests (owner)

**POST `/profiles/{pid}/financing-requests`** — `{"requested_amount":"200000","purpose_text":"ঈদের আগে চাল-ডাল-তেল কিনবো","purpose_category":"inventory","desired_start_date":"2026-12-01","season_id":null}` → `201 FinancingRequestOut`. DB: INSERT.

**PATCH `/profiles/{pid}/financing-requests/{rid}`** — any of: amount/purpose fields, `associated_expenses`, `liquidity_buffer`, `buffer_justification`, `cash_safely_available`, `committed_financing`, `current_cash_balance`, `minimum_cash_reserve`, `schedule_type`, `installment_count`, `installment_frequency`, `first_due_date`, `interest_fees_total`, `interest_fees_unknown`, `over_request_explanation`.
- Example (step 5): `{"schedule_type":"equal_installments","installment_count":12,"installment_frequency":"weekly","first_due_date":"2026-12-08","interest_fees_total":"16000","minimum_cash_reserve":"10000","current_cash_balance":"45000"}`
- Success `200 FinancingRequestOut` incl. live `preview`: `{"items_total":"150000.00","funding_gap":"150000.00","request_minus_gap":"50000.00","installments":[{"due_date":"2026-12-08","amount":"18000.00"},…]}`.
- Validation: `single_payment` ⇒ count 1; `equal_installments` ⇒ frequency; `first_due_date ≥ today`.
- DB: UPDATE; bump `data_version`.

**POST `/profiles/{pid}/financing-requests/{rid}/items`** — `{"item_name":"Mixed stock units","quantity":"100","unit":"unit","unit_price":"1500","price_source_type":"supplier_quote","price_date":"2026-11-29","price_source_note":"Quotation from Supplier A"}` or `{"copy_from_season_cost_item_id":"…"}` → `201 ItemOut` (`line_total`). DB: INSERT; bump.

**PATCH / DELETE `…/items/{iid}`** — edit fields; `{"confirmed":true}` confirms an AI suggestion.

**POST `/profiles/{pid}/financing-requests/{rid}/parse-purpose`** (AI) — body `{}` (uses stored `purpose_text`).
- Success `200 {"items":[{"id","item_name":"চাল","quantity":"20","unit":"বস্তা","unit_price":null,"ai_proposed":true,"confirmed":false}],"note_key":"fin.ai_items_confirm"}` — prices are **never** filled by AI (owner supplies price + source).
- Errors 503/429 → client keeps manual item entry.
- DB: INSERT items (`ai_proposed=true, confirmed=false`, `unit_price=0` placeholder hidden until edited — unconfirmed rows never count); INSERT `ai_interactions`.

### 4.11 Assessments and scenarios (owner)

**POST `/profiles/{pid}/financing-requests/{rid}/assessments`** — body optional `{"as_of_date":"2026-12-01"}`.
- Success `201 AssessmentOut` (D1 example, as_of 2026-12-01):
```json
{"id":"…","status":"ready_for_lender_review","as_of_date":"2026-12-01","engine_version":"assess-v1",
 "funding_gap":"150000.00","purpose_items_total":"150000.00","request_minus_gap":"50000.00",
 "missing_items":[],
 "flags":["request_exceeds_gap","high_supplier_dependency","scenario_shortfall"],
 "base_result":{"kind":"shop_due_dates","start_balance":"15000.00","reserve":"10000.00",
   "min_balance_after_payment":"21626.22","first_shortfall":null,"beyond_horizon":[],
   "checks":[{"date":"2026-12-08","paid":"18000.00","new_installment":"18000.00","balance_after":"21626.22","shortfall_vs_reserve":"0.00"}]},
 "scenarios":[{"id":"…","scenario_type":"supplier_delay","origin":"auto","status":"computed",
   "parameters":{"days":7,"share":"0.65","start":"2026-12-01"},
   "result":{"any_shortfall":true,"first_shortfall":{"date":"2026-12-08","shortfall_vs_reserve":"9376.90"}},
   "assumption_key":"scn.delay"}],
 "news_signals":[{"news_event_id":"…","headline":"DEMO: Road blockade…","is_demo":true,"match_reasons":["supplier_location"],"proposed_scenario_id":"…"}],
 "explanation":{"formulas":["funding_gap = max(0, items + associated + buffer − cash_available − committed)"],
   "inputs":[{"name":"household_withdrawal_monthly","value":"15000.00","source":"declared"}],
   "parameters":{"forecast_window_weeks":8,"min_weeks":4,"horizon_days":90}},
 "is_stale":false,"disclaimer_key":"asm.not_approval"}
```
- Insufficient example (D4): `{"status":"insufficient_information","missing_items":["debts_not_declared","household_withdrawal_not_declared","purpose_items_missing","gap_inputs_missing","terms_incomplete","forecast_insufficient_history"],"funding_gap":null,…}`
- DB: SELECT inputs; INSERT `forecast_runs` (shop, if latest stale); INSERT `financial_assessments`; INSERT `risk_scenarios` (auto computed + news proposed).
- **Forbidden content test:** payload must never contain the words "approved", "eligible", "credit score", "probability of default" (FR-ASM-07).

**GET `…/{rid}/assessments/latest`** → latest `AssessmentOut` with `is_stale`.

- Implementation notes (P3): `as_of_date` in POST bodies is honoured only when `APP_ENV ≠ production`. Also `GET /profiles/{pid}/assessments/{aid}` (read one, used by SCR-O12). `explanation.formulas` items are `{key, expr, values}` (i18n label key + formula + the same formula with numbers); `explanation.proposal` carries `requested_amount`, the installment rows and `label:"owner_proposal_not_lender_offer"`. `base_result.checks[]` also has `existing_paid`. `ForecastOut` adds `weeks[]` (8 blocks, `net` null = missing week). `FinancingOut` adds `latest_assessment {id,status,is_stale}` and `preview.gap_inputs_complete` / `repayment_total`. A declared overdue amount is an outflow on as_of (rest of the schedule uses outstanding − overdue). An explicit `interest_fees_unknown:true` wins over an amount in the same PATCH. 409 `CONFLICT` / `fin.err.item_already_copied` when copying the same season cost item twice.

**GET `/profiles/{pid}/assessments/{aid}/scenarios`** → `{"items":[ScenarioOut]}`.

**POST `/profiles/{pid}/scenarios/{scid}/confirm`** — only `origin=news, status=proposed` → computes → `200 ScenarioOut(status="computed")`. Others → 409. **POST `…/dismiss`** → `status="dismissed"`. Neither changes the assessment status (DEC-30). DB: UPDATE `risk_scenarios`.

### 4.12 News signals (owner)

**GET `/profiles/{pid}/news-signals`** → `{"items":[{"id","headline","headline_lang","summary","source_name","source_url","published_date","event_date","event_type","districts","upazilas","is_demo":true,"corroboration":"single_source","match_reasons":["supplier_location"],"matched_supplier":"Supplier A (DEMO wholesaler)"}]}`; empty list allowed. DB: SELECT with matching rules (Architecture §5.6).

- Implementation notes (P4): match reasons are `location | supplier_location | sector | commodity` with the relevance rule of SUG-37; window = published within 30 days before as_of (not after it) or event date ≥ as_of. Items also carry `source_count`, `news_event_id`, `proposed_scenario_id` and `scenario_status` (the same row shape is used in `AssessmentOut.news_signals`, matched at the assessment's `as_of_date`). `ScenarioOut` adds `supplier_name` (owner view only) and uses `assumption_key` `scn.input_cost` for a farm's input-price case. Shop scenario `result` = `{kind, any_shortfall, covered, checks_count, min_balance_after_payment, first_shortfall{date,balance_after,shortfall_vs_reserve}}`; crop = the crop-check fields. Parameters: delay `{days, share, start, basis}`, shop price `{pct, share, basis}`, crop `{pct}`. Confirm/dismiss on a non-proposed scenario → 409 `CONFLICT` (`scn.err.not_proposed`); confirm after inputs changed → 409 `ASSESSMENT_STALE` (SUG-39). `/supplier-concentration` adds `window_start`, `window_end`, `linked_purchase_count`; `amount`/`total_purchases` are null when owner-reported.

### 4.13 Advisor (owner)

**POST `/profiles/{pid}/advisor/messages`** — `{"message":"আগামী সপ্তাহে আমার কত কিস্তি?","history":[{"role":"user","text":"…"},{"role":"assistant","text":"…"}]}` (history ≤ 6 turns, client-held; server does not store chat text).
- Success `200 {"reply":"আগামী ৭ দিনে আপনার জানা কিস্তি Tk 2,500 (DEMO NGO weekly loan)।","language":"bn","tools_used":["get_upcoming_installments"],"grounded":true,"mode":"llm"}`; fallback `mode:"template"`.
- Errors: 429 `AI_DAILY_LIMIT` (body includes `help_topics`); 503 `AI_UNAVAILABLE` (body includes `help_topics`).
- DB: read-only via tools; INSERT `ai_interactions`.

**GET `/profiles/{pid}/advisor/help-topics`** → `{"items":[{"key":"what_is_funding_gap","title_bn","title_en","body_bn","body_en"}]}` plus deterministic answers (e.g. `next_week_installments`) computed by services.

### 4.14 Consent (owner)

**GET `/profiles/{pid}/consents`** → `{"items":[{"id","status","lender_organization":{"name","is_demo"},"requested_by":"Nasrin Officer (DEMO)","requested_sections":[…],"request_message","approved_sections","valid_until","is_expired":false,"latest_report":{"version":1,"snapshot_sha256"},"read_count":2,"open_info_requests":1}]}`.

**POST `/profiles/{pid}/consents/{cid}/approve`** — `{"approved_sections":["profile_summary","money_summary","forecast","financing_request","obligations","supplier_risk","news_signals"],"financing_request_id":"…","valid_days":14}`
- Rules: status must be `requested`; `approved_sections ⊆ allowed keys` and must include `profile_summary`, `financing_request`; `valid_days ∈ {7,14,30}`; latest assessment for the request must exist and not be stale (else 409 `ASSESSMENT_STALE`); `season_summary` only for farm; `forecast` only for shop.
- Success `200 ConsentOut` + `{"report":{"version":1,"snapshot_sha256":"9f2c…"}}`.
- DB: build snapshot (snapshot_service) → INSERT `shared_reports`; UPDATE `consents` (approved, sections, assessment_id, valid_until = now + days); INSERT `lender_reviews` (under_review); audit `consent.approve`.

**POST `…/{cid}/decline`** → `200` (from `requested` only). **POST `…/{cid}/revoke`** → `200` (from `approved`; immediate). **POST `…/{cid}/reshare`** → new snapshot version from the latest non-stale assessment (`200 {"version":2,…}`). All audited.

**GET `…/{cid}/activity`** → `{"reads":[{"at","organization"}],"info_requests":[{"at","body"}],"decision":null|{"decision","reason","at"}}` (lender notes excluded).

### 4.15 Lender

**POST `/lender/access-requests`** — role `lender_officer`.
- Request `{"share_code":"7KQ2M9XA4P","requested_sections":["profile_summary","financing_request","obligations","supplier_risk"],"message":"Please share your financing case for review."}` (dashes/spaces in code ignored).
- Success **always** `202 {"message_key":"lender.request_sent_if_valid"}`. If the code is valid and no open request from this org exists → INSERT `consents(requested)`. Rate limit 20/hour/officer (SUG-05 family).
- DB: SELECT profile by share_code; INSERT consent; audit `consent.request` (outcome success or `denied` for invalid code — not revealed to caller).

**GET `/lender/cases?status=active|pending|closed`** → `{"items":[{"consent_id","applicant":{"display_name":"Rahim Store","activity_type":"shop","is_demo":true}|null,"status","valid_until","assessment_status","requested_amount","review_status","last_read_at"}]}`. For `requested` (pending) cases, applicant fields are **null** until the owner approves.

**GET `/lender/cases/{cid}`** → `200 CaseFileOut`: `{"consent":{"id","approved_sections","valid_until","version","snapshot_sha256"},"snapshot":{…approved sections only…},"review":{"status","decision","events":[…]},"cib_notice_key":"debt.cib"}`. Snapshot supplier names replaced with `Supplier 1/2/3`.
- Errors: other org → 404; `requested`/`declined` → 403 `CONSENT_REQUIRED`; revoked → 403 `CONSENT_REVOKED`; expired → 403 `CONSENT_EXPIRED`.
- DB: SELECT; INSERT `audit_logs(consent.read)` on success, `consent.read_denied` on failure.

**POST `/lender/cases/{cid}/events`**
- `{"event_type":"status_change","status":"under_review"}` | `{"event_type":"note","body":"Check quotation date"}` | `{"event_type":"info_request","body":"অনুগ্রহ করে সরবরাহকারীর দরপত্র দিন"}` | `{"event_type":"decision","decision":"refer","body":"Needs supplier quotation verification at branch"}`.
- Rules: consent must be readable (same as GET); decision requires `body` ≥ 5 chars; after decision, further decisions allowed (latest wins, all logged).
- Success `201 {"review":{"status","decision"},"event":{…}}` + `"banner_key":"lender.decision_banner"` for decisions.
- DB: INSERT `lender_review_events`; UPDATE `lender_reviews`; audit `lender.event` / `lender.decision`.

---

## 5. Snapshot JSON structure (shared report)

```json
{
  "schema": "bb-report-v1",
  "generated_at": "2026-12-01T09:30:00Z",
  "is_demo": true,
  "sections": {
    "profile_summary": {"display_name":"Rahim Store","activity_type":"shop","district":"Dhaka","upazila":"Savar","business_category":"grocery"},
    "money_summary": {"period":{"from":"2026-10-06","to":"2026-11-30"},"net_operating_cash":"258500.00","evidence_mix":{"declared_pct":"100.0","document_attached_pct":"0.0"},"record_coverage":{"weeks_with_records":8,"window_weeks":8}},
    "forecast": {"status":"ok","weekly_net":{"low":"25000.00","expected":"32312.50","high":"41000.00"},"disclaimer":"estimate"},
    "financing_request": {"requested_amount":"200000.00","purpose_text":"…","items":[…],"funding_gap":"150000.00","request_minus_gap":"50000.00","over_request_explanation":null,"proposal":{"schedule_type":"equal_installments","installment_count":12,"frequency":"weekly","total_interest_fees":"16000.00","label":"owner_proposal_not_lender_offer"},"assessment":{"status":"ready_for_lender_review","flags":[…],"base_result":{…},"scenarios":[…]}},
    "obligations": {"declared":[…],"no_debt_declared":true,"cib_notice":"Official credit checks are done by the lender outside Bonik Bondhu"},
    "supplier_risk": {"basis":"linked_purchases","suppliers":[{"label":"Supplier 1","share_pct":"65.0"},{"label":"Supplier 2","share_pct":"25.0"},{"label":"Supplier 3","share_pct":"10.0"}],"high_dependency":true},
    "news_signals": [{"headline":"DEMO: …","source_name":"DEMO (fictional)","published_date":"2026-11-30","corroboration":"single_source","is_demo":true,"match_reasons":["supplier_location"]}]
  }
}
```
Only keys in `approved_sections` are present. `snapshot_sha256 = sha256(json.dumps(snapshot, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8"))`.
