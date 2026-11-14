import { CheckCircle2, Send } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { SectionKey } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { ErrorBanner } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import { SECTION_ORDER } from "../../lib/sharing";
import { LenderShell } from "./LenderShell";

const DEFAULT: SectionKey[] = ["profile_summary", "money_summary", "financing_request", "obligations", "supplier_risk"];

/** SCR-L02 Request access (FR-CON-01). The reply is the same whether or not
 *  the code exists, so codes cannot be probed. */
export function RequestAccess() {
  const { t } = useTranslation();
  const [code, setCode] = useState("");
  const [sections, setSections] = useState<SectionKey[]>(DEFAULT);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);

  const toggle = (s: SectionKey) =>
    setSections((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : SECTION_ORDER.filter((k) => [...cur, s].includes(k))));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await api("/lender/access-requests", {
        method: "POST", body: { share_code: code, requested_sections: sections, message: message || null },
      });
      setSent(true);
      setCode("");
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <LenderShell title={t("lender.request_access")}>
      <Card className="flex max-w-2xl flex-col gap-4">
        {sent ? (
          <StatusBanner tone="info" title={t("lender.request_sent_if_valid")}>
            <CheckCircle2 aria-hidden className="inline size-4" /> {t("lender.request_next")}
          </StatusBanner>
        ) : null}
        <ErrorBanner error={error} />
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <Field label={t("lender.share_code")} value={code} maxLength={20} hint={t("lender.share_code_hint")}
                 onChange={(e) => { setCode(e.target.value); setSent(false); }} errorKey={fields.share_code} />
          <fieldset className="flex flex-col gap-1">
            <legend className="mb-1 font-semibold">{t("lender.sections")}</legend>
            {SECTION_ORDER.map((s) => (
              <label key={s} className="flex min-h-12 items-center gap-3">
                <input type="checkbox" className="size-5 accent-bb-primary" checked={sections.includes(s)} onChange={() => toggle(s)} />
                <span>{t(`section.${s}`)}</span>
              </label>
            ))}
            {fields.requested_sections ? <p className="text-small text-bb-danger">{t(fields.requested_sections)}</p> : null}
          </fieldset>
          <div className="flex flex-col gap-1">
            <label htmlFor="msg" className="font-semibold">{t("lender.message")}</label>
            <textarea id="msg" value={message} maxLength={500} rows={3} onChange={(e) => setMessage(e.target.value)}
                      className="rounded-lg border border-bb-border p-3" />
          </div>
          <Button type="submit" busy={busy} disabled={!code.trim() || sections.length === 0}
                  icon={<Send aria-hidden className="size-5" />}>{t("lender.send_request")}</Button>
        </form>
      </Card>
    </LenderShell>
  );
}
