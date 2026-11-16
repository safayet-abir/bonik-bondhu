import { Globe2, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import type { EconomyContext, EconomyWhatIf } from "../api/types";
import type { Lang } from "../i18n";
import { formatDate } from "../lib/dates";
import { formatNumber, formatTaka, toBanglaDigits } from "../lib/format";
import { useActiveProfile } from "../state/ActiveProfile";
import { Card } from "./Card";

// A year is not an amount: no thousands separator ("2025", not "2,025")
const year = (y: number, lang: Lang) => (lang === "bn" ? toBanglaDigits(String(y)) : String(y));

/** World Bank yearly figures for Bangladesh (SUG-58). Public data — same for owner and lender. */
export function EconomyFigures({ ctx }: { ctx: EconomyContext }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  return (
    <div className="flex flex-col gap-2">
      <dl className="divide-y divide-bb-border">
        {ctx.indicators.map((i) => (
          <div key={i.code} className="flex items-baseline justify-between gap-3 py-2">
            <dt>{t(`eco.key.${i.key}`)}</dt>
            <dd className="shrink-0 text-right">
              <span className="tabular font-semibold">{formatNumber(i.value, lang)}%</span>
              <span className="ml-2 text-caption text-bb-muted">{year(i.year, lang)}</span>
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-small text-bb-muted">
        {t("eco.note")}{" "}
        <a href={ctx.source.url} target="_blank" rel="noopener noreferrer" className="text-bb-primary underline">
          {t("eco.source")}
        </a>
      </p>
    </div>
  );
}

/** Home card for the owner. */
export function EconomyCard() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const [ctx, setCtx] = useState<EconomyContext | null>(null);
  useEffect(() => {
    api<EconomyContext>(`/profiles/${p.id}/economy-context`).then(setCtx).catch(() => setCtx(null));
  }, [p.id]);
  if (!ctx) return null;
  return (
    <Card className="flex flex-col gap-2">
      <p className="flex items-center gap-2 font-semibold"><Globe2 aria-hidden className="size-5 text-bb-primary" />{t("eco.title")}</p>
      <EconomyFigures ctx={ctx} />
    </Card>
  );
}

/** Risks tab: what if prices keep rising at last year's inflation? What-if only (DEC-30). */
export function InflationWhatIf({ rid }: { rid: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const [w, setW] = useState<EconomyWhatIf["whatif"]>(null);
  useEffect(() => {
    api<EconomyWhatIf>(`/profiles/${p.id}/financing-requests/${rid}/economy-whatif`)
      .then((r) => setW(r.whatif)).catch(() => setW(null));
  }, [p.id, rid]);
  if (!w) return null;
  const shop = w.result.kind === "shop_due_dates";
  const fs = w.result.first_shortfall;
  return (
    <Card className="flex flex-col gap-2">
      <p className="flex items-start gap-2 font-semibold">
        <TrendingUp aria-hidden className="mt-1 size-5 shrink-0 text-bb-warning" />
        <span>{t("eco.whatif_title", { infl: formatNumber(w.inflation_pct, lang), year: year(w.inflation_year, lang) })}</span>
      </p>
      <span className="self-start rounded-full bg-bb-primary-soft px-2 text-caption text-bb-primary">{t("eco.from_wb")}</span>
      <p className="text-small text-bb-muted">
        {t(shop ? "eco.whatif_shop" : "eco.whatif_farm", { pct: formatNumber(w.price_rise_pct, lang), days: formatNumber(String(w.days), lang) })}
      </p>
      {w.result.covered ? (
        <p className="font-semibold text-bb-success">{t("eco.ok")}</p>
      ) : shop && fs ? (
        <p className="font-semibold text-bb-danger">
          {t("eco.short_shop", { date: formatDate(fs.date, lang), amount: formatTaka(fs.shortfall_vs_reserve, lang) })}
        </p>
      ) : (
        <p className="font-semibold text-bb-danger">
          {t("eco.short_farm", { amount: formatTaka((-Number(w.result.surplus_or_shortfall ?? 0)).toFixed(2), lang) })}
        </p>
      )}
    </Card>
  );
}
