-- =============================================================================
-- Bonik Bondhu Hackathon MVP — PostgreSQL schema (v1, migration 0001)
-- Document: 03_Technical/DATABASE_SCHEMA.md (BB-DOC-07)
-- Target: PostgreSQL 13+ (tested on PostgreSQL 16). gen_random_uuid() is core in 13+.
-- Conventions:
--   * UUID primary keys (SUG-26), money NUMERIC(14,2) in BDT (SUG-06)
--   * enums as TEXT + CHECK (easy to migrate) [DERIVED]
--   * every owner-data table carries profile_id; child FKs are composite
--     (profile_id, id) so a row can never point at another profile's row
--     [DERIVED from MP §5, §12 ownership boundaries]
--   * is_demo flags separate synthetic demo data (MP §18)
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Accounts and sessions
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name           TEXT        NOT NULL CHECK (char_length(full_name) BETWEEN 2 AND 100),
    phone_e164          TEXT        NOT NULL UNIQUE CHECK (phone_e164 ~ '^\+8801[3-9][0-9]{8}$'),
    email               TEXT        NOT NULL CHECK (email = lower(email) AND char_length(email) <= 254),
    password_hash       TEXT        NOT NULL,
    role                TEXT        NOT NULL DEFAULT 'owner'
                                    CHECK (role IN ('owner', 'lender_officer', 'admin')),
    preferred_language  TEXT        NOT NULL DEFAULT 'bn' CHECK (preferred_language IN ('bn', 'en')),
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    is_demo             BOOLEAN     NOT NULL DEFAULT FALSE,
    failed_login_count  INTEGER     NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until        TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_users_email ON users (email);

CREATE TABLE user_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_sha256    CHAR(64)    NOT NULL UNIQUE,          -- raw token never stored (SUG-03)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
CREATE INDEX ix_sessions_user ON user_sessions (user_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- 2. Lender organisations and officers (manually provisioned, DEC-24)
-- ---------------------------------------------------------------------------
CREATE TABLE lender_organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL UNIQUE CHECK (char_length(name) BETWEEN 2 AND 120),
    org_type    TEXT        NOT NULL CHECK (org_type IN ('bank', 'mfi', 'ngo', 'other')),
    is_demo     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE lender_officers (
    user_id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    organization_id  UUID        NOT NULL REFERENCES lender_organizations(id),
    designation      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_officers_org ON lender_officers (organization_id);

-- ---------------------------------------------------------------------------
-- 3. Business profiles (shop or crop farm), many per owner (MP §5, DEC-04)
-- ---------------------------------------------------------------------------
CREATE TABLE business_profiles (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id                 UUID        NOT NULL REFERENCES users(id),
    activity_type                 TEXT        NOT NULL CHECK (activity_type IN ('shop', 'crop_farm')),
    display_name                  TEXT        NOT NULL CHECK (char_length(display_name) BETWEEN 2 AND 80),
    business_category             TEXT,                 -- e.g. grocery, retail, trader, service, crop
    district                      TEXT,
    upazila                       TEXT,
    market_area                   TEXT,
    household_withdrawal_monthly  NUMERIC(14,2) CHECK (household_withdrawal_monthly >= 0),
    household_declared_at         TIMESTAMPTZ,          -- set when owner declares (0 allowed) DEC-37
    no_debt_declared_at           TIMESTAMPTZ,          -- "I have no current loans" FR-DEBT-02
    share_code                    TEXT        NOT NULL UNIQUE CHECK (share_code ~ '^[A-HJ-NP-Z2-9]{10}$'),
    data_version                  BIGINT      NOT NULL DEFAULT 1,   -- bumped on any input change (FR-ASM-09)
    is_demo                       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at                   TIMESTAMPTZ
);
CREATE INDEX ix_profiles_owner ON business_profiles (owner_user_id) WHERE archived_at IS NULL;

-- ---------------------------------------------------------------------------
-- 4. Suppliers (L2 Stage 1; suppliers only, DEC-26)
-- ---------------------------------------------------------------------------
CREATE TABLE suppliers (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id                   UUID        NOT NULL REFERENCES business_profiles(id),
    display_name                 TEXT        NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 80),
    goods_supplied               TEXT,
    district                     TEXT,
    upazila                      TEXT,
    declared_purchase_share_pct  NUMERIC(5,2) CHECK (declared_purchase_share_pct BETWEEN 0 AND 100),
    is_active                    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id)
);

-- ---------------------------------------------------------------------------
-- 5. Crop seasons and planned cost items (S1 §5; DEC-05, DEC-27)
-- ---------------------------------------------------------------------------
CREATE TABLE farming_seasons (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id               UUID          NOT NULL REFERENCES business_profiles(id),
    crop_name                TEXT          NOT NULL,
    variety                  TEXT,
    season_name              TEXT          NOT NULL CHECK (season_name IN ('aman','boro','aus','winter_vegetables','other')),
    season_label             TEXT,                         -- e.g. '2026-27'
    area_value               NUMERIC(12,4) NOT NULL CHECK (area_value > 0),
    area_unit                TEXT          NOT NULL CHECK (area_unit IN ('acre','decimal','sq_ft','bigha')),
    decimals_per_bigha       NUMERIC(8,3)  CHECK (decimals_per_bigha > 0),
    area_acres               NUMERIC(12,4) NOT NULL CHECK (area_acres > 0),  -- computed by service (SUG-14)
    sowing_date              DATE          NOT NULL,
    expected_harvest_date    DATE          NOT NULL,
    output_unit              TEXT          NOT NULL DEFAULT 'kg' CHECK (output_unit = 'kg'),
    expected_output_low      NUMERIC(14,2) CHECK (expected_output_low > 0),
    expected_output_expected NUMERIC(14,2) CHECK (expected_output_expected > 0),
    expected_output_high     NUMERIC(14,2) CHECK (expected_output_high > 0),
    expected_price_low       NUMERIC(14,2) CHECK (expected_price_low > 0),
    expected_price_expected  NUMERIC(14,2) CHECK (expected_price_expected > 0),
    expected_price_high      NUMERIC(14,2) CHECK (expected_price_high > 0),
    status                   TEXT          NOT NULL DEFAULT 'planned'
                                           CHECK (status IN ('planned','growing','harvested','closed')),
    actual_harvest_date      DATE,
    actual_output            NUMERIC(14,2) CHECK (actual_output >= 0),
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    CHECK (expected_harvest_date > sowing_date),
    CHECK (area_unit <> 'bigha' OR decimals_per_bigha IS NOT NULL),
    CHECK (expected_output_low <= expected_output_expected AND expected_output_expected <= expected_output_high),
    CHECK (expected_price_low <= expected_price_expected AND expected_price_expected <= expected_price_high),
    CHECK (status <> 'harvested' OR (actual_harvest_date IS NOT NULL AND actual_output IS NOT NULL))
);
CREATE INDEX ix_seasons_profile ON farming_seasons (profile_id);

CREATE TABLE season_cost_items (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id         UUID          NOT NULL,
    season_id          UUID          NOT NULL,
    category           TEXT          NOT NULL CHECK (category IN
                         ('seed','fertilizer','pesticide','irrigation','labour','land_lease','transport','other')),
    item_name          TEXT          NOT NULL,
    quantity           NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
    unit               TEXT          NOT NULL,
    unit_cost          NUMERIC(14,2) NOT NULL CHECK (unit_cost >= 0),
    total_cost         NUMERIC(14,2) GENERATED ALWAYS AS (round(quantity * unit_cost, 2)) STORED,
    planned_date       DATE,
    price_source_type  TEXT          NOT NULL DEFAULT 'owner_estimate' CHECK (price_source_type IN
                         ('supplier_quote','own_purchase_history','reference_market_price','public_listing','owner_estimate')),
    price_source_note  TEXT,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, season_id) REFERENCES farming_seasons (profile_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_cost_items_season ON season_cost_items (season_id);

-- ---------------------------------------------------------------------------
-- 6. Declared debts (F2 internal; S1 §3, §5.1)
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id   UUID        NOT NULL REFERENCES business_profiles(id),
    uploaded_by  UUID        NOT NULL REFERENCES users(id),
    storage_key  TEXT        NOT NULL UNIQUE,             -- random name on private disk (SUG-18)
    mime_type    TEXT        NOT NULL CHECK (mime_type IN ('image/jpeg','image/png')),
    size_bytes   INTEGER     NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 5242880),
    sha256       CHAR(64)    NOT NULL,                     -- duplicate-evidence check (S1 F1)
    purpose      TEXT        NOT NULL DEFAULT 'receipt' CHECK (purpose IN ('receipt','quotation','loan_paper','other')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id)
);
CREATE INDEX ix_documents_profile_hash ON documents (profile_id, sha256);

CREATE TABLE debt_facilities (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id             UUID          NOT NULL REFERENCES business_profiles(id),
    season_id              UUID,
    lender_type            TEXT          NOT NULL CHECK (lender_type IN
                             ('bank','mfi','ngo','samity','mohajon','supplier_credit','dealer_credit','other')),
    lender_label           TEXT          NOT NULL,          -- free text, e.g. 'DEMO NGO'
    original_principal     NUMERIC(14,2) NOT NULL CHECK (original_principal > 0),
    outstanding_balance    NUMERIC(14,2) NOT NULL CHECK (outstanding_balance >= 0),
    outstanding_as_of      DATE          NOT NULL,
    installment_amount     NUMERIC(14,2) CHECK (installment_amount > 0),
    installment_frequency  TEXT          NOT NULL CHECK (installment_frequency IN ('weekly','monthly','single')),
    next_due_date          DATE,
    is_overdue             BOOLEAN       NOT NULL DEFAULT FALSE,
    overdue_amount         NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (overdue_amount >= 0),
    interest_fee_note      TEXT,
    evidence_state         TEXT          NOT NULL DEFAULT 'declared' CHECK (evidence_state IN ('declared','document_attached')),
    document_id            UUID,
    status                 TEXT          NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed')),
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, season_id)   REFERENCES farming_seasons (profile_id, id),
    FOREIGN KEY (profile_id, document_id) REFERENCES documents (profile_id, id),
    CHECK (installment_frequency = 'single' OR installment_amount IS NOT NULL),
    CHECK (status = 'closed' OR outstanding_balance = 0 OR next_due_date IS NOT NULL),
    CHECK (evidence_state = 'declared' OR document_id IS NOT NULL)
);
CREATE INDEX ix_debts_profile ON debt_facilities (profile_id) WHERE status = 'active';

-- ---------------------------------------------------------------------------
-- 7. Ledger (F1 + F2 internal). Accounting effect per txn_type is defined in
--    DATABASE_SCHEMA.md §4 and reference_calculations.py (S1 F2, Appendix A4)
-- ---------------------------------------------------------------------------
CREATE TABLE extraction_drafts (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id                UUID        NOT NULL REFERENCES business_profiles(id),
    document_id               UUID        NOT NULL,
    status                    TEXT        NOT NULL DEFAULT 'pending'
                                          CHECK (status IN ('pending','confirmed','discarded','failed')),
    provider                  TEXT        NOT NULL,
    model                     TEXT,
    proposed                  JSONB       NOT NULL DEFAULT '{}'::jsonb,   -- fields + confidence, never auto-posted
    confirmed_transaction_id  UUID,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at               TIMESTAMPTZ,
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, document_id) REFERENCES documents (profile_id, id)
);

CREATE TABLE transactions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id            UUID          NOT NULL REFERENCES business_profiles(id),
    txn_type              TEXT          NOT NULL CHECK (txn_type IN (
                            'sale_cash','sale_credit','receivable_collection',
                            'purchase_cash','purchase_credit','payable_payment','operating_expense',
                            'loan_received','loan_principal_repayment','loan_interest_fee_payment',
                            'owner_withdrawal','owner_contribution')),
    amount                NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency              CHAR(3)       NOT NULL DEFAULT 'BDT' CHECK (currency = 'BDT'),
    value_date            DATE          NOT NULL,
    settlement_date       DATE,
    category              TEXT,                            -- expense/farm category
    note                  TEXT          CHECK (char_length(note) <= 300),
    supplier_id           UUID,
    debt_facility_id      UUID,
    season_id             UUID,
    season_cost_item_id   UUID,
    document_id           UUID,
    entry_method          TEXT          NOT NULL DEFAULT 'manual' CHECK (entry_method IN ('manual','photo_assisted','seed')),
    evidence_state        TEXT          NOT NULL DEFAULT 'declared' CHECK (evidence_state IN ('declared','document_attached')),
    status                TEXT          NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed','voided')),
    duplicate_confirmed   BOOLEAN       NOT NULL DEFAULT FALSE,
    void_reason           TEXT,
    voided_at             TIMESTAMPTZ,
    client_request_id     UUID,
    created_by            UUID          NOT NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    UNIQUE (profile_id, client_request_id),
    FOREIGN KEY (profile_id, supplier_id)         REFERENCES suppliers (profile_id, id),
    FOREIGN KEY (profile_id, debt_facility_id)    REFERENCES debt_facilities (profile_id, id),
    FOREIGN KEY (profile_id, season_id)           REFERENCES farming_seasons (profile_id, id),
    FOREIGN KEY (profile_id, season_cost_item_id) REFERENCES season_cost_items (profile_id, id),
    FOREIGN KEY (profile_id, document_id)         REFERENCES documents (profile_id, id),
    CHECK (supplier_id IS NULL OR txn_type IN ('purchase_cash','purchase_credit','payable_payment')),
    CHECK (debt_facility_id IS NULL OR txn_type IN ('loan_received','loan_principal_repayment','loan_interest_fee_payment')),
    CHECK (evidence_state = 'declared' OR document_id IS NOT NULL),
    CHECK ((status = 'voided') = (voided_at IS NOT NULL)),
    CHECK (status <> 'voided' OR void_reason IS NOT NULL),
    CHECK (settlement_date IS NULL OR settlement_date >= value_date)
);
CREATE INDEX ix_txn_profile_date ON transactions (profile_id, value_date) WHERE status = 'confirmed';
CREATE INDEX ix_txn_profile_supplier ON transactions (profile_id, supplier_id) WHERE supplier_id IS NOT NULL;
CREATE INDEX ix_txn_dup_check ON transactions (profile_id, txn_type, amount, value_date) WHERE status = 'confirmed';
CREATE INDEX ix_txn_season ON transactions (season_id) WHERE season_id IS NOT NULL;

ALTER TABLE extraction_drafts
    ADD FOREIGN KEY (profile_id, confirmed_transaction_id) REFERENCES transactions (profile_id, id);

-- ---------------------------------------------------------------------------
-- 8. Financing requests and purpose items (F7)
-- ---------------------------------------------------------------------------
CREATE TABLE financing_requests (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id                UUID          NOT NULL REFERENCES business_profiles(id),
    season_id                 UUID,
    status                    TEXT          NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','archived')),
    requested_amount          NUMERIC(14,2) NOT NULL CHECK (requested_amount > 0),
    purpose_text              TEXT          NOT NULL CHECK (char_length(purpose_text) BETWEEN 2 AND 500),
    purpose_category          TEXT          NOT NULL CHECK (purpose_category IN ('inventory','farm_inputs','equipment','other')),
    desired_start_date        DATE,
    associated_expenses       NUMERIC(14,2) CHECK (associated_expenses >= 0),
    liquidity_buffer          NUMERIC(14,2) CHECK (liquidity_buffer >= 0),
    buffer_justification      TEXT,
    cash_safely_available     NUMERIC(14,2) CHECK (cash_safely_available >= 0),
    committed_financing       NUMERIC(14,2) CHECK (committed_financing >= 0),
    current_cash_balance      NUMERIC(14,2) CHECK (current_cash_balance >= 0),   -- optional (DEC-35)
    minimum_cash_reserve      NUMERIC(14,2) CHECK (minimum_cash_reserve >= 0),
    schedule_type             TEXT          CHECK (schedule_type IN ('equal_installments','single_payment')),
    installment_count         INTEGER       CHECK (installment_count BETWEEN 1 AND 60),
    installment_frequency     TEXT          CHECK (installment_frequency IN ('weekly','monthly')),
    first_due_date            DATE,
    interest_fees_total       NUMERIC(14,2) CHECK (interest_fees_total >= 0),     -- NULL = unknown (flag)
    interest_fees_unknown     BOOLEAN       NOT NULL DEFAULT FALSE,
    over_request_explanation  TEXT          CHECK (char_length(over_request_explanation) <= 500),
    created_at                TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, season_id) REFERENCES farming_seasons (profile_id, id),
    CHECK (schedule_type IS DISTINCT FROM 'single_payment' OR (installment_count IS NULL OR installment_count = 1)),
    CHECK (schedule_type IS DISTINCT FROM 'equal_installments' OR installment_frequency IS NOT NULL)
);
CREATE INDEX ix_finreq_profile ON financing_requests (profile_id);

CREATE TABLE financing_request_items (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id                   UUID          NOT NULL,
    financing_request_id         UUID          NOT NULL,
    item_name                    TEXT          NOT NULL CHECK (char_length(item_name) BETWEEN 1 AND 120),
    quantity                     NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
    unit                         TEXT          NOT NULL,
    unit_price                   NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),
    line_total                   NUMERIC(14,2) GENERATED ALWAYS AS (round(quantity * unit_price, 2)) STORED,
    price_source_type            TEXT          NOT NULL CHECK (price_source_type IN
                                   ('supplier_quote','own_purchase_history','reference_market_price','public_listing','owner_estimate')),
    price_date                   DATE,
    price_source_note            TEXT,
    ai_proposed                  BOOLEAN       NOT NULL DEFAULT FALSE,
    confirmed                    BOOLEAN       NOT NULL DEFAULT TRUE,     -- AI rows start FALSE (FR-FIN-03)
    source_season_cost_item_id   UUID,
    created_at                   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, financing_request_id) REFERENCES financing_requests (profile_id, id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id, source_season_cost_item_id) REFERENCES season_cost_items (profile_id, id),
    CHECK (ai_proposed OR confirmed)
);
CREATE INDEX ix_finitems_request ON financing_request_items (financing_request_id);

-- ---------------------------------------------------------------------------
-- 9. Forecasts, assessments, scenarios (F3, assessment, L1/L2 scenarios)
-- ---------------------------------------------------------------------------
CREATE TABLE forecast_runs (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id                   UUID          NOT NULL REFERENCES business_profiles(id),
    as_of_date                   DATE          NOT NULL,
    method_version               TEXT          NOT NULL,          -- e.g. 'weekly-baseline-v1'
    status                       TEXT          NOT NULL CHECK (status IN ('ok','insufficient_history')),
    window_weeks                 INTEGER       NOT NULL,
    weeks_with_records           INTEGER       NOT NULL,
    min_weeks_required           INTEGER       NOT NULL,
    net_weekly_expected          NUMERIC(14,2),
    net_weekly_low               NUMERIC(14,2),
    net_weekly_high              NUMERIC(14,2),
    collections_weekly_expected  NUMERIC(14,2),
    payments_weekly_expected     NUMERIC(14,2),
    purchases_weekly_expected    NUMERIC(14,2),
    horizons                     JSONB         NOT NULL DEFAULT '{}'::jsonb,   -- 7/30/60/90 day values
    assumptions                  JSONB         NOT NULL DEFAULT '{}'::jsonb,
    profile_data_version         BIGINT        NOT NULL,
    created_at                   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    CHECK (status = 'insufficient_history' OR
           (net_weekly_expected IS NOT NULL AND net_weekly_low IS NOT NULL AND net_weekly_high IS NOT NULL))
);
CREATE INDEX ix_forecast_profile_time ON forecast_runs (profile_id, created_at DESC);

CREATE TABLE financial_assessments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id              UUID          NOT NULL,
    financing_request_id    UUID          NOT NULL,
    forecast_run_id         UUID,
    as_of_date              DATE          NOT NULL,
    engine_version          TEXT          NOT NULL,          -- e.g. 'assess-v1'
    status                  TEXT          NOT NULL CHECK (status IN
                              ('insufficient_information','not_affordable_base_case','ready_for_lender_review')),
    purpose_items_total     NUMERIC(14,2),
    funding_gap             NUMERIC(14,2),
    request_minus_gap       NUMERIC(14,2),
    missing_items           JSONB         NOT NULL DEFAULT '[]'::jsonb,
    flags                   JSONB         NOT NULL DEFAULT '[]'::jsonb,
    base_result             JSONB         NOT NULL DEFAULT '{}'::jsonb,   -- due-date checks / crop check
    explanation             JSONB         NOT NULL DEFAULT '{}'::jsonb,   -- formulas, inputs with sources
    inputs_sha256           CHAR(64)      NOT NULL,
    profile_data_version    BIGINT        NOT NULL,
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, financing_request_id) REFERENCES financing_requests (profile_id, id),
    FOREIGN KEY (profile_id, forecast_run_id)      REFERENCES forecast_runs (profile_id, id),
    CHECK (status = 'insufficient_information' OR funding_gap IS NOT NULL)
);
CREATE INDEX ix_assess_request_time ON financial_assessments (financing_request_id, created_at DESC);

CREATE TABLE news_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    headline        TEXT        NOT NULL CHECK (char_length(headline) BETWEEN 5 AND 300),
    headline_lang   TEXT        NOT NULL CHECK (headline_lang IN ('bn','en')),
    summary         TEXT        CHECK (char_length(summary) <= 500),   -- team-written, not article text
    source_name     TEXT        NOT NULL,
    source_url      TEXT,
    published_date  DATE        NOT NULL,
    event_date      DATE,
    event_type      TEXT        NOT NULL CHECK (event_type IN (
                       'flood_waterlogging','market_fire','hartal_road_blockade','disease_outbreak',
                       'price_shock','policy_change','factory_closure_layoffs','market_eviction_relocation')),
    districts       TEXT[]      NOT NULL DEFAULT '{}',
    upazilas        TEXT[]      NOT NULL DEFAULT '{}',
    sectors         TEXT[]      NOT NULL DEFAULT '{}',
    commodities     TEXT[]      NOT NULL DEFAULT '{}',
    source_count    INTEGER     NOT NULL DEFAULT 1 CHECK (source_count >= 1),
    dedup_key       TEXT        NOT NULL UNIQUE,
    is_demo         BOOLEAN     NOT NULL DEFAULT FALSE,
    curated_by      TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (is_demo OR (source_url IS NOT NULL AND source_url ~ '^https?://')),
    CHECK (NOT is_demo OR source_name = 'DEMO (fictional)')
);
CREATE INDEX ix_news_districts ON news_events USING GIN (districts);
CREATE INDEX ix_news_date ON news_events (published_date DESC);

CREATE TABLE risk_scenarios (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id     UUID        NOT NULL,
    assessment_id  UUID        NOT NULL,
    scenario_type  TEXT        NOT NULL CHECK (scenario_type IN
                     ('supplier_delay','input_price_rise','harvest_price_fall','yield_shortfall')),
    origin         TEXT        NOT NULL CHECK (origin IN ('auto','news')),
    news_event_id  UUID        REFERENCES news_events(id),
    supplier_id    UUID,
    parameters     JSONB       NOT NULL,          -- e.g. {"days":7,"share":"0.65","start":"2026-12-01"}
    status         TEXT        NOT NULL CHECK (status IN ('computed','proposed','dismissed')),
    result         JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at    TIMESTAMPTZ,
    UNIQUE (profile_id, id),
    FOREIGN KEY (profile_id, assessment_id) REFERENCES financial_assessments (profile_id, id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id, supplier_id)   REFERENCES suppliers (profile_id, id),
    CHECK (origin <> 'news' OR news_event_id IS NOT NULL),
    CHECK (status <> 'computed' OR result IS NOT NULL),
    CHECK (origin <> 'auto' OR status = 'computed')     -- only news-origin scenarios wait for confirmation (DEC-30)
);
CREATE INDEX ix_scenarios_assessment ON risk_scenarios (assessment_id);

-- ---------------------------------------------------------------------------
-- 10. Consent, shared reports, lender review (F10 simplified, lender portal)
-- ---------------------------------------------------------------------------
CREATE TABLE consents (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id               UUID        NOT NULL REFERENCES business_profiles(id),
    lender_organization_id   UUID        NOT NULL REFERENCES lender_organizations(id),
    requested_by_user_id     UUID        NOT NULL REFERENCES lender_officers(user_id),
    requested_sections       TEXT[]      NOT NULL CHECK (cardinality(requested_sections) >= 1 AND requested_sections <@ ARRAY[
                               'profile_summary','money_summary','forecast','financing_request','obligations',
                               'supplier_risk','news_signals','season_summary','transaction_list']::TEXT[]),
    request_message          TEXT        CHECK (char_length(request_message) <= 500),
    status                   TEXT        NOT NULL DEFAULT 'requested'
                                         CHECK (status IN ('requested','approved','declined','revoked')),
    approved_sections        TEXT[]      CHECK (approved_sections <@ ARRAY[
                               'profile_summary','money_summary','forecast','financing_request','obligations',
                               'supplier_risk','news_signals','season_summary','transaction_list']::TEXT[]),
    financing_request_id     UUID,
    assessment_id            UUID,
    valid_until              TIMESTAMPTZ,
    approved_at              TIMESTAMPTZ,
    declined_at              TIMESTAMPTZ,
    revoked_at               TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (profile_id, financing_request_id) REFERENCES financing_requests (profile_id, id),
    FOREIGN KEY (profile_id, assessment_id)        REFERENCES financial_assessments (profile_id, id),
    CHECK (status <> 'approved' OR (approved_sections IS NOT NULL AND valid_until IS NOT NULL
                                    AND approved_at IS NOT NULL AND assessment_id IS NOT NULL
                                    AND 'profile_summary' = ANY(approved_sections)
                                    AND 'financing_request' = ANY(approved_sections))),
    CHECK (status <> 'revoked' OR revoked_at IS NOT NULL),
    CHECK (status <> 'declined' OR declined_at IS NOT NULL)
);
CREATE INDEX ix_consents_org_status ON consents (lender_organization_id, status);
CREATE INDEX ix_consents_profile ON consents (profile_id, status);

CREATE TABLE shared_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_id       UUID        NOT NULL REFERENCES consents(id) ON DELETE CASCADE,
    version          INTEGER     NOT NULL CHECK (version >= 1),
    snapshot         JSONB       NOT NULL,          -- approved sections only (DEC-31)
    snapshot_sha256  CHAR(64)    NOT NULL,          -- of canonical JSON (DEC-19)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (consent_id, version)
);

CREATE TABLE lender_reviews (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_id       UUID        NOT NULL UNIQUE REFERENCES consents(id),
    organization_id  UUID        NOT NULL REFERENCES lender_organizations(id),
    status           TEXT        NOT NULL DEFAULT 'under_review'
                                 CHECK (status IN ('under_review','info_requested','decision_recorded')),
    decision         TEXT        CHECK (decision IN ('proceed','decline','refer')),   -- demo only (DEC-34)
    decision_reason  TEXT,
    decided_by       UUID        REFERENCES lender_officers(user_id),
    decided_at       TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((status = 'decision_recorded') = (decision IS NOT NULL)),
    CHECK (decision IS NULL OR (decision_reason IS NOT NULL AND char_length(decision_reason) >= 5
                                AND decided_by IS NOT NULL AND decided_at IS NOT NULL))
);

CREATE TABLE lender_review_events (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id         UUID        NOT NULL REFERENCES lender_reviews(id) ON DELETE CASCADE,
    officer_user_id   UUID        NOT NULL REFERENCES lender_officers(user_id),
    event_type        TEXT        NOT NULL CHECK (event_type IN ('status_change','note','info_request','decision')),
    body              TEXT        NOT NULL CHECK (char_length(body) BETWEEN 1 AND 1000),
    visible_to_owner  BOOLEAN     NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (event_type <> 'note' OR visible_to_owner = FALSE),
    CHECK (event_type <> 'info_request' OR visible_to_owner = TRUE)
);
CREATE INDEX ix_review_events_review ON lender_review_events (review_id, created_at);

-- ---------------------------------------------------------------------------
-- 11. Audit and AI metadata
-- ---------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id                      BIGSERIAL PRIMARY KEY,
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_user_id           UUID,
    actor_role              TEXT,
    action                  TEXT        NOT NULL,   -- e.g. 'auth.login', 'consent.approve', 'consent.read'
    outcome                 TEXT        NOT NULL CHECK (outcome IN ('success','denied','failure')),
    entity_type             TEXT,
    entity_id               UUID,
    profile_id              UUID,
    lender_organization_id  UUID,
    ip_sha256               CHAR(64),
    metadata                JSONB       NOT NULL DEFAULT '{}'::jsonb   -- never passwords/tokens
);
CREATE INDEX ix_audit_profile_time ON audit_logs (profile_id, occurred_at DESC);
CREATE INDEX ix_audit_entity ON audit_logs (entity_type, entity_id);

CREATE FUNCTION audit_logs_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only';
END $$;
CREATE TRIGGER trg_audit_no_update BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_append_only();

CREATE TABLE ai_interactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES users(id),
    profile_id       UUID        REFERENCES business_profiles(id),
    feature          TEXT        NOT NULL CHECK (feature IN ('receipt_extraction','purpose_parse','advisor')),
    provider         TEXT        NOT NULL,       -- 'gemini' | 'none'
    model            TEXT,
    status           TEXT        NOT NULL CHECK (status IN ('ok','error','blocked','fallback','limit')),
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    latency_ms       INTEGER,
    tools_called     TEXT[]      NOT NULL DEFAULT '{}',
    grounding_check  TEXT        NOT NULL DEFAULT 'not_applicable'
                                 CHECK (grounding_check IN ('passed','failed','not_applicable')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()        -- no prompt/response text stored (SUG-22)
);
CREATE INDEX ix_ai_user_day ON ai_interactions (user_id, feature, created_at);

COMMIT;
