/* eslint-disable @typescript-eslint/no-explicit-any -- the snapshot is a stored JSON document (bb-report-v1) */
import { AlertTriangle, ExternalLink, FileCheck2, Lock, MessageSquare, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { CaseFile as CaseFileT, Decision } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Chips } from "../../components/Chips";
import { DemoBadge } from "../../components/DemoBadge";
import { ErrorBanner, Loading } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { STATUS_KEY, STATUS_TONE } from "../../lib/financing";
import { formatNumber, formatTaka } from "../../lib/format";
import { LenderShell } from "./LenderShell";

type S = Record<string, any>;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="flex flex-col gap-2">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </Card>
  );
}

function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 text-small">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-bb-muted">{k}</dt>
          <dd className="tabular text-right">{v ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

function useFmt() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  return {
    t, lang,
    tk: (v: string | null | undefined) => (v == null ? "—" : formatTaka(v, lang)),
    num: (v: string | number | null | undefined) => (v == null ? "—" : formatNumber(String(v), lang)),
    day: (v: string | null | undefined) => (v ? formatDate(v.slice(0, 10), lang) : "—"),
  };
}

function scenarioKey(s: S): string {
  if (s.scenario_type === "input_price_rise") return s.parameters?.share ? "scn.price_rise" : "scn.input_cost";
  return { supplier_delay: "scn.delay", harvest_price_fall: "scn.harvest_price", yield_shortfall: "scn.yield" }[
    s.scenario_type as string] ?? "scn.whatif";
}

function FinancingSection({ fr }: { fr: S }) {
  const { t, tk, num, day } = useFmt();
  const a = fr.assessment as S;
  const b = (a.base_result ?? {}) as S;
  return (
    <Section title={t("section.financing_request")}>
      <StatusBanner tone={STATUS_TONE[a.status as keyof typeof STATUS_TONE]} title={t(STATUS_KEY[a.status as keyof typeof STATUS_KEY])}>
        {t("asm.not_approval")} · {t("lender.checked_on", { date: day(a.as_of_date) })}
      </StatusBanner>
      <KV rows={[
        [t("fin.you_asked"), tk(fr.requested_amount)], [t("fin.gap"), tk(fr.funding_gap)],
        [t("fin.difference"), tk(fr.request_minus_gap)], [t("lender.purpose"), fr.purpose_text],
      ]} />
      {fr.over_request_explanation ? <p className="text-small">“{fr.over_request_explanation}”</p> : null}
      {fr.items?.length ? (
        <table className="w-full text-small">
          <thead className="text-bb-muted"><tr><th className="text-left font-normal">{t("lender.item")}</th>
            <th className="text-right font-normal">{t("lender.qty")}</th><th className="text-right font-normal">{t("lender.total")}</th>
            <th className="text-left font-normal pl-2">{t("lender.price_source")}</th></tr></thead>
          <tbody>{fr.items.map((i: S, n: number) => (
            <tr key={n} className="border-t border-bb-border">
              <td>{i.item_name}</td><td className="tabular text-right">{num(i.quantity)} {i.unit}</td>
              <td className="tabular text-right">{tk(i.line_total)}</td>
              <td className="pl-2">{t(`price_source.${i.price_source_type}`)}{i.price_date ? ` · ${day(i.price_date)}` : ""}</td>
            </tr>))}</tbody>
        </table>
      ) : null}
      <div className="rounded-lg bg-bb-bg p-3 text-small">
        <p className="font-semibold">{t("fin.proposal_banner")}</p>
        <p>{fr.proposal.schedule_type === "single_payment"
          ? t("asm.proposal_single", { amount: tk(fr.proposal.repayment_total), date: day(fr.proposal.first_due_date) })
          : t("asm.proposal_equal", { n: num(fr.proposal.installment_count), freq: t(`debt.freq.${fr.proposal.frequency}`),
                                      total: tk(fr.proposal.repayment_total) })}</p>
        {fr.proposal.interest_fees_unknown ? <p className="text-bb-warning">{t("flag.interest_fees_unknown")}</p> : null}
      </div>
      {b.kind === "shop_due_dates" ? (
        <KV rows={[[t("asm.dates_checked"), num(b.checks?.length)], [t("asm.start_balance"), tk(b.start_balance)],
                   [t("asm.reserve"), tk(b.reserve)], [t("asm.lowest_balance"), tk(b.min_balance_after_payment)],
                   [t("lender.first_shortfall"), b.first_shortfall ? `${day(b.first_shortfall.date)} · ${tk(b.first_shortfall.shortfall_vs_reserve)}` : t("lender.none")]]} />
      ) : null}
      {b.kind === "crop_harvest" ? (
        <KV rows={[[t("asm.income_low"), tk(b.income_low)], [t("asm.available_at_due"), tk(b.available_at_due_date)],
                   [t("asm.repayment"), tk(b.repayment_due)], [t("season.break_even"), tk(b.break_even_price_per_unit)],
                   [t("season.loan_cover_title"), tk(b.loan_cover_price_per_unit)]]} />
      ) : null}
      {a.missing_items?.length ? <p className="text-small">{t("asm.missing_title")}: {a.missing_items.map((m: string) => t(`missing.${m}`)).join("; ")}</p> : null}
      {a.flags?.length ? (
        <ul className="flex flex-col gap-1 text-small">
          {a.flags.map((f: string) => <li key={f} className="flex gap-2"><AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-bb-warning" />{t(`flag.${f}`)}</li>)}
        </ul>
      ) : null}
      {a.scenarios?.length ? (
        <div className="flex flex-col gap-1 text-small">
          <p className="font-semibold">{t("asm.tab_risks")} — {t("scn.whatif")}</p>
          {a.scenarios.map((s: S, n: number) => (
            <p key={n}>
              • {t(scenarioKey(s), { supplier: s.supplier ?? t("scn.main_supplier"), days: num(s.parameters?.days),
                                     pct: num(Math.round(Number(s.parameters?.pct ?? 0) * 100)) })}:{" "}
              {s.result?.kind === "shop_due_dates"
                ? (s.result.first_shortfall ? t("lender.short_on", { date: day(s.result.first_shortfall.date), amount: tk(s.result.first_shortfall.shortfall_vs_reserve) }) : t("scn.covered"))
                : (s.result?.covered ? t("scn.crop_covered", { amount: tk(s.result.surplus_or_shortfall) }) : t("lender.not_covered"))}
            </p>
          ))}
        </div>
      ) : null}
      <p className="break-all text-caption text-bb-muted">{t("how.hash")}: {a.inputs_sha256}</p>
    </Section>
  );
}

function Sections({ s }: { s: S }) {
  const { t, tk, num, day } = useFmt();
  return (
    <>
      {s.profile_summary ? (
        <Section title={t("section.profile_summary")}>
          <KV rows={[[t("lender.name"), s.profile_summary.display_name], [t("lender.type"), t(`profile.type.${s.profile_summary.activity_type}`)],
                     [t("profile.category"), s.profile_summary.business_category],
                     [t("lender.location"), [s.profile_summary.upazila, s.profile_summary.district].filter(Boolean).join(", ")]]} />
        </Section>
      ) : null}
      {s.financing_request ? <FinancingSection fr={s.financing_request} /> : null}
      {s.money_summary ? (
        <Section title={t("section.money_summary")}>
          <p className="text-small text-bb-muted">{day(s.money_summary.period.from)} – {day(s.money_summary.period.to)}</p>
          <KV rows={[[t("summary.sales_recorded"), tk(s.money_summary.sales_recorded)],
                     [t("summary.net_operating_cash"), tk(s.money_summary.net_operating_cash)],
                     [t("summary.receivables_outstanding"), tk(s.money_summary.receivables_outstanding)],
                     [t("summary.payables_outstanding"), tk(s.money_summary.payables_outstanding)],
                     [t("lender.evidence_mix"), t("lender.evidence_value", { d: num(s.money_summary.evidence_mix?.declared_pct), a: num(s.money_summary.evidence_mix?.document_attached_pct) })],
                     [t("lender.coverage"), `${num(s.money_summary.record_coverage?.weeks_with_records)} / ${num(s.money_summary.record_coverage?.window_weeks)}`]]} />
        </Section>
      ) : null}
      {s.forecast ? (
        <Section title={t("section.forecast")}>
          {s.forecast.weekly_net ? (
            <KV rows={[[t("lender.weekly_low"), tk(s.forecast.weekly_net.low)], [t("lender.weekly_expected"), tk(s.forecast.weekly_net.expected)],
                       [t("lender.weekly_high"), tk(s.forecast.weekly_net.high)], [t("lender.coverage"), `${num(s.forecast.weeks_with_records)} / ${num(s.forecast.window_weeks)}`]]} />
          ) : <p className="text-small">{t("forecast.insufficient", { required: num(4), have: num(s.forecast.weeks_with_records) })}</p>}
          <p className="text-small text-bb-muted">{t("forecast.estimate")}</p>
        </Section>
      ) : null}
      {s.obligations ? (
        <Section title={t("section.obligations")}>
          {s.obligations.declared.length === 0
            ? <p className="text-small">{s.obligations.no_debt_declared ? t("lender.no_debt_declared") : t("lender.none")}</p>
            : s.obligations.declared.map((d: S, n: number) => (
              <p key={n} className="text-small">• {t(`lender_type.${d.lender_type}`)} — {d.lender_label}: {tk(d.outstanding_balance)}
                {d.installment_amount ? ` · ${tk(d.installment_amount)} ${t(`debt.freq.${d.installment_frequency}`)}` : ""}
                {d.next_due_date ? ` · ${day(d.next_due_date)}` : ""}{d.is_overdue ? ` · ${t("lender.overdue", { amount: tk(d.overdue_amount) })}` : ""}</p>))}
          <p className="text-small text-bb-muted">{t("lender.declared_by_owner")}</p>
          <p className="flex gap-2 rounded-lg bg-bb-bg p-2 text-small font-semibold"><ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0" />{t("debt.cib")}</p>
        </Section>
      ) : null}
      {s.supplier_risk ? (
        <Section title={t("section.supplier_risk")}>
          {s.supplier_risk.suppliers.map((x: S) => (
            <div key={x.label} className="flex flex-col gap-1 text-small">
              <div className="flex justify-between"><span>{x.label}</span><span className="tabular">{num(x.share_pct)}%</span></div>
              <div className="h-2 rounded-full bg-bb-bg" aria-hidden><div className="h-2 rounded-full bg-bb-primary" style={{ width: `${Math.min(100, Number(x.share_pct))}%` }} /></div>
            </div>))}
          {s.supplier_risk.high_dependency ? <p className="font-semibold text-bb-warning">{t("supplier.high_dep", { pct: num(s.supplier_risk.top_share_pct) })}</p> : null}
          {s.supplier_risk.note_key ? <p className="text-small">{t(s.supplier_risk.note_key)}</p> : null}
          <p className="text-small text-bb-muted">{t(`lender.basis.${s.supplier_risk.basis}`)} · {t("lender.names_hidden")}</p>
        </Section>
      ) : null}
      {s.news_signals ? (
        <Section title={t("section.news_signals")}>
          {s.news_signals.length === 0 ? <p className="text-small">{t("news.none")}</p> : s.news_signals.map((n: S, i: number) => (
            <div key={i} className="flex flex-col gap-1 border-t border-bb-border pt-2 text-small first:border-0 first:pt-0">
              <p className="font-semibold" lang={n.headline_lang}>{n.is_demo ? <><DemoBadge />{" "}</> : null}{n.headline}</p>
              <p className="text-bb-muted">{t("news.reported_by", { source: n.source_name, date: day(n.published_date) })} · {t(n.corroboration === "corroborated" ? "news.corroborated" : "news.single")}{n.auto_collected ? ` · ${t("news.auto")}` : ""}</p>
              {n.source_url ? <a href={n.source_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-bb-primary underline"><ExternalLink aria-hidden className="size-4" />{t("news.open_source")}</a> : null}
            </div>))}
        </Section>
      ) : null}
      {s.season_summary ? (
        <Section title={t("section.season_summary")}>
          <KV rows={[[t("lender.crop"), s.season_summary.season?.crop_name], [t("season.harvest"), day(s.season_summary.season?.expected_harvest_date)],
                     [t("lender.income_range"), `${tk(s.season_summary.income_range?.low)} – ${tk(s.season_summary.income_range?.high)}`],
                     [t("lender.planned_cost"), tk(s.season_summary.planned_cost_total)], [t("lender.paid_cost"), tk(s.season_summary.paid_cost_total)],
                     [t("season.break_even"), tk(s.season_summary.break_even_price_per_kg)], [t("season.loan_cover_title"), tk(s.season_summary.loan_cover_price_per_kg)]]} />
          <p className="text-small text-bb-muted">{t("lender.owner_estimates")}</p>
        </Section>
      ) : null}
      {s.transaction_list ? (
        <Section title={t("section.transaction_list")}>
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-small">
              <tbody>{s.transaction_list.map((x: S, i: number) => (
                <tr key={i} className="border-t border-bb-border">
                  <td className="py-1">{day(x.value_date)}</td><td>{t(`txn.${x.txn_type}`)}{x.supplier ? ` · ${x.supplier}` : ""}</td>
                  <td className="tabular text-right">{tk(x.amount)}</td></tr>))}</tbody>
            </table>
          </div>
        </Section>
      ) : null}
    </>
  );
}

function ReviewPanel({ c, onSaved }: { c: CaseFileT; onSaved: () => void }) {
  const { t, day } = useFmt();
  const [note, setNote] = useState("");
  const [info, setInfo] = useState("");
  const [decision, setDecision] = useState<Decision>("refer");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [fields, setFields] = useState<FieldErrors>({});
  const rv = c.review;

  async function send(kind: string, body: Record<string, unknown>, reset: () => void) {
    setBusy(kind);
    setError(null);
    setFields({});
    try {
      await api(`/lender/cases/${c.consent.id}/events`, { method: "POST", body });
      reset();
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(null);
    }
  }
  const area = (id: string, value: string, set: (v: string) => void, label: string, hint?: string) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="font-semibold">{label}</label>
      {hint ? <span className="text-small text-bb-muted">{hint}</span> : null}
      <textarea id={id} rows={2} maxLength={1000} value={value} onChange={(e) => set(e.target.value)}
                className="rounded-lg border border-bb-border p-2" />
    </div>
  );
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="font-semibold">{t("lender.review_panel")}</h2>
      {c.banner_key && rv?.decision ? (
        <StatusBanner tone="info" title={t("lender.decision_recorded", { decision: t(`decision.${rv.decision}`) })}>
          <p>{rv.decision_reason}</p><p className="mt-1 font-semibold">{t(c.banner_key)}</p>
        </StatusBanner>
      ) : null}
      <ErrorBanner error={error} />
      <p className="text-small">{t("lender.review_status")}: <span className="font-semibold">{rv ? t(`review.${rv.status}`) : "—"}</span></p>
      {!rv?.decision ? (
        <div className="flex flex-wrap gap-2">
          {(["under_review", "info_requested"] as const).map((s) => (
            <Button key={s} variant="secondary" disabled={rv?.status === s} busy={busy === s}
                    onClick={() => void send(s, { event_type: "status_change", status: s }, () => undefined)}>{t(`review.${s}`)}</Button>
          ))}
        </div>
      ) : null}
      {area("note", note, setNote, t("lender.note"), t("lender.note_hint"))}
      <Button variant="secondary" busy={busy === "note"} disabled={!note.trim()}
              icon={<Lock aria-hidden className="size-4" />}
              onClick={() => void send("note", { event_type: "note", body: note }, () => setNote(""))}>{t("lender.add_note")}</Button>
      {area("info", info, setInfo, t("lender.info_request"), t("lender.info_hint"))}
      <Button variant="secondary" busy={busy === "info"} disabled={!info.trim()}
              icon={<MessageSquare aria-hidden className="size-4" />}
              onClick={() => void send("info", { event_type: "info_request", body: info }, () => setInfo(""))}>{t("lender.send_info_request")}</Button>
      <div className="flex flex-col gap-2 border-t border-bb-border pt-3">
        <p className="font-semibold">{t("lender.decision")}</p>
        <Chips label={t("lender.decision")} value={decision} onChange={setDecision}
               options={(["proceed", "refer", "decline"] as Decision[]).map((d) => ({ value: d, label: t(`decision.${d}`) }))} />
        {area("reason", reason, setReason, t("lender.reason"), t("lender.reason_hint"))}
        {fields.body ? <p className="text-small text-bb-danger">{t(fields.body)}</p> : null}
        <Button busy={busy === "decision"} icon={<FileCheck2 aria-hidden className="size-4" />}
                onClick={() => void send("decision", { event_type: "decision", decision, body: reason }, () => setReason(""))}>
          {t("lender.record_decision")}
        </Button>
        <p className="text-caption text-bb-muted">{t("lender.decision_banner")}</p>
      </div>
      {rv?.events.length ? (
        <div className="flex flex-col gap-2 border-t border-bb-border pt-3 text-small">
          <p className="font-semibold">{t("lender.history")}</p>
          {[...rv.events].reverse().map((e) => (
            <p key={e.id}>
              <span className="text-bb-muted">{day(e.at)} · {e.officer} · {t(`lender.event.${e.event_type}`)}{e.visible_to_owner ? "" : ` (${t("lender.private")})`}:</span> {e.body}
            </p>
          ))}
        </div>
      ) : null}
    </Card>
  );
}

/** SCR-L03 Case file + review panel (FR-LEN-03..06). Reads the stored snapshot
 *  only; every read is logged and visible to the owner. */
export function CaseFile() {
  const { t, day } = useFmt();
  const { cid } = useParams();
  const [c, setC] = useState<CaseFileT | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [showHash, setShowHash] = useState(false);

  const load = useCallback(() => {
    api<CaseFileT>(`/lender/cases/${cid}`).then(setC).catch(setError);
  }, [cid]);
  useEffect(load, [load]);

  const blocked = error instanceof ApiError && error.status === 403;
  return (
    <LenderShell title={c?.snapshot.sections.profile_summary ? (c.snapshot.sections.profile_summary as S).display_name : t("lender.case_file")}>
      {blocked ? (
        <StatusBanner tone="danger" title={t((error as ApiError).messageKey)}>{t("lender.access_ended")}</StatusBanner>
      ) : <ErrorBanner error={error} />}
      {!c && !error ? <Loading /> : null}
      {c ? (
        <>
          <Card className="flex flex-wrap items-center gap-x-6 gap-y-1 text-small">
            {c.snapshot.is_demo ? <DemoBadge /> : null}
            <span>{t("lender.version", { n: c.consent.version })} · {t("lender.shared_on", { date: day(c.consent.shared_at) })}</span>
            <span>{t("lender.valid_until")}: {day(c.consent.valid_until)}</span>
            <button type="button" className="min-h-12 text-left underline" onClick={() => setShowHash((v) => !v)}>
              SHA-256 {showHash ? c.consent.snapshot_sha256 : `${c.consent.snapshot_sha256.slice(0, 12)}…`}
            </button>
            <span className={c.consent.hash_verified ? "text-bb-success" : "font-semibold text-bb-danger"}>
              {t(c.consent.hash_verified ? "lender.hash_ok" : "lender.hash_bad")}
            </span>
            <span className="basis-full text-bb-muted">{t("lender.hash_meaning")}</span>
          </Card>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
            <div className="flex flex-col gap-4"><Sections s={c.snapshot.sections as S} /></div>
            <div className="flex flex-col gap-4"><ReviewPanel c={c} onSaved={load} /></div>
          </div>
        </>
      ) : null}
    </LenderShell>
  );
}
