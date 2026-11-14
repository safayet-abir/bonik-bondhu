// Business dates are Bangladesh calendar dates (TRD §11), regardless of the
// device's own timezone.
import type { Lang } from "../i18n";

const ISO_DHAKA = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Dhaka" });

/** Today in Asia/Dhaka as YYYY-MM-DD. */
export function todayDhaka(): string {
  return ISO_DHAKA.format(new Date());
}

/** Shift a YYYY-MM-DD date by whole days (calendar arithmetic in UTC). */
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function firstOfMonth(iso: string): string {
  return `${iso.slice(0, 8)}01`;
}

/** "10 Nov 2026" / "১০ নভে, ২০২৬". */
export function formatDate(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === "bn" ? "bn-BD" : "en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  }).format(new Date(`${iso}T00:00:00Z`));
}
