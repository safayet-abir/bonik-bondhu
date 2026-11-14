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

export type TxnType = "sale_cash" | "operating_expense";

export type Transaction = {
  id: string;
  txn_type: string;
  amount: string;
  value_date: string;
  category: string | null;
  note: string | null;
  entry_method: string;
  evidence_state: "declared" | "document_attached";
  status: "confirmed" | "voided";
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

export type LenderCase = {
  consent_id: string;
  applicant: { display_name: string; activity_type: ActivityType; is_demo: boolean } | null;
  status: string;
  is_expired: boolean;
  valid_until: string | null;
};

export type Page<T> = { items: T[]; total: number };
