// Number display helpers (FR-I18N-04, UI spec §9).
// Display only — the server is the source of truth for every money value.
import type { Lang } from "../i18n";

const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

export function toBanglaDigits(s: string): string {
  return s.replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)]);
}

/** Bangla digits -> Latin, commas/spaces removed. "১৮,০০০" -> "18000". */
export function normalizeDigits(s: string): string {
  return s
    .replace(/[০-৯]/g, (d) => String(BN_DIGITS.indexOf(d)))
    .replace(/[,\s]/g, "");
}

/** South-Asian grouping: "150000.00" -> "1,50,000" (decimals kept if non-zero). */
export function groupSouthAsian(amount: string): string {
  const [intPart, frac = ""] = amount.replace(/^-/, "").split(".");
  const last3 = intPart.slice(-3);
  const rest = intPart.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  const grouped = rest ? `${rest},${last3}` : last3;
  const sign = amount.startsWith("-") ? "-" : "";
  const decimals = frac && /[1-9]/.test(frac) ? `.${frac.padEnd(2, "0").slice(0, 2)}` : "";
  return sign + grouped + decimals;
}

/** "150000.00" -> "Tk 1,50,000" (en) or "Tk ১,৫০,০০০" (bn). */
export function formatTaka(amount: string, lang: Lang): string {
  const g = groupSouthAsian(amount);
  return `Tk ${lang === "bn" ? toBanglaDigits(g) : g}`;
}
