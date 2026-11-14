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
  labels: string[];
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

export type LenderCase = {
  consent_id: string;
  applicant: { display_name: string; activity_type: ActivityType; is_demo: boolean } | null;
  status: string;
  is_expired: boolean;
  valid_until: string | null;
};

export type Page<T> = { items: T[]; total: number };
