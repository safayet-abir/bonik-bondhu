// Response shapes from docs/03_Technical/API_SPECIFICATION.md. Money is a
// 2-decimal string; never parse it to float for arithmetic.

export type Role = "owner" | "lender_officer" | "admin";

export type Me = {
  id: string;
  full_name: string;
  phone: string;
  email: string;
  role: Role;
  preferred_language: "bn" | "en";
  is_demo: boolean;
  lender: { organization: { id: string; name: string; is_demo: boolean }; designation: string | null } | null;
};

export type ActivityType = "shop" | "crop_farm";

export type Profile = {
  id: string;
  activity_type: ActivityType;
  display_name: string;
  business_category: string | null;
  district: string | null;
  upazila: string | null;
  market_area: string | null;
  household_withdrawal_monthly: string | null;
  household_declared: boolean;
  no_debt_declared: boolean;
  share_code: string;
  is_demo: boolean;
  financing_fields_complete: boolean;
};

export type TxnType =
  | "sale_cash" | "sale_credit" | "receivable_collection"
  | "purchase_cash" | "purchase_credit" | "payable_payment" | "operating_expense"
  | "loan_received" | "loan_principal_repayment" | "loan_interest_fee_payment"
  | "owner_withdrawal" | "owner_contribution";

export type Transaction = {
  id: string;
  txn_type: TxnType;
  amount: string;
  value_date: string;
  settlement_date: string | null;
  category: string | null;
  note: string | null;
  supplier: { id: string; display_name: string } | null;
  debt_facility_id: string | null;
  season_id: string | null;
  season_cost_item_id: string | null;
  document_id: string | null;
  entry_method: string;
  evidence_state: "declared" | "document_attached";
  status: "confirmed" | "voided";
  duplicate_confirmed: boolean;
  void_reason: string | null;
  voided_at: string | null;
  created_at: string;
};

export type Supplier = {
  id: string;
  display_name: string;
  goods_supplied: string | null;
  district: string | null;
  upazila: string | null;
  declared_purchase_share_pct: string | null;
  is_active: boolean;
};

export type LenderType = "bank" | "mfi" | "ngo" | "samity" | "mohajon" | "supplier_credit" | "dealer_credit" | "other";
export type DebtFrequency = "weekly" | "monthly" | "single";

export type Debt = {
  id: string;
  lender_type: LenderType;
  lender_label: string;
  original_principal: string;
  outstanding_balance: string;
  outstanding_as_of: string;
  installment_amount: string | null;
  installment_frequency: DebtFrequency;
  next_due_date: string | null;
  is_overdue: boolean;
  overdue_amount: string;
  season_id: string | null;
  interest_fee_note: string | null;
  evidence_state: string;
  status: "active" | "closed";
  next_installments: { due_date: string; amount: string }[];
  dates_outdated: boolean;
  created_at: string;
};

export type DebtList = Page<Debt> & { no_debt_declared: boolean };

export type SeasonName = "aman" | "boro" | "aus" | "winter_vegetables" | "other";
export type AreaUnit = "acre" | "decimal" | "sq_ft" | "bigha";
export type IncomeRange = { low: string; expected: string; high: string };

export type Season = {
  id: string;
  crop_name: string;
  variety: string | null;
  season_name: SeasonName;
  season_label: string | null;
  area_value: string;
  area_unit: AreaUnit;
  decimals_per_bigha: string | null;
  area_acres: string;
  sowing_date: string;
  expected_harvest_date: string;
  output_unit: "kg";
  expected_output_low: string | null;
  expected_output_expected: string | null;
  expected_output_high: string | null;
  expected_price_low: string | null;
  expected_price_expected: string | null;
  expected_price_high: string | null;
  status: "planned" | "growing" | "harvested" | "closed";
  actual_harvest_date: string | null;
  actual_output: string | null;
  income_range: IncomeRange | null;
  created_at: string;
};

export type CostItem = {
  id: string;
  season_id: string;
  category: string;
  item_name: string;
  quantity: string;
  unit: string;
  unit_cost: string;
  total_cost: string;
  planned_date: string | null;
  price_source_type: string;
  price_source_note: string | null;
  paid_total: string;
};

export type SeasonDetail = Season & { cost_items: CostItem[] };

export type SeasonSummary = {
  season: Season;
  planned_cost_total: string;
  paid_cost_total: string;
  actual_sales_total: string;
  income_range: IncomeRange | null;
  break_even_price_per_kg: string | null;
  loan_cover_price_per_kg: string | null;
  loan_cover_basis: { financing_request_id: string; repayment_total: string } | null;
  labels: string[];
};

export type HorizonRow = { low: string; expected: string; known_debt_service: string };

export type Forecast = {
  id: string;
  status: "ok" | "insufficient_history";
  as_of_date: string;
  method_version: string;
  weeks_with_records: number;
  window_weeks: number;
  min_weeks_required: number;
  weekly: {
    net: { low: string; expected: string; high: string };
    collections_expected: string;
    payments_expected: string;
    purchases_expected: string;
  } | null;
  horizons: Record<string, HorizonRow>;
  weeks: { start: string; end: string; has_records: boolean; net: string | null }[];
  is_stale: boolean;
  disclaimer_key: string;
  created_at: string;
};

export type PriceSource = "supplier_quote" | "own_purchase_history" | "reference_market_price" | "public_listing" | "owner_estimate";
export type PurposeCategory = "inventory" | "farm_inputs" | "equipment" | "other";

export type FinancingItem = {
  id: string;
  item_name: string;
  quantity: string;
  unit: string;
  unit_price: string | null;
  line_total: string;
  price_source_type: PriceSource;
  price_date: string | null;
  price_source_note: string | null;
  ai_proposed: boolean;
  confirmed: boolean;
  source_season_cost_item_id: string | null;
};

export type Installment = { due_date: string; amount: string };

export type FinancingRequest = {
  id: string;
  season_id: string | null;
  status: string;
  requested_amount: string;
  purpose_text: string;
  purpose_category: PurposeCategory;
  desired_start_date: string | null;
  associated_expenses: string | null;
  liquidity_buffer: string | null;
  buffer_justification: string | null;
  cash_safely_available: string | null;
  committed_financing: string | null;
  current_cash_balance: string | null;
  minimum_cash_reserve: string | null;
  schedule_type: "equal_installments" | "single_payment" | null;
  installment_count: number | null;
  installment_frequency: "weekly" | "monthly" | null;
  first_due_date: string | null;
  interest_fees_total: string | null;
  interest_fees_unknown: boolean;
  over_request_explanation: string | null;
  items: FinancingItem[];
  preview: {
    items_total: string;
    funding_gap: string;
    request_minus_gap: string;
    gap_inputs_complete: boolean;
    installments: Installment[];
    repayment_total: string | null;
  };
  latest_assessment: { id: string; status: AssessmentStatus; is_stale: boolean; created_at: string } | null;
  created_at: string;
  updated_at: string;
};

export type AssessmentStatus = "insufficient_information" | "not_affordable_base_case" | "ready_for_lender_review";

export type DueCheck = {
  date: string; paid: string; new_installment: string; existing_paid: string;
  balance_after: string; shortfall_vs_reserve: string;
};

export type ShopResult = {
  kind: "shop_due_dates";
  start_balance: string; reserve: string; household_monthly: string; daily_net_low: string; household_daily: string;
  horizon_end: string; checks: DueCheck[]; first_shortfall: DueCheck | null;
  beyond_horizon: { installment_no: number; due_date: string; amount: string }[];
  min_balance_after_payment: string; any_shortfall: boolean;
};

export type CropResult = {
  kind: "crop_harvest";
  start_balance: string; reserve: string; expected_harvest_date: string; due_date: string; first_due_date: string;
  installments: number; output_low: string; price_low: string; remaining_costs_outside_request: string;
  total_planned_costs: string; debts_due_by_due_date: string; household_until_due: string;
  income_low: string; pre_harvest_balance: string; pre_harvest_shortfall: string; available_at_due_date: string;
  repayment_due: string; covered: boolean; surplus_or_shortfall: string;
  loan_cover_price_per_unit: string; break_even_price_per_unit: string;
};

export type ScenarioType = "supplier_delay" | "input_price_rise" | "harvest_price_fall" | "yield_shortfall";

export type ShopScenarioResult = {
  kind: "shop_due_dates"; any_shortfall: boolean; covered: boolean; checks_count: number;
  min_balance_after_payment: string;
  first_shortfall: { date: string; balance_after: string; shortfall_vs_reserve: string } | null;
};
export type CropScenarioResult = Omit<CropResult, "kind" | "start_balance" | "reserve" | "expected_harvest_date" |
  "due_date" | "first_due_date" | "installments" | "output_low" | "price_low" | "remaining_costs_outside_request" |
  "total_planned_costs" | "debts_due_by_due_date" | "household_until_due"> & { kind: "crop_harvest" };

/** What-if only (DEC-30): never changes the assessment status. */
export type Scenario = {
  id: string;
  scenario_type: ScenarioType;
  origin: "auto" | "news";
  status: "computed" | "proposed" | "dismissed";
  parameters: { days?: number; share?: string; start?: string; pct?: string; basis?: string };
  result: ShopScenarioResult | CropScenarioResult | null;
  news_event_id: string | null;
  supplier_name: string | null;
  assumption_key: string;
  label_key: string;
};

export type NewsSignal = {
  id: string;
  news_event_id: string;
  headline: string;
  headline_lang: "bn" | "en";
  summary: string | null;
  source_name: string;
  source_url: string | null;
  published_date: string;
  event_date: string | null;
  event_type: string;
  districts: string[];
  upazilas: string[];
  is_demo: boolean;
  source_count: number;
  corroboration: "single_source" | "corroborated";
  /** Collected by the daily news search, not checked by a person (SUG-45). Absent in older snapshots. */
  auto_collected?: boolean;
  match_reasons: ("location" | "supplier_location" | "sector" | "commodity")[];
  matched_supplier: string | null;
  proposed_scenario_id: string | null;
  scenario_status: Scenario["status"] | null;
};

export type Concentration = {
  window_days: number;
  window_start: string;
  window_end: string;
  basis: "linked_purchases" | "owner_reported" | "none";
  linked_purchase_count: number;
  total_purchases: string | null;
  suppliers: { supplier_id: string; display_name: string; amount: string | null; share_pct: string }[];
  top_share_pct: string | null;
  high_dependency: boolean;
  threshold_pct: string;
  note_key: string | null;
};

export type Assessment = {
  id: string;
  financing_request_id: string;
  activity_type: ActivityType;
  status: AssessmentStatus;
  as_of_date: string;
  engine_version: string;
  forecast_run_id: string | null;
  purpose_items_total: string | null;
  funding_gap: string | null;
  request_minus_gap: string | null;
  missing_items: string[];
  flags: string[];
  base_result: ShopResult | CropResult | Record<string, never>;
  explanation: {
    formulas: { key: string; expr: string; values: string }[];
    inputs: { name: string; value: string | number | boolean | null; source: string }[];
    proposal: {
      requested_amount: string;
      schedule_type: string | null; installment_count: number | null; frequency: string | null;
      first_due_date: string | null; last_due_date: string | null; interest_fees_total: string | null;
      interest_fees_unknown: boolean; repayment_total: string | null; installments: Installment[]; label: string;
    };
    parameters: Record<string, string | number>;
    excluded: string[];
  };
  scenarios: Scenario[];
  news_signals: NewsSignal[];
  inputs_sha256: string;
  is_stale: boolean;
  disclaimer_key: string;
  created_at: string;
};

export type Summary = {
  from: string;
  to: string;
  has_data: boolean;
  sales_recorded: string;
  cash_sales: string;
  credit_sales: string;
  operating_cash_in: string;
  operating_cash_out: string;
  net_operating_cash: string;
  receivables_outstanding: string;
  payables_outstanding: string;
  financing_received: string;
  principal_repaid: string;
  interest_fees_paid: string;
  owner_withdrawals: string;
  owner_contributions: string;
  cash_net_change: string;
  evidence_mix: { declared_pct: string; document_attached_pct: string };
  record_coverage: { weeks_with_records: number; window_weeks: number };
};

export type SectionKey = "profile_summary" | "money_summary" | "forecast" | "financing_request" | "obligations" |
  "supplier_risk" | "news_signals" | "season_summary" | "transaction_list";
export type ConsentStatus = "requested" | "approved" | "declined" | "revoked";
export type ReviewStatus = "under_review" | "info_requested" | "decision_recorded";
export type Decision = "proceed" | "decline" | "refer";

export type LenderCase = {
  consent_id: string;
  applicant: { display_name: string; activity_type: ActivityType; is_demo: boolean } | null;
  status: ConsentStatus;
  is_expired: boolean;
  valid_until: string | null;
  requested_sections: SectionKey[];
  created_at: string;
  assessment_status: AssessmentStatus | null;
  requested_amount: string | null;
  review_status: ReviewStatus | null;
  decision: Decision | null;
  last_read_at: string | null;
};

/** Owner view of one lender request / share (SCR-O14). */
export type ConsentRow = {
  id: string;
  status: ConsentStatus;
  is_expired: boolean;
  lender_organization: { name: string; is_demo: boolean };
  requested_by: string | null;
  requested_sections: SectionKey[];
  request_message: string | null;
  approved_sections: SectionKey[] | null;
  financing_request_id: string | null;
  valid_until: string | null;
  created_at: string;
  latest_report: { version: number; snapshot_sha256: string; created_at: string } | null;
  read_count: number;
  open_info_requests: number;
  review_status: ReviewStatus | null;
  decision: { decision: Decision; reason: string; at: string } | null;
};

export type ConsentList = Page<ConsentRow> & {
  allowed_sections: SectionKey[];
  required_sections: SectionKey[];
  valid_days: number[];
};

export type ConsentActivity = {
  reads: { at: string; organization: string }[];
  info_requests: { at: string; body: string }[];
  decision: { decision: Decision; reason: string; at: string; organization: string } | null;
};

export type ReviewEvent = {
  id: string; event_type: "status_change" | "note" | "info_request" | "decision"; body: string;
  visible_to_owner: boolean; officer: string | null; at: string;
};

/** Immutable shared report (bb-report-v1). Only approved sections exist. */
export type Snapshot = {
  schema: string;
  generated_at: string;
  as_of_date: string;
  is_demo: boolean;
  sections: Partial<Record<SectionKey, unknown>>;
};

export type CaseFile = {
  consent: { id: string; approved_sections: SectionKey[]; valid_until: string; approved_at: string; version: number;
             snapshot_sha256: string; shared_at: string; hash_verified: boolean };
  organization: { name: string; is_demo: boolean };
  snapshot: Snapshot;
  review: { status: ReviewStatus; decision: Decision | null; decision_reason: string | null; decided_by: string | null;
            decided_at: string | null; events: ReviewEvent[] } | null;
  cib_notice_key: string;
  banner_key: string | null;
};

export type Page<T> = { items: T[]; total: number };
