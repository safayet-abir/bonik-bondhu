import { Info } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { api } from "../../api/client";
import type { SeasonSummary as SeasonSummaryT } from "../../api/types";
import { Card } from "../../components/Card";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";
import { seasonTitle } from "../owner/AddEntry";

/** SCR-F05 Season summary (FR-SEA-07). The loan-cover price appears once a
 *  complete financing request is linked to the season; everything here is
 *  the farmer's own estimate. */
export function SeasonSummary() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const { sid } = useParams();
  const [s, setS] = useState<SeasonSummaryT | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [showHow, setShowHow] = useState(false);

  useEffect(() => {
    api<SeasonSummaryT>(`/profiles/${p.id}/seasons/${sid}/summary`).then(setS).catch(setError);
  }, [p.id, sid]);

  const back = `/p/${p.id}/seasons/${sid}`;
  if (!s) return <PageShell back={back}><ErrorBanner error={error} />{error ? null : <Loading />}</PageShell>;
  const perKg = (v: string) => t("season.per_kg", { amount: formatTaka(v, lang) });

  return (
    <PageShell title={seasonTitle(s.season, t)} back={back}>
      <StatusBanner tone="info" title={t("season.estimates_note")} />
      <Card className="flex flex-col gap-1">
        <p className="font-semibold">{t("season.income_range")}</p>
        {s.income_range ? (
          <div className="grid grid-cols-3 gap-2 text-center">
            {(["low", "expected", "high"] as const).map((r) => (
              <div key={r} className="flex flex-col">
                <span className="text-caption text-bb-muted">{t(`range.${r}`)}</span>
                <span className="tabular font-semibold">{formatTaka(s.income_range![r], lang)}</span>
              </div>
            ))}
          </div>
        ) : <p className="text-small text-bb-muted">{t("season.income_missing")}</p>}
      </Card>
      <Card className="divide-y divide-bb-border p-0">
        {([
          ["season.planned_cost", formatTaka(s.planned_cost_total, lang)],
          ["season.paid_cost", formatTaka(s.paid_cost_total, lang)],
          ["season.sales", formatTaka(s.actual_sales_total, lang)],
          ["season.break_even", s.break_even_price_per_kg ? perKg(s.break_even_price_per_kg) : "—"],
        ] as const).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 px-4 py-2">
            <span>{t(k)}</span>
            <span className="tabular text-right">{v}</span>
          </div>
        ))}
      </Card>
      {s.loan_cover_price_per_kg ? (
        <Card className="flex flex-col gap-1">
          <div className="flex justify-between gap-3">
            <span className="font-semibold">{t("season.loan_cover_title")}</span>
            <span className="tabular font-semibold">{perKg(s.loan_cover_price_per_kg)}</span>
          </div>
          <p className="text-small text-bb-muted">{t("season.loan_cover_low")}</p>
          <p className="text-small">{t("season.loan_cover")}</p>
          {s.loan_cover_basis ? (
            <p className="text-caption text-bb-muted">
              {t("season.loan_cover_basis", { amount: formatTaka(s.loan_cover_basis.repayment_total, lang) })}
            </p>
          ) : null}
        </Card>
      ) : (
        <p className="text-small text-bb-muted">{t("season.loan_cover_later")}</p>
      )}
      <button type="button" onClick={() => setShowHow((v) => !v)} aria-expanded={showHow}
              className="flex min-h-12 items-center gap-2 font-semibold text-bb-primary">
        <Info aria-hidden className="size-5" />
        {t("common.how_calculated")}
      </button>
      {showHow ? (
        <Card className="flex flex-col gap-1 text-small">
          <p>{t("season.how_income")}</p>
          <p>{t("season.how_break_even")}</p>
          <p>{t("season.how_paid")}</p>
        </Card>
      ) : null}
    </PageShell>
  );
}
