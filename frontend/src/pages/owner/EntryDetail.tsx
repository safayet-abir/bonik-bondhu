import { Ban } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { api, ApiError } from "../../api/client";
import type { Transaction } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { formatTaka } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";
import { entryLabel } from "./Entries";

/** SCR-O06 detail sheet: entries are never deleted; "Wrong? Void" keeps the
 *  row visible as voided and removes it from every calculation (FR-LED-06). */
export function EntryDetail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const { tid } = useParams();
  const [tx, setTx] = useState<Transaction | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [voiding, setVoiding] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonErr, setReasonErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Transaction>(`/profiles/${p.id}/transactions/${tid}`).then(setTx).catch(setError);
  }, [p.id, tid]);

  async function submitVoid(e: FormEvent) {
    e.preventDefault();
    if (reason.trim().length < 3) {
      setReasonErr("entry.err.void_reason");
      return;
    }
    setBusy(true);
    setReasonErr(undefined);
    try {
      setTx(await api<Transaction>(`/profiles/${p.id}/transactions/${tid}/void`, { method: "POST", body: { reason } }));
      setVoiding(false);
    } catch (err) {
      if (err instanceof ApiError && err.fields.reason) setReasonErr(err.fields.reason);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  const rows: [string, string | null][] = tx ? [
    ["entry.type", t(`txn.${tx.txn_type}`)],
    ["entry.amount", formatTaka(tx.amount, lang)],
    ["entry.date", formatDate(tx.value_date, lang)],
    ["entry.category", tx.category ? t(`category.${tx.category}`, { defaultValue: tx.category }) : null],
    ["entry.supplier", tx.supplier?.display_name ?? null],
    ["entry.note", tx.note],
    ["entry.evidence", t(`evidence.${tx.evidence_state}`)],
  ] : [];

  return (
    <PageShell title={tx ? entryLabel(tx, t) : t("entry.detail")} back={`/p/${p.id}/entries`}>
      <ErrorBanner error={error} />
      {!tx && !error ? <Loading /> : null}
      {tx ? (
        <>
          {tx.status === "voided" ? (
            <StatusBanner tone="warning" title={t("entry.voided")}>
              {t("entry.void_reason_was", { reason: tx.void_reason })}
            </StatusBanner>
          ) : null}
          <Card className="divide-y divide-bb-border p-0">
            {rows.filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 px-4 py-2">
                <span className="text-bb-muted">{t(k)}</span>
                <span className="text-right">{v}</span>
              </div>
            ))}
          </Card>
          <p className="text-small text-bb-muted">{t(`txn.help.${tx.txn_type}`)}</p>
          {tx.status === "confirmed" && !voiding ? (
            <Button variant="secondary" full icon={<Ban aria-hidden className="size-5" />} onClick={() => setVoiding(true)}>
              {t("entry.void")}
            </Button>
          ) : null}
          {voiding ? (
            <form onSubmit={submitVoid} className="flex flex-col gap-3" noValidate>
              <Field label={t("entry.void_reason")} value={reason} maxLength={200}
                     onChange={(e) => setReason(e.target.value)} hint={t("entry.void_hint")} errorKey={reasonErr} />
              <Button type="submit" variant="danger" full busy={busy}>{t("entry.void_confirm")}</Button>
            </form>
          ) : null}
        </>
      ) : null}
    </PageShell>
  );
}
