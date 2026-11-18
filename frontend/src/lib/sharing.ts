// Shared helpers for consent (SCR-O14) and the lender portal (SCR-L01..L03).
import type { SectionKey } from "../api/types";

export const SECTION_ORDER: SectionKey[] = [
  "profile_summary", "money_summary", "forecast", "financing_request", "obligations", "supplier_risk",
  "news_signals", "season_summary", "transaction_list",
];

/** "7KQ2M9XA4P" -> "7KQ2M-9XA4P" (display only; dashes are ignored on input). */
export function formatShareCode(code: string): string {
  return code.length === 10 ? `${code.slice(0, 5)}-${code.slice(5)}` : code;
}

/** First 12 hex chars of a SHA-256 for display; the full hash is shown on demand. */
export function shortHash(h: string | null | undefined): string {
  return h ? `${h.slice(0, 12)}…` : "—";
}

export function sortSections(keys: SectionKey[]): SectionKey[] {
  return SECTION_ORDER.filter((k) => keys.includes(k));
}
