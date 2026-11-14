// Shared helpers for the financing wizard (SCR-O11) and result (SCR-O12).
import type { AssessmentStatus, PriceSource, PurposeCategory } from "../api/types";

export const PURPOSE_CATEGORIES: PurposeCategory[] = ["inventory", "farm_inputs", "equipment", "other"];
export const PRICE_SOURCES: PriceSource[] = [
  "supplier_quote", "own_purchase_history", "reference_market_price", "public_listing", "owner_estimate",
];

/** "10000.00" -> "10000" for editing; null -> "". */
export function editable(v: string | null | undefined): string {
  if (!v) return "";
  return v.replace(/\.00$/, "");
}

/** Empty input clears the value on the server. */
export function orNull(v: string): string | null {
  return v.trim() === "" ? null : v;
}

export const STATUS_TONE: Record<AssessmentStatus, "success" | "danger" | "info"> = {
  ready_for_lender_review: "success",
  not_affordable_base_case: "danger",
  insufficient_information: "info",
};

export const STATUS_KEY: Record<AssessmentStatus, string> = {
  ready_for_lender_review: "asm.ready",
  not_affordable_base_case: "asm.not_affordable",
  insufficient_information: "asm.insufficient",
};

/** Where the owner fixes each missing item (FR-ASM-02 "fix-it actions"). */
export function fixLink(code: string, base: string, rid: string): string {
  const step = (n: number) => `${base}/financing/${rid}/step/${n}`;
  switch (code) {
    case "household_withdrawal_not_declared":
    case "profile_location_missing":
    case "season_incomplete":
      return step(1);
    case "purpose_items_missing":
      return step(2);
    case "gap_inputs_missing":
      return step(3);
    case "debts_not_declared":
      return step(4);
    case "forecast_insufficient_history":
      return `${base}/entries/new`;
    default:
      return step(5); // terms_incomplete, term_beyond_forecast_horizon, repayment_due_before_expected_harvest
  }
}
