import { ArrowDownCircle, Info, Receipt } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { TxnType } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { addDays, todayDhaka } from "../../lib/dates";
import { useActiveProfile } from "../../state/ActiveProfile";

// P1 slice: two entry types (Implementation Plan P1-T07). P2 adds the other ten.
const TYPES: { type: TxnType; icon: typeof Receipt }[] = [
  { type: "sale_cash", icon: ArrowDownCircle },
  { type: "operating_expense", icon: Receipt },
];
const EXPENSE_CATEGORIES = ["rent", "salary", "utility", "transport", "other"];

/** SCR-O04 Add entry. One client_request_id per form instance makes a
 *  double tap or retry save only once (FR-LED-10). */
export function AddEntry() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const initial = params.get("type") === "operating_expense" ? "operating_expense" : "sale_cash";

  const requestId = useMemo(() => crypto.randomUUID(), []);
  const today = todayDhaka();
  const [type, setType] = useState<TxnType>(initial);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(today);
  const [category, setCategory] = useState("rent");
  const [note, setNote] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!amount || Number(amount) <= 0) {
      setFields({ amount: "entry.err.amount" });
      return;
    }
    setBusy(true);
    setFields({});
    setError(null);
    try {
      await api(`/profiles/${p.id}/transactions`, {
        method: "POST",
        body: {
          txn_type: type, amount, value_date: date, note: note || null,
          category: type === "operating_expense" ? category : null,
          client_request_id: requestId,
        },
      });
      void navigate(`/p/${p.id}/home`, { state: { notice: "entry.saved" } });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t("entry.new")}>
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-semibold">{t("entry.what_happened")}</legend>
          <div className="grid grid-cols-2 gap-3">
            {TYPES.map(({ type: ty, icon: Icon }) => (
              <button key={ty} type="button" aria-pressed={type === ty} onClick={() => setType(ty)}
                      className={`flex min-h-14 items-center justify-center gap-2 rounded-bb border p-2 font-semibold ${
                        type === ty ? "border-bb-primary bg-bb-primary-soft text-bb-primary" : "border-bb-border bg-bb-surface"
                      }`}>
                <Icon aria-hidden className="size-5" />
                {t(`txn.${ty}`)}
              </button>
            ))}
          </div>
          <p className="flex gap-2 text-small text-bb-muted">
            <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
            {t(`txn.help.${type}`)}
          </p>
        </fieldset>

        <AmountInput label={t("entry.amount")} value={amount} onChange={setAmount}
                     hint={t("entry.amount_hint")} errorKey={fields.amount} />
        <Field label={t("entry.date")} type="date" value={date} max={addDays(today, 1)}
               onChange={(e) => setDate(e.target.value)} errorKey={fields.value_date} />

        {type === "operating_expense" ? (
          <label className="flex flex-col gap-1">
            <span className="font-semibold">{t("entry.category")}</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}
                    className="h-12 rounded-bb border border-bb-border bg-bb-surface px-3">
              {EXPENSE_CATEGORIES.map((c) => (
                <option key={c} value={c}>{t(`category.${c}`)}</option>
              ))}
            </select>
          </label>
        ) : null}

        <Field label={t("entry.note")} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)}
               hint={t("entry.note_hint")} errorKey={fields.note} />

        <Button type="submit" full busy={busy}>
          {t("common.save")}
        </Button>
      </form>
    </PageShell>
  );
}
