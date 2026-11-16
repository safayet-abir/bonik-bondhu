import { AlertTriangle, CheckCircle2, Landmark, PlusCircle, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { Debt, DebtFrequency, DebtList, LenderType } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Chips } from "../../components/Chips";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate, todayDhaka } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

const LENDER_TYPES: LenderType[] = ["bank", "mfi", "ngo", "samity", "mohajon", "supplier_credit", "dealer_credit", "other"];
const FREQS: DebtFrequency[] = ["weekly", "monthly", "single"];

function DebtForm({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const [lenderType, setLenderType] = useState<LenderType>("mfi");
  const [label, setLabel] = useState("");
  const [principal, setPrincipal] = useState("");
  const [outstanding, setOutstanding] = useState("");
  const [freq, setFreq] = useState<DebtFrequency>("weekly");
  const [installment, setInstallment] = useState("");
  const [nextDue, setNextDue] = useState("");
  const [overdue, setOverdue] = useState(false);
  const [overdueAmount, setOverdueAmount] = useState("");
  const [note, setNote] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    try {
      await api(`/profiles/${p.id}/debts`, {
        method: "POST",
        body: {
          lender_type: lenderType, lender_label: label, original_principal: principal,
          outstanding_balance: outstanding, installment_frequency: freq,
          installment_amount: freq === "single" ? null : installment || null,
          next_due_date: nextDue || null, is_overdue: overdue,
          overdue_amount: overdue ? overdueAmount || "0" : null, interest_fee_note: note || null,
          outstanding_as_of: todayDhaka(),
        },
      });
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
        <ErrorBanner error={error} />
        <SelectField label={t("debt.lender_type")} value={lenderType} onChange={(v) => setLenderType(v as LenderType)}
                     options={LENDER_TYPES.map((lt) => ({ value: lt, label: t(`lender_type.${lt}`) }))}
                     errorKey={fields.lender_type} />
        <Field label={t("debt.label")} value={label} maxLength={80} hint={t("debt.label_hint")}
               onChange={(e) => setLabel(e.target.value)} errorKey={fields.lender_label} />
        <AmountInput label={t("debt.original")} value={principal} onChange={setPrincipal} errorKey={fields.original_principal} />
        <AmountInput label={t("debt.outstanding")} value={outstanding} onChange={setOutstanding}
                     hint={t("debt.outstanding_hint")} errorKey={fields.outstanding_balance} />
        <div className="flex flex-col gap-1">
          <span className="font-semibold">{t("debt.frequency")}</span>
          <Chips label={t("debt.frequency")} value={freq} onChange={setFreq}
                 options={FREQS.map((f) => ({ value: f, label: t(`debt.freq.${f}`) }))} />
        </div>
        {freq !== "single" ? (
          <AmountInput label={t("debt.installment")} value={installment} onChange={setInstallment}
                       errorKey={fields.installment_amount} />
        ) : null}
        <Field label={freq === "single" ? t("debt.due_date") : t("debt.next_due")} type="date" value={nextDue}
               onChange={(e) => setNextDue(e.target.value)} errorKey={fields.next_due_date} />
        <label className="flex min-h-12 items-center gap-3">
          <input type="checkbox" checked={overdue} onChange={(e) => setOverdue(e.target.checked)} className="size-5" />
          {t("debt.is_overdue")}
        </label>
        {overdue ? (
          <AmountInput label={t("debt.overdue_amount")} value={overdueAmount} onChange={setOverdueAmount}
                       errorKey={fields.overdue_amount} />
        ) : null}
        <Field label={t("debt.interest_note")} value={note} maxLength={120} hint={t("debt.interest_note_hint")}
               onChange={(e) => setNote(e.target.value)} errorKey={fields.interest_fee_note} />
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>
          <Button type="submit" busy={busy}>{t("common.save")}</Button>
        </div>
      </form>
    </Card>
  );
}

function DebtCard({ d, onClose }: { d: Debt; onClose: (d: Debt) => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const closed = d.status === "closed";
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="flex items-center gap-2 font-semibold">
          <Landmark aria-hidden className="size-5 text-bb-primary" />
          {t(`lender_type.${d.lender_type}`)} — {d.lender_label}
        </p>
        {d.is_overdue ? (
          <span className="flex items-center gap-1 rounded-full bg-bb-danger px-2 text-caption text-white">
            <AlertTriangle aria-hidden className="size-3" />{t("debt.overdue")}
          </span>
        ) : null}
      </div>
      <div className="grid grid-cols-2 gap-2 text-small">
        <span className="text-bb-muted">{t("debt.outstanding")}</span>
        <span className="tabular text-right font-semibold">{formatTaka(d.outstanding_balance, lang)}</span>
        <span className="text-bb-muted">{t("debt.installment")}</span>
        <span className="tabular text-right">
          {d.installment_amount ? `${formatTaka(d.installment_amount, lang)} · ` : ""}{t(`debt.freq.${d.installment_frequency}`)}
        </span>
        {d.next_due_date ? (
          <>
            <span className="text-bb-muted">{t("debt.next_due")}</span>
            <span className="text-right">{formatDate(d.next_due_date, lang)}</span>
          </>
        ) : null}
        {d.is_overdue ? (
          <>
            <span className="text-bb-muted">{t("debt.overdue_amount")}</span>
            <span className="tabular text-right">{formatTaka(d.overdue_amount, lang)}</span>
          </>
        ) : null}
      </div>
      {d.dates_outdated ? <StatusBanner tone="warning" title={t("debt.dates_outdated")} /> : null}
      {d.next_installments.length > 0 ? (
        <p className="text-small text-bb-muted">
          {t("debt.upcoming")}: {d.next_installments.map((i) => `${formatDate(i.due_date, lang)} (${formatTaka(i.amount, lang)})`).join(", ")}
        </p>
      ) : null}
      <p className="text-caption text-bb-muted">{t("debt.declared_by_owner")}</p>
      {closed ? (
        <p className="text-small font-semibold text-bb-muted">{t("debt.closed")}</p>
      ) : (
        <button type="button" onClick={() => onClose(d)} className="min-h-12 self-start text-small font-semibold text-bb-primary underline">
          {t("debt.mark_closed")}
        </button>
      )}
    </Card>
  );
}

/** SCR-O09 Loans I owe (FR-DEBT-01..04). */
export function Debts() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const [params] = useSearchParams();
  const back = params.get("back")?.startsWith(`/p/${p.id}/`) ? params.get("back")! : `/p/${p.id}/more`;
  const [data, setData] = useState<DebtList | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<DebtList>(`/profiles/${p.id}/debts`).then(setData).catch(setError);
  }, [p.id]);
  useEffect(load, [load]);

  const active = data?.items.filter((d) => d.status === "active") ?? [];

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t("debt.title")} back={back}>
      <ErrorBanner error={error} />
      {!data && !error ? <Loading /> : null}
      {data?.no_debt_declared && active.length === 0 ? (
        <StatusBanner tone="success" title={t("debt.none_declared")} />
      ) : null}
      {adding ? (
        <DebtForm onSaved={() => { setAdding(false); load(); }} onCancel={() => setAdding(false)} />
      ) : (
        <Button full icon={<PlusCircle aria-hidden className="size-5" />} onClick={() => setAdding(true)}>
          {t("debt.add")}
        </Button>
      )}
      {data && active.length === 0 && !data.no_debt_declared && !adding ? (
        <Button variant="secondary" full busy={busy} icon={<CheckCircle2 aria-hidden className="size-5" />}
                onClick={() => void run(() => api(`/profiles/${p.id}/debts/declare-none`, { method: "POST" }))}>
          {t("debt.none")}
        </Button>
      ) : null}
      {data?.items.map((d) => (
        <DebtCard key={d.id} d={d} onClose={(x) => void run(() =>
          api(`/profiles/${p.id}/debts/${x.id}`, { method: "PATCH", body: { status: "closed" } }))} />
      ))}
      <p className="flex gap-2 text-small text-bb-muted">
        <ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0" />
        {t("debt.cib")}
      </p>
    </PageShell>
  );
}
