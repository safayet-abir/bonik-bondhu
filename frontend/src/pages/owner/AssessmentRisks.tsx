import { AlertTriangle, CheckCircle2, ExternalLink, FlaskConical, MapPin, Newspaper, XCircle } from "lucide-react";
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../../api/client";
import type { Assessment, NewsSignal, Scenario } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { DemoBadge } from "../../components/DemoBadge";
import { EmptyState } from "../../components/EmptyState";
import { ErrorBanner } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatAmount, formatNumber, formatTaka } from "../../lib/format";

/** "0.6500" -> "65", "0.15" -> "15" (display only). */
function pctOf(fraction: string | undefined, lang: Lang): string {
  return formatNumber(String(Math.round(Number(fraction ?? 0) * 1000) / 10), lang);
}

export function scenarioTitle(s: Scenario, t: TFunction, lang: Lang): string {
  return t(s.assumption_key, {
    supplier: s.supplier_name ?? t("scn.main_supplier"),
    days: formatNumber(String(s.parameters.days ?? ""), lang),
    pct: pctOf(s.parameters.pct, lang),
  });
}

function Assumption({ s, lang }: { s: Scenario; lang: Lang }) {
  const { t } = useTranslation();
  const share = pctOf(s.parameters.share, lang);
  const pct = pctOf(s.parameters.pct, lang);
  const days = formatNumber(String(s.parameters.days ?? ""), lang);
  const key = {
    supplier_delay: "scn.delay_detail", input_price_rise: s.parameters.share ? "scn.price_detail" : "scn.input_cost_detail",
    harvest_price_fall: "scn.harvest_price_detail", yield_shortfall: "scn.yield_detail",
  }[s.scenario_type];
  return (
    <p className="text-small text-bb-muted">
      {t(key, { share, pct, days, date: s.parameters.start ? formatDate(s.parameters.start, lang) : "" })}
      {s.parameters.basis === "owner_reported" ? ` ${t("scn.basis_owner")}` : ""}
    </p>
  );
}

function ResultLine({ s, lang }: { s: Scenario; lang: Lang }) {
  const { t } = useTranslation();
  const r = s.result;
  if (!r) return null;
  if (r.kind === "shop_due_dates") {
    return r.first_shortfall ? (
      <div className="flex flex-col gap-1">
        <p className="flex gap-2 font-semibold text-bb-danger">
          <AlertTriangle aria-hidden className="mt-1 size-4 shrink-0" />
          {t("asm.shortfall_on", { date: formatDate(r.first_shortfall.date, lang),
                                   amount: formatAmount(r.first_shortfall.shortfall_vs_reserve, lang) })}
        </p>
        <p className="text-small">{t("asm.lowest_balance")}: {formatTaka(r.min_balance_after_payment, lang)}</p>
      </div>
    ) : (
      <p className="flex gap-2 text-bb-success">
        <CheckCircle2 aria-hidden className="mt-1 size-4 shrink-0" />{t("scn.covered")}
      </p>
    );
  }
  const short = Number(r.pre_harvest_shortfall) > 0;
  return (
    <div className="flex flex-col gap-1">
      {r.covered ? (
        <p className="flex gap-2 text-bb-success">
          <CheckCircle2 aria-hidden className="mt-1 size-4 shrink-0" />
          {t("scn.crop_covered", { amount: formatTaka(r.surplus_or_shortfall, lang) })}
        </p>
      ) : (
        <p className="flex gap-2 font-semibold text-bb-danger">
          <AlertTriangle aria-hidden className="mt-1 size-4 shrink-0" />
          {t("asm.crop_short", { amount: formatAmount(r.surplus_or_shortfall.replace("-", ""), lang) })}
        </p>
      )}
      {short ? (
        <p className="flex gap-2 font-semibold text-bb-warning">
          <AlertTriangle aria-hidden className="mt-1 size-4 shrink-0" />
          {t("scn.pre_harvest_short", { amount: formatTaka(r.pre_harvest_shortfall, lang) })}
        </p>
      ) : null}
      <p className="text-small">{t("asm.available_at_due")}: {formatTaka(r.available_at_due_date, lang)}</p>
      <p className="text-small">{t("season.loan_cover_title")}: {t("season.per_kg", { amount: formatTaka(r.loan_cover_price_per_unit, lang) })}</p>
    </div>
  );
}

/** SCR-O12 Risks tab (FR-SCN-01..04): every scenario with its plain-words
 *  assumption next to the result. What-if only — never changes the status. */
export function RisksTab({ a, lang }: { a: Assessment; lang: Lang }) {
  const { t } = useTranslation();
  const shown = a.scenarios.filter((s) => s.status === "computed");
  if (shown.length === 0) {
    return <EmptyState icon={<FlaskConical className="size-10" />}
                       message={t(a.status === "insufficient_information" ? "scn.none_insufficient" : "scn.none")} />;
  }
  return (
    <>
      <p className="rounded-lg bg-bb-primary-soft px-3 py-2 text-small font-semibold text-bb-primary">{t("scn.whatif")}</p>
      {shown.map((s) => (
        <Card key={s.id} className="flex flex-col gap-2">
          <p className="flex items-start gap-2 font-semibold">
            <FlaskConical aria-hidden className="mt-1 size-5 shrink-0 text-bb-primary" />
            <span>{scenarioTitle(s, t, lang)}</span>
          </p>
          {s.origin === "news" ? (
            <span className="self-start rounded-full bg-bb-primary-soft px-2 text-caption text-bb-primary">{t("scn.from_news")}</span>
          ) : null}
          <Assumption s={s} lang={lang} />
          <ResultLine s={s} lang={lang} />
        </Card>
      ))}
      <p className="text-small text-bb-muted">{t("scn.severity_note")}</p>
    </>
  );
}

function NewsCard({ n, a, lang, profileId, onChanged }: {
  n: NewsSignal; a: Assessment; lang: Lang; profileId: string; onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<"confirm" | "dismiss" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const proposal = a.scenarios.find((s) => s.id === n.proposed_scenario_id);
  const place = [...n.upazilas, ...n.districts].join(", ") || t("news.national");

  async function run(kind: "confirm" | "dismiss") {
    if (!proposal) return;
    setBusy(kind);
    setError(null);
    try {
      await api(`/profiles/${profileId}/scenarios/${proposal.id}/${kind}`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="p-0">
    <article aria-label={n.headline} className="flex flex-col gap-2 p-4">
      <ErrorBanner error={error} />
      <div className="flex flex-wrap items-center gap-2">
        {n.is_demo ? <DemoBadge /> : null}
        <span className={`rounded-full px-2 text-caption font-semibold ${
          n.corroboration === "corroborated" ? "bg-bb-primary-soft text-bb-primary" : "bg-bb-bg text-bb-warning"}`}>
          {t(n.corroboration === "corroborated" ? "news.corroborated" : "news.single")}
        </span>
        {n.auto_collected ? <span className="rounded-full bg-bb-bg px-2 text-caption text-bb-muted">{t("news.auto")}</span> : null}
      </div>
      <p lang={n.headline_lang} className="flex items-start gap-2 font-semibold">
        <Newspaper aria-hidden className="mt-1 size-5 shrink-0 text-bb-primary" />{n.headline}
      </p>
      {n.summary ? <p className="text-small">{n.summary}</p> : null}
      <p className="text-small text-bb-muted">
        {t("news.reported_by", { source: n.source_name, date: formatDate(n.published_date, lang) })}
        {n.event_date && n.event_date !== n.published_date ? ` · ${t("news.event_on", { date: formatDate(n.event_date, lang) })}` : ""}
      </p>
      <p className="flex items-start gap-1 text-small"><MapPin aria-hidden className="mt-1 size-4 shrink-0" />{place}</p>
      <ul className="flex flex-col text-small">
        {n.match_reasons.map((r) => (
          <li key={r}>• {t(`news.reason.${r}`, { supplier: n.matched_supplier ?? "" })}</li>
        ))}
      </ul>
      {n.source_url ? (
        <a href={n.source_url} target="_blank" rel="noopener noreferrer"
           className="flex min-h-12 items-center gap-2 self-start font-semibold text-bb-primary underline">
          <ExternalLink aria-hidden className="size-4" />{t("news.open_source")}
        </a>
      ) : null}
      {proposal?.status === "proposed" ? (
        <>
          <p className="text-small">{t("news.proposal")}: {scenarioTitle(proposal, t, lang)}</p>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" busy={busy === "dismiss"} disabled={busy !== null}
                    icon={<XCircle aria-hidden className="size-4" />} onClick={() => void run("dismiss")}>
              {t("news.dismiss")}
            </Button>
            <Button busy={busy === "confirm"} disabled={busy !== null}
                    icon={<FlaskConical aria-hidden className="size-4" />} onClick={() => void run("confirm")}>
              {t("news.test")}
            </Button>
          </div>
        </>
      ) : proposal?.status === "computed" ? (
        <p className="text-small font-semibold text-bb-success">{t("news.tested")}</p>
      ) : proposal?.status === "dismissed" ? (
        <p className="text-small text-bb-muted">{t("news.dismissed")}</p>
      ) : (
        <p className="text-small text-bb-muted">{t("news.signal_only")}</p>
      )}
    </article>
    </Card>
  );
}

/** SCR-O12 News tab (FR-NEWS-02..06). Curated list only — never "live" news. */
export function NewsTab({ a, lang, profileId, onChanged }: {
  a: Assessment; lang: Lang; profileId: string; onChanged: () => void;
}) {
  const { t } = useTranslation();
  if (a.news_signals.length === 0) {
    return <EmptyState icon={<Newspaper className="size-10" />} message={t("news.none")} />;
  }
  return (
    <>
      <p className="text-small text-bb-muted">{t("news.curated_note")}</p>
      {a.news_signals.map((n) => (
        <NewsCard key={n.id} n={n} a={a} lang={lang} profileId={profileId} onChanged={onChanged} />
      ))}
    </>
  );
}
