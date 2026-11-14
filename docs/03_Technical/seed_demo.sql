-- =============================================================================
-- Bonik Bondhu MVP — DEMO seed data (MP §18). ALL DATA IS FICTIONAL.
-- Dates are relative to CURRENT_DATE so the forecast always has history
-- (FR-DEMO-02). Re-run on demo day after TRUNCATE (see DATABASE_SCHEMA.md §9).
--
-- Passwords: rows get a NON-LOGINABLE placeholder hash. The CLI command
-- `python -m app.cli seed-demo` runs this file and then sets real Argon2id
-- hashes from the environment variable DEMO_PASSWORD (SUG-02, SUG-29).
-- Phone numbers are fictional test values; emails use the reserved .invalid TLD.
--
-- Expected outputs for these records: TESTING_AND_ACCEPTANCE.md §4 (golden
-- cases D1-D4), produced by 05_Development/reference_calculations.py.
-- =============================================================================
BEGIN;

DO $$
DECLARE
    a          DATE := CURRENT_DATE;        -- as_of
    ph         TEXT := '!seed-placeholder-not-loginable!';
    u_rahim    UUID; u_karim UUID; u_selina UUID; u_off1 UUID; u_off2 UUID; u_off3 UUID;
    org_bank   UUID; org_mfi UUID;
    p_store    UUID; p_farm UUID; p_karim UUID; p_selina UUID;
    s_a UUID; s_b UUID; s_c UUID;
    season     UUID;
    ci_seed UUID; ci_fert UUID; ci_irr UUID; ci_lab UUID; ci_pest UUID; ci_tr UUID;
    req        UUID;
    i          INT;
    blk_date   DATE;
    coll       NUMERIC[] := ARRAY[152000,128500,171000,140500,118000,162000,149500,133000];
    purch      NUMERIC[] := ARRAY[100000, 83000,112000, 92000, 75000,106000, 98000, 86000];
    nets2      NUMERIC[] := ARRAY[9000,7500,11000,6000,8500,10000];
BEGIN
    -- ---------------- users ----------------
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Rahim Uddin (DEMO)', '+8801900000001', 'd1.rahim@demo.invalid', ph, 'owner', TRUE) RETURNING id INTO u_rahim;
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Karim Mia (DEMO)', '+8801900000002', 'd2.karim@demo.invalid', ph, 'owner', TRUE) RETURNING id INTO u_karim;
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Selina Akter (DEMO)', '+8801900000004', 'd4.selina@demo.invalid', ph, 'owner', TRUE) RETURNING id INTO u_selina;
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Nasrin Officer (DEMO)', '+8801900000101', 'l1.nasrin@demo.invalid', ph, 'lender_officer', TRUE) RETURNING id INTO u_off1;
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Tanvir Officer (DEMO)', '+8801900000102', 'l2.tanvir@demo.invalid', ph, 'lender_officer', TRUE) RETURNING id INTO u_off2;
    INSERT INTO users (full_name, phone_e164, email, password_hash, role, is_demo)
    VALUES ('Other-Org Officer (DEMO)', '+8801900000103', 'l3.other@demo.invalid', ph, 'lender_officer', TRUE) RETURNING id INTO u_off3;

    -- ---------------- lenders (fictional, ASM-03) ----------------
    INSERT INTO lender_organizations (name, org_type, is_demo) VALUES ('DEMO Bank Ltd (fictional)', 'bank', TRUE) RETURNING id INTO org_bank;
    INSERT INTO lender_organizations (name, org_type, is_demo) VALUES ('DEMO MFI (fictional)', 'mfi', TRUE) RETURNING id INTO org_mfi;
    INSERT INTO lender_officers (user_id, organization_id, designation) VALUES
        (u_off1, org_bank, 'SME Officer'), (u_off2, org_bank, 'Branch Manager'), (u_off3, org_mfi, 'Credit Officer');

    -- ======================================================================
    -- D1 Rahim Store (shop): irregular sales, 65% supplier, request > gap
    -- ======================================================================
    INSERT INTO business_profiles (owner_user_id, activity_type, display_name, business_category, district, upazila,
                                   market_area, household_withdrawal_monthly, household_declared_at, no_debt_declared_at,
                                   share_code, is_demo)
    VALUES (u_rahim, 'shop', 'Rahim Store', 'grocery', 'Dhaka', 'Savar', 'Baipail (DEMO)', 15000, now(), now(),
            '7KQ2M9XA4P', TRUE) RETURNING id INTO p_store;

    INSERT INTO suppliers (profile_id, display_name, goods_supplied, district, upazila)
    VALUES (p_store, 'Supplier A (DEMO wholesaler)', 'rice, oil, lentils', 'Gazipur', 'Kaliakair') RETURNING id INTO s_a;
    INSERT INTO suppliers (profile_id, display_name, goods_supplied, district, upazila)
    VALUES (p_store, 'Supplier B (DEMO)', 'lentils, flour', 'Dhaka', 'Savar') RETURNING id INTO s_b;
    INSERT INTO suppliers (profile_id, display_name, goods_supplied, district, upazila)
    VALUES (p_store, 'Supplier C (DEMO)', 'spices', 'Dhaka', 'Dhamrai') RETURNING id INTO s_c;

    FOR i IN 1..8 LOOP     -- week i = oldest(1) .. newest(8); block = [a-7(9-i), a-7(9-i)+6]
        blk_date := a - 7 * (9 - i) + 3;
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, entry_method, created_by, note)
        VALUES (p_store, 'sale_cash', coll[i], blk_date, 'seed', u_rahim, 'weekly cash sales (DEMO)');
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, supplier_id, entry_method, created_by)
        VALUES (p_store, 'purchase_cash', round(purch[i] * 0.65, 2), blk_date, s_a, 'seed', u_rahim),
               (p_store, 'purchase_cash', round(purch[i] * 0.25, 2), blk_date, s_b, 'seed', u_rahim),
               (p_store, 'purchase_cash', round(purch[i] * 0.10, 2), blk_date, s_c, 'seed', u_rahim);
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, category, entry_method, created_by)
        VALUES (p_store, 'operating_expense', 18000, blk_date, 'rent_salary_utilities', 'seed', u_rahim);
        IF i IN (4, 8) THEN
            INSERT INTO transactions (profile_id, txn_type, amount, value_date, entry_method, created_by)
            VALUES (p_store, 'owner_withdrawal', 15000, blk_date, 'seed', u_rahim);
        END IF;
    END LOOP;

    INSERT INTO financing_requests (profile_id, requested_amount, purpose_text, purpose_category, desired_start_date,
        associated_expenses, liquidity_buffer, buffer_justification, cash_safely_available, committed_financing,
        current_cash_balance, minimum_cash_reserve, schedule_type, installment_count, installment_frequency,
        first_due_date, interest_fees_total)
    VALUES (p_store, 200000, 'ঈদের আগে চাল-ডাল-তেল কিনবো (DEMO)', 'inventory', a,
        10000, 20000, 'Operating buffer for Eid rush (DEMO)', 30000, 0,
        45000, 10000, 'equal_installments', 12, 'weekly', a + 7, 16000) RETURNING id INTO req;
    INSERT INTO financing_request_items (profile_id, financing_request_id, item_name, quantity, unit, unit_price,
        price_source_type, price_date, price_source_note)
    VALUES (p_store, req, 'Mixed stock units (DEMO)', 100, 'unit', 1500, 'supplier_quote', a - 2, 'Quotation from Supplier A (DEMO)');

    -- ======================================================================
    -- D3 Rahim Rice Farm (crop_farm) — same user (multi-profile, MP §5)
    -- ======================================================================
    INSERT INTO business_profiles (owner_user_id, activity_type, display_name, business_category, district, upazila,
                                   household_withdrawal_monthly, household_declared_at, share_code, is_demo)
    VALUES (u_rahim, 'crop_farm', 'Rahim Rice Farm', 'crop', 'Dhaka', 'Dhamrai', 0, now(), 'R3FARM8DMB', TRUE)
    RETURNING id INTO p_farm;

    INSERT INTO farming_seasons (profile_id, crop_name, variety, season_name, season_label, area_value, area_unit,
        area_acres, sowing_date, expected_harvest_date, expected_output_low, expected_output_expected,
        expected_output_high, expected_price_low, expected_price_expected, expected_price_high, status)
    VALUES (p_farm, 'Rice', NULL, 'boro', '2026-27', 150, 'decimal', 1.5, DATE '2027-01-10', DATE '2027-05-05',
        2700, 3300, 3750, 28, 32, 35, 'planned') RETURNING id INTO season;

    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'seed',       'Seed (DEMO)',          1, 'lot', 4500)  RETURNING id INTO ci_seed;
    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'fertilizer', 'Fertilizer (DEMO)',    1, 'lot', 18000) RETURNING id INTO ci_fert;
    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'irrigation', 'Irrigation (DEMO)',    1, 'lot', 12000) RETURNING id INTO ci_irr;
    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'labour',     'Labour (DEMO)',        1, 'lot', 22000) RETURNING id INTO ci_lab;
    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'pesticide',  'Pesticide (DEMO)',     1, 'lot', 5500)  RETURNING id INTO ci_pest;
    INSERT INTO season_cost_items (profile_id, season_id, category, item_name, quantity, unit, unit_cost) VALUES
        (p_farm, season, 'transport',  'Transport (DEMO)',     1, 'lot', 3000)  RETURNING id INTO ci_tr;

    INSERT INTO transactions (profile_id, txn_type, amount, value_date, category, season_id, season_cost_item_id,
                              entry_method, created_by)
    VALUES (p_farm, 'purchase_cash', 4500, a - 3, 'seed', season, ci_seed, 'seed', u_rahim);

    INSERT INTO debt_facilities (profile_id, season_id, lender_type, lender_label, original_principal,
        outstanding_balance, outstanding_as_of, installment_frequency, next_due_date)
    VALUES (p_farm, season, 'dealer_credit', 'Fertilizer dealer credit (DEMO)', 6000, 6000, a, 'single', DATE '2027-05-15');

    INSERT INTO financing_requests (profile_id, season_id, requested_amount, purpose_text, purpose_category,
        desired_start_date, associated_expenses, liquidity_buffer, buffer_justification, cash_safely_available,
        committed_financing, current_cash_balance, minimum_cash_reserve, schedule_type, installment_count,
        first_due_date, interest_fees_total)
    VALUES (p_farm, season, 40000, 'বোরো ধানের সার, সেচ ও শ্রমিক খরচ (DEMO)', 'farm_inputs', DATE '2027-01-05',
        0, 3000, 'Small reserve for input price changes (DEMO)', 15000, 0, 23500, 5000,
        'single_payment', 1, DATE '2027-05-20', 2400) RETURNING id INTO req;
    INSERT INTO financing_request_items (profile_id, financing_request_id, item_name, quantity, unit, unit_price,
        price_source_type, price_date, source_season_cost_item_id) VALUES
        (p_farm, req, 'Fertilizer (DEMO)', 1, 'lot', 18000, 'owner_estimate', a, ci_fert),
        (p_farm, req, 'Irrigation (DEMO)', 1, 'lot', 12000, 'owner_estimate', a, ci_irr),
        (p_farm, req, 'Labour (DEMO)',     1, 'lot', 22000, 'owner_estimate', a, ci_lab);

    -- ======================================================================
    -- D2 Karim Variety Store: existing MFI + samity debts -> base-case stress
    -- ======================================================================
    INSERT INTO business_profiles (owner_user_id, activity_type, display_name, business_category, district, upazila,
                                   household_withdrawal_monthly, household_declared_at, share_code, is_demo)
    VALUES (u_karim, 'shop', 'Karim Variety Store', 'grocery', 'Dhaka', 'Savar', 8000, now(), 'KRM2D7XQ5A', TRUE)
    RETURNING id INTO p_karim;
    FOR i IN 1..6 LOOP     -- newest 6 blocks only (blocks 7-8 empty = missing, not zero)
        blk_date := a - 7 * (7 - i) + 3;
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, entry_method, created_by) VALUES
            (p_karim, 'sale_cash', 30000 + nets2[i], blk_date, 'seed', u_karim),
            (p_karim, 'purchase_cash', 24000, blk_date, 'seed', u_karim);
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, category, entry_method, created_by) VALUES
            (p_karim, 'operating_expense', 6000, blk_date, 'rent_salary_utilities', 'seed', u_karim);
    END LOOP;
    INSERT INTO debt_facilities (profile_id, lender_type, lender_label, original_principal, outstanding_balance,
        outstanding_as_of, installment_amount, installment_frequency, next_due_date) VALUES
        (p_karim, 'mfi',    'DEMO NGO weekly loan', 100000, 60000, a, 2500, 'weekly',  a + 3),
        (p_karim, 'samity', 'Bazar samity (DEMO)',   30000, 18000, a, 3000, 'monthly', a + 10);
    INSERT INTO financing_requests (profile_id, requested_amount, purpose_text, purpose_category, desired_start_date,
        associated_expenses, liquidity_buffer, cash_safely_available, committed_financing, current_cash_balance,
        minimum_cash_reserve, schedule_type, installment_count, installment_frequency, first_due_date, interest_fees_total)
    VALUES (p_karim, 80000, 'দোকানের মাল কিনবো (DEMO)', 'inventory', a, 3000, 5000, 8000, 0, 12000, 2000,
        'equal_installments', 12, 'weekly', a + 7, 4000) RETURNING id INTO req;
    INSERT INTO financing_request_items (profile_id, financing_request_id, item_name, quantity, unit, unit_price,
        price_source_type, price_date)
    VALUES (p_karim, req, 'Mixed groceries (DEMO)', 1, 'lot', 70000, 'owner_estimate', a);

    -- ======================================================================
    -- D4 Selina Tailoring: insufficient information
    -- ======================================================================
    INSERT INTO business_profiles (owner_user_id, activity_type, display_name, business_category, district, upazila,
                                   share_code, is_demo)
    VALUES (u_selina, 'shop', 'Selina Tailoring', 'service', 'Dhaka', 'Savar', 'SLN4T8WQ3Z', TRUE) RETURNING id INTO p_selina;
    FOR i IN 1..2 LOOP
        blk_date := a - 7 * (3 - i) + 3;
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, entry_method, created_by) VALUES
            (p_selina, 'sale_cash', 9000, blk_date, 'seed', u_selina),
            (p_selina, 'purchase_cash', 3000, blk_date, 'seed', u_selina);
        INSERT INTO transactions (profile_id, txn_type, amount, value_date, category, entry_method, created_by) VALUES
            (p_selina, 'operating_expense', 2000, blk_date, 'other', 'seed', u_selina);
    END LOOP;
    INSERT INTO financing_requests (profile_id, requested_amount, purpose_text, purpose_category)
    VALUES (p_selina, 30000, 'নতুন সেলাই মেশিন (DEMO)', 'equipment');

    -- ======================================================================
    -- DEMO news events (fictional; FR-NEWS-03 shows DEMO badge)
    -- ======================================================================
    INSERT INTO news_events (headline, headline_lang, summary, source_name, published_date, event_date, event_type,
                             districts, upazilas, sectors, commodities, source_count, dedup_key, is_demo, curated_by)
    VALUES
    ('DEMO: Road blockade reported near a wholesale market in Kaliakair (fictional)', 'en',
     'Fictional event for demonstration. Transport to and from a wholesale market reported disrupted.',
     'DEMO (fictional)', a - 1, a - 1, 'hartal_road_blockade', ARRAY['Gazipur'], ARRAY['Kaliakair'],
     ARRAY['grocery','wholesale'], ARRAY['rice','oil'], 1, 'demo-blockade-kaliakair-' || (a - 1)::text, TRUE, 'team-demo'),
    ('ডেমো: ধামরাইয়ে নিচু জমিতে জলাবদ্ধতার খবর (কাল্পনিক)', 'bn',
     'Fictional event for demonstration. Low-lying fields reported waterlogged.',
     'DEMO (fictional)', a - 2, a - 2, 'flood_waterlogging', ARRAY['Dhaka'], ARRAY['Dhamrai'],
     ARRAY['crop'], ARRAY['rice'], 1, 'demo-flood-dhamrai-' || (a - 2)::text, TRUE, 'team-demo');
END $$;

COMMIT;
