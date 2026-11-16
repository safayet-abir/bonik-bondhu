import { AlertTriangle, ChevronRight, Pencil, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { api } from "../../api/client";
import type { Assessment as AssessmentT, CropResult, ShopResult } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Chips } from "../../components/Chips";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { STATUS_KEY, STATUS_TONE, fixLink } from "../../lib/financing";
import { Balance } from "../../components/Balance";
import { formatAmount, formatNumber, formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";
import { NewsTab, RisksTab } from "./AssessmentRisks";

type Tab = "result" | "risks" | "news" | "how";

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex justify-between gap-3 px-4 py-2">
      <span className={strong ? "font-semibold" : ""}>{label}</span>
      <span className={`tabular text-right ${strong ? "font-semibold" : ""}`}>{value}</span>
    </div>
  );
}

function ShopBlock({ r, lang }: { r: ShopResult; lang: Lang }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      {r.first_shortfall ? (
        <p className="font-semibold text-bb-danger">
          {t("asm.shortfall_on", {
            date: formatDate(r.first_shortfall.date, lang),
            amount: formatAmount(r.first_shortfall.shortfall_vs_reserve, lang),
          })}
        </p>
      ) : (
        <p>{t("asm.covers_every_date")}</p>
      )}
      <Card className="divide-y divide-bb-border p-0">
        <Row label={t("asm.start_balance")} value={formatTaka(r.start_balance, lang)} />
        <Row label={t("asm.reserve")} value={formatTaka(r.reserve, lang)} />
        <Row label={t("asm.dates_checked")} value={formatNumber(String(r.checks.length), lang)} />
        <Row label={t("asm.lowest_balance")} value={formatTaka(r.min_balance_after_payment, lang)} strong />
      </Card>
      <button type="button" aria-expanded={open} onClick={() => setOpen((v) => !v)}
              className="flex min-h-12 items-center gap-2 font-semibold text-bb-primary">
        <ChevronRight aria-hidden className={`size-5 ${open ? "rotate-90" : ""}`} />{t("asm.show_dates")}
      </button>
      {open ? (
        <Card className="p-0">
          <table className="w-full text-small">
            <thead>
              <tr className="border-b border-bb-border text-bb-muted">
                <th className="px-3 py-2 text-left font-normal">{t("asm.col_date")}</th>
                <th className="px-3 py-2 text-right font-normal">{t("asm.col_paid")}</th>
                <th className="px-3 py-2 text-right font-normal">{t("asm.col_balance")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bb-border">
              {r.checks.map((c) => {
                const short = Number(c.shortfall_vs_reserve) > 0;
                return (
                  <tr key={c.date} className={short ? "text-bb-danger" : ""}>
                    <td className="px-3 py-2">{formatDate(c.date, lang)}</td>
                    <td className="tabular px-3 py-2 text-right">{formatTaka(c.paid, lang)}</td>
                    <td className="tabular px-3 py-2 text-right">
                      {short ? <AlertTriangle aria-label={t("asm.short")} className="mr-1 inline size-4" /> : null}
                      {formatTaka(c.balance_after, lang)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      ) : null}
    </>
  );
}

function CropBlock({ r, lang }: { r: CropResult; lang: Lang }) {
  const { t } = useTranslation();
  const perKg = (v: string) => t("season.per_kg", { amount: formatTaka(v, lang) });
  return (
    <>
      <p className={r.covered ? "" : "font-semibold text-bb-danger"}>
        {r.covered ? t("asm.crop_covered", { date: formatDate(r.due_date, lang) })
          : t("asm.crop_short", { amount: formatAmount(r.surplus_or_shortfall.replace("-", ""), lang) })}
      </p>
      {Number(r.pre_harvest_shortfall) > 0 ? (
        <StatusBanner tone="warning" title={t("flag.pre_harvest_cash_shortfall")}>
          {formatTaka(r.pre_harvest_shortfall, lang)}
        </StatusBanner>
      ) : null}
      <Card className="divide-y divide-bb-border p-0">
        <Row label={t("asm.income_low")} value={formatTaka(r.income_low, lang)} />
        <Row label={t("asm.remaining_costs")} value={formatTaka(r.remaining_costs_outside_request, lang)} />
        <Row label={t("asm.debts_due")} value={formatTaka(r.debts_due_by_due_date, lang)} />
        <Row label={t("asm.reserve")} value={formatTaka(r.reserve, lang)} />
        <Row label={t("asm.available_at_due")} value={formatTaka(r.available_at_due_date, lang)} strong />
        <Row label={t("asm.repayment")} value={formatTaka(r.repayment_due, lang)} />
        <Row label={t("season.break_even")} value={perKg(r.break_even_price_per_unit)} />
        <Row label={t("season.loan_cover_title")} value={perKg(r.loan_cover_price_per_unit)} strong />
      </Card>
      <p className="text-small text-bb-muted">{t("season.loan_cover")}</p>
    </>
  );
}

function HowTab({ a, lang }: { a: AssessmentT; lang: Lang }) {
  const { t } = useTranslation();
  const e = a.explanation;
  return (
    <>
      <Card className="flex flex-col gap-3">
        <p className="font-semibold">{t("how.formulas")}</p>
        {e.formulas.map((f) => (
          <div key={f.key} className="flex flex-col gap-1 border-l-2 border-bb-primary pl-3">
            <span className="font-semibold">{t(f.key)}</span>
            <code className="text-small break-words text-bb-muted">{f.expr}</code>
            <code className="tabular text-small break-words">{f.values}</code>
          </div>
        ))}
      </Card>
      <Card className="flex flex-col gap-2">
        <p className="font-semibold">{t("how.inputs")}</p>
        {e.inputs.map((i) => (
          <div key={i.name} className="flex items-start justify-between gap-3 text-small">
            <span>{t(`how.input.${i.name}`)}</span>
            <span className="flex flex-col items-end">
              <span className="tabular">
                {i.value === null ? "—" : typeof i.value === "string" && /^-?\d+\.\d{2}$/.test(i.value)
                  ? formatTaka(i.value, lang) : formatNumber(String(i.value), lang)}
              </span>
              <span className="rounded-full bg-bb-primary-soft px-2 text-caption text-bb-primary">
                {t(`how.source.${i.source.split(":")[0]}`)}{i.source.includes(":")
                  ? ` · ${i.source.split(":")[1].split(",").map((s) => t(`price_source.${s}`)).join(", ")}` : ""}
              </span>
            </span>
          </div>
        ))}
      </Card>
      <Card className="flex flex-col gap-1 text-small">
        <p className="font-semibold">{t("how.assumptions")}</p>
        <p>{t("how.low_case")}</p>
        <p>{t("how.window", { weeks: formatNumber(String(e.parameters.forecast_window_weeks), lang),
                              days: formatNumber(String(e.parameters.horizon_days), lang) })}</p>
        <p>{t("how.excluded")}</p>
        <p>{t("how.engine", { v: a.engine_version, date: formatDate(a.as_of_date, lang) })}</p>
        <p className="break-all text-caption text-bb-muted">{t("how.hash")}: {a.inputs_sha256}</p>
      </Card>
    </>
  );
}

/** SCR-O12 Assessment result (FR-ASM-01..09) with Risks (FR-SCN) and News
 *  (FR-NEWS) tabs. Never approval language: the lender decides. */
export function Assessment() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const navigate = useNavigate();
  const { aid } = useParams();
  const [a, setA] = useState<AssessmentT | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tab, setTab] = useState<Tab>("result");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<AssessmentT>(`/profiles/${p.id}/assessments/${aid}`).then(setA).catch(setError);
  }, [p.id, aid]);
  useEffect(() => {
    setA(null);
    load();
  }, [load]);

  const base = `/p/${p.id}`;
  if (!a) return <PageShell back={`${base}/financing`}><ErrorBanner error={error} />{error ? null : <Loading />}</PageShell>;
  const rid = a.financing_request_id;

  async function rerun() {
    setBusy(true);
    try {
      const fresh = await api<AssessmentT>(`/profiles/${p.id}/financing-requests/${rid}/assessments`, { method: "POST" });
      void navigate(`${base}/assessment/${fresh.id}`, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const proposal = a.explanation.proposal;
  const result = a.base_result;
  return (
    <PageShell title={t("asm.title")} back={`${base}/financing`}>
      <ErrorBanner error={error} />
      {a.is_stale ? (
        <StatusBanner tone="warning" title={t("asm.stale")}>
          <Button variant="secondary" busy={busy} icon={<RefreshCw aria-hidden className="size-4" />} onClick={() => void rerun()}>
            {t("asm.check_again")}
          </Button>
        </StatusBanner>
      ) : null}
      <Chips label={t("asm.title")} value={tab} onChange={setTab}
             options={[{ value: "result", label: t("asm.tab_result") },
                       { value: "risks", label: t("asm.tab_risks") },
                       { value: "news", label: a.news_signals.length
                         ? `${t("asm.tab_news")} (${formatNumber(String(a.news_signals.length), lang)})` : t("asm.tab_news") },
                       { value: "how", label: t("asm.tab_how") }]} />

      {tab === "how" ? <HowTab a={a} lang={lang} /> : tab === "risks" ? <RisksTab a={a} lang={lang} />
        : tab === "news" ? <NewsTab a={a} lang={lang} profileId={p.id} onChanged={load} /> : (
        <>
          {/* the result weighed on the shop's balance: cash side down = fits, payment side down = does not */}
          <div className="rounded-bb bg-bb-wall px-10 pt-3">
            <Balance className="mx-auto max-w-[280px]" label={t(STATUS_KEY[a.status])} settleFrom={0}
                     left={a.status === "ready_for_lender_review" ? 14 : 10}
                     right={a.status === "not_affordable_base_case" ? 14 : 10} unit={4} />
          </div>
          <StatusBanner tone={STATUS_TONE[a.status]} title={t(STATUS_KEY[a.status])}>{t("asm.not_approval")}</StatusBanner>

          {a.missing_items.length > 0 ? (
            <Card className="flex flex-col gap-1">
              <p className="font-semibold">{t("asm.missing_title")}</p>
              <ul className="flex flex-col">
                {a.missing_items.map((m) => (
                  <li key={m}>
                    <Link to={fixLink(m, base, rid)} className="flex min-h-12 items-center gap-2 text-bb-primary">
                      <ChevronRight aria-hidden className="size-4 shrink-0" />
                      <span className="underline">{t(`missing.${m}`)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {a.funding_gap !== null ? (
            <Card className="divide-y divide-bb-border p-0">
              <Row label={t("fin.gap")} value={formatTaka(a.funding_gap, lang)} strong />
              <Row label={t("fin.you_asked")} value={formatTaka(proposal.requested_amount, lang)} />
              <Row label={t("fin.difference")} value={formatTaka(a.request_minus_gap ?? "0", lang)} />
              {Number(a.request_minus_gap) > 0 ? (
                <div className="px-4 py-2">
                  <Link to={`${base}/financing/${rid}/step/3`} className="flex min-h-12 items-center gap-2 font-semibold text-bb-primary">
                    <Pencil aria-hidden className="size-4" />{t("fin.explain")}
                  </Link>
                </div>
              ) : null}
            </Card>
          ) : null}

          {"kind" in result && result.kind === "shop_due_dates" ? <ShopBlock r={result} lang={lang} /> : null}
          {"kind" in result && result.kind === "crop_harvest" ? <CropBlock r={result} lang={lang} /> : null}
          {a.status === "not_affordable_base_case" ? (
            <Card className="text-small"><p className="font-semibold">{t("asm.suggest_title")}</p><p>{t("asm.suggest")}</p></Card>
          ) : null}

          {a.flags.length > 0 ? (
            <Card className="flex flex-col gap-2">
              <p className="font-semibold">{t("asm.flags")}</p>
              {a.flags.map((f) => (
                <p key={f} className="flex gap-2 text-small">
                  <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-bb-warning" />{t(`flag.${f}`)}
                </p>
              ))}
            </Card>
          ) : null}

          {proposal.repayment_total ? (
            <Card className="flex flex-col gap-1 text-small">
              <p className="font-semibold">{t("fin.proposal_banner")}</p>
              <p>
                {proposal.schedule_type === "single_payment"
                  ? t("asm.proposal_single", { amount: formatTaka(proposal.repayment_total, lang),
                                               date: formatDate(proposal.first_due_date!, lang) })
                  : t("asm.proposal_equal", { n: formatNumber(String(proposal.installment_count), lang),
                                              freq: t(`debt.freq.${proposal.frequency}`),
                                              total: formatTaka(proposal.repayment_total, lang) })}
              </p>
              {proposal.interest_fees_unknown ? <p className="text-bb-warning">{t("flag.interest_fees_unknown")}</p> : null}
            </Card>
          ) : null}
          <Link to={`${base}/financing/${rid}/step/1`} className="text-center font-semibold text-bb-primary underline">
            {t("asm.edit_request")}
          </Link>
        </>
      )}
    </PageShell>
  );
}
