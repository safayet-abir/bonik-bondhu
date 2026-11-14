import { AlertTriangle, CalendarClock, Info, NotebookText, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, ApiError } from "../../api/client";
import type { Forecast as ForecastT } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate, todayDhaka } from "../../lib/dates";
import { formatNumber, formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

const HORIZONS = ["7", "30", "60", "90"] as const;

/** Weekly net per block as CSS bars (the one simple visual on this screen).
 *  Missing weeks are drawn as gaps, never as zero (S1 F5). */
function WeekBars({ f, lang }: { f: ForecastT; lang: Lang }) {
  const { t } = useTranslation();
  const nets = f.weeks.map((w) => (w.net === null ? null : Number(w.net)));
  const max = Math.max(1, ...nets.map((n) => Math.abs(n ?? 0)));
  return (
    <Card className="flex flex-col gap-2">
      <p className="font-semibold">{t("forecast.weeks_title")}</p>
      <div className="flex h-24 items-end gap-1" aria-hidden>
        {nets.map((n, i) => (
          <div key={f.weeks[i].start} className="flex flex-1 flex-col items-center justify-end">
            {n === null ? (
              <div className="h-2 w-full rounded-sm border border-dashed border-bb-border" />
            ) : (
              <div className={`w-full rounded-sm ${n < 0 ? "bg-bb-danger" : "bg-bb-primary"}`}
                   style={{ height: `${Math.max(4, (Math.abs(n) / max) * 88)}px` }} />
            )}
          </div>
        ))}
      </div>
      <ul className="sr-only">
        {f.weeks.map((w) => (
          <li key={w.start}>{formatDate(w.start, lang)}: {w.net === null ? t("forecast.week_missing") : formatTaka(w.net, lang)}</li>
        ))}
      </ul>
      <p className="text-caption text-bb-muted">{t("forecast.weeks_note")}</p>
    </Card>
  );
}

/** SCR-O10 Forecast (shop only; FR-FC-01..06). A rolling average of the
 *  owner's own records — an estimate, never guaranteed income. */
export function Forecast() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [f, setF] = useState<ForecastT | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [showHow, setShowHow] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setF(await api<ForecastT>(`/profiles/${p.id}/forecasts`, { method: "POST" }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [p.id]);

  useEffect(() => {
    api<ForecastT>(`/profiles/${p.id}/forecasts/latest`)
      .then((latest) => (latest.is_stale || latest.as_of_date !== todayDhaka() ? refresh() : setF(latest)))
      .catch((err) => (err instanceof ApiError && err.status === 404 ? refresh() : setError(err)));
  }, [p.id, refresh]);

  const back = `/p/${p.id}/more`;
  if (!f) return <PageShell title={t("forecast.title")} back={back}><ErrorBanner error={error} />{error ? null : <Loading />}</PageShell>;

  const coverage = t("forecast.coverage", {
    have: formatNumber(String(f.weeks_with_records), lang), window: formatNumber(String(f.window_weeks), lang),
  });

  if (f.status === "insufficient_history") {
    const more = Math.max(1, f.min_weeks_required - f.weeks_with_records);
    return (
      <PageShell title={t("forecast.title")} back={back}>
        <Card className="flex flex-col items-center gap-3 py-6 text-center">
          <CalendarClock aria-hidden className="size-12 text-bb-primary" />
          <p className="text-card font-semibold">{t("forecast.record_more", { n: formatNumber(String(more), lang) })}</p>
          <p className="text-small text-bb-muted">
            {t("forecast.insufficient", {
              required: formatNumber(String(f.min_weeks_required), lang), have: formatNumber(String(f.weeks_with_records), lang),
            })}
          </p>
          <p className="text-small text-bb-muted">{coverage}</p>
        </Card>
        <Button full icon={<NotebookText aria-hidden className="size-5" />} onClick={() => navigate(`/p/${p.id}/entries/new`)}>
          {t("home.path_a")}
        </Button>
      </PageShell>
    );
  }

  const w = f.weekly!;
  return (
    <PageShell title={t("forecast.title")} back={back}>
      <ErrorBanner error={error} />
      <p className="text-small text-bb-muted">
        {t("forecast.made_on", { date: formatDate(f.as_of_date, lang) })} · {coverage}
      </p>
      <Card className="p-0">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-bb-border text-small text-bb-muted">
              <th className="px-3 py-2 font-normal">{t("forecast.period")}</th>
              <th className="px-3 py-2 text-right font-normal">{t("range.low")}</th>
              <th className="px-3 py-2 text-right font-normal">{t("range.expected")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bb-border">
            {HORIZONS.map((h) => (
              <tr key={h}>
                <td className="px-3 py-2">{t("forecast.days", { n: formatNumber(h, lang) })}</td>
                <td className="tabular px-3 py-2 text-right">{formatTaka(f.horizons[h].low, lang)}</td>
                <td className="tabular px-3 py-2 text-right font-semibold">{formatTaka(f.horizons[h].expected, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-small">
        {t("forecast.known_installments", { amount: formatTaka(f.horizons["30"].known_debt_service, lang) })}
      </p>
      <WeekBars f={f} lang={lang} />
      <StatusBanner tone="warning" title={t("forecast.estimate")} />
      {f.is_stale ? <StatusBanner tone="info" title={t("forecast.stale")} /> : null}
      <button type="button" onClick={() => setShowHow((v) => !v)} aria-expanded={showHow}
              className="flex min-h-12 items-center gap-2 font-semibold text-bb-primary">
        <Info aria-hidden className="size-5" />
        {t("common.how_calculated")}
      </button>
      {showHow ? (
        <Card className="flex flex-col gap-2 text-small">
          <p>{t("forecast.how_weeks", { window: formatNumber(String(f.window_weeks), lang) })}</p>
          <p>{t("forecast.how_net")}</p>
          <p>{t("forecast.how_cases", {
            low: formatTaka(w.net.low, lang), expected: formatTaka(w.net.expected, lang), high: formatTaka(w.net.high, lang),
          })}</p>
          <p>{t("forecast.how_parts", {
            coll: formatTaka(w.collections_expected, lang), pay: formatTaka(w.payments_expected, lang),
          })}</p>
          <p>{t("forecast.how_horizon")}</p>
          <p className="flex gap-2 text-bb-muted">
            <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0" />{t("forecast.how_excluded")}
          </p>
        </Card>
      ) : null}
      <Button variant="secondary" full busy={busy} icon={<RefreshCw aria-hidden className="size-5" />} onClick={() => void refresh()}>
        {t("forecast.update")}
      </Button>
    </PageShell>
  );
}
