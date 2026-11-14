import { FileText, Info } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api } from "../../api/client";
import type { Summary as SummaryT } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { addDays, firstOfMonth, todayDhaka } from "../../lib/dates";
import { formatTaka, toBanglaDigits } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

type Period = "this_week" | "this_month" | "last_8_weeks";

function range(period: Period): { from: string; to: string } {
  const to = todayDhaka();
  if (period === "this_week") return { from: addDays(to, -6), to };
  if (period === "last_8_weeks") return { from: addDays(to, -55), to };
  return { from: firstOfMonth(to), to };
}

// Rows in the order of UI spec SCR-O07; `indent` = part of the row above.
const ROWS: { key: keyof SummaryT; indent?: boolean; tone?: "in" | "out" | "net" }[] = [
  { key: "sales_recorded" },
  { key: "cash_sales", indent: true },
  { key: "credit_sales", indent: true },
  { key: "operating_cash_in", tone: "in" },
  { key: "operating_cash_out", tone: "out" },
  { key: "net_operating_cash", tone: "net" },
  { key: "receivables_outstanding" },
  { key: "payables_outstanding" },
  { key: "financing_received" },
  { key: "principal_repaid" },
  { key: "interest_fees_paid" },
  { key: "owner_withdrawals" },
  { key: "owner_contributions" },
];

/** SCR-O07 Money summary (FR-LED-08/09). Every number comes from the server. */
export function Summary() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [period, setPeriod] = useState<Period>("this_month");
  const [data, setData] = useState<SummaryT | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [showHow, setShowHow] = useState(false);

  useEffect(() => {
    const { from, to } = range(period);
    setData(null);
    api<SummaryT>(`/profiles/${p.id}/summary?from=${from}&to=${to}`).then(setData).catch(setError);
  }, [p.id, period]);

  const periods: Period[] = ["this_week", "this_month", "last_8_weeks"];
  const num = (n: number) => (lang === "bn" ? toBanglaDigits(String(n)) : String(n));

  return (
    <PageShell title={t("summary.title")}>
      <div role="group" aria-label={t("summary.period")} className="flex flex-wrap gap-2">
        {periods.map((pd) => (
          <button key={pd} type="button" aria-pressed={period === pd} onClick={() => setPeriod(pd)}
                  className={`min-h-12 rounded-full border px-4 ${
                    period === pd ? "border-bb-primary bg-bb-primary-soft font-semibold text-bb-primary" : "border-bb-border bg-bb-surface"
                  }`}>
            {t(`period.${pd}`)}
          </button>
        ))}
      </div>
      <ErrorBanner error={error} />
      {!data && !error ? <Loading /> : null}
      {data && !data.has_data ? (
        <EmptyState icon={<FileText className="size-10" />} message={t("summary.empty")}
                    action={<Button onClick={() => navigate(`/p/${p.id}/entries/new`)}>{t("entry.new")}</Button>} />
      ) : null}
      {data && data.has_data ? (
        <>
          <Card className="divide-y divide-bb-border p-0">
            {ROWS.map(({ key, indent, tone }) => (
              <div key={key} className={`flex justify-between gap-3 px-4 py-2 ${indent ? "pl-8 text-small text-bb-muted" : ""} ${
                tone === "net" ? "bg-bb-primary-soft font-semibold" : ""}`}>
                <span>{t(`summary.${key}`)}</span>
                <span className={`tabular ${tone === "in" ? "text-bb-success" : ""}`}>
                  {formatTaka(data[key] as string, lang)}
                </span>
              </div>
            ))}
          </Card>
          <p className="text-small text-bb-muted">
            {t("summary.coverage", {
              have: num(data.record_coverage.weeks_with_records),
              window: num(data.record_coverage.window_weeks),
            })}
          </p>
          <button type="button" onClick={() => setShowHow((v) => !v)} aria-expanded={showHow}
                  className="flex min-h-12 items-center gap-2 font-semibold text-bb-primary">
            <Info aria-hidden className="size-5" />
            {t("common.how_calculated")}
          </button>
          {showHow ? (
            <Card className="flex flex-col gap-1 text-small">
              <p>{t("rule.loan_received")}</p>
              <p>{t("rule.credit_sale")}</p>
              <p>{t("rule.principal")}</p>
              <p>{t("summary.how_net")}</p>
            </Card>
          ) : null}
        </>
      ) : null}
    </PageShell>
  );
}
