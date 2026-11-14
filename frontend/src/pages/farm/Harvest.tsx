import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import { addDays, todayDhaka } from "../../lib/dates";
import { useActiveProfile } from "../../state/ActiveProfile";

/** SCR-F04 Record harvest (FR-SEA-06), then prompt to record the sale. */
export function Harvest() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const { sid } = useParams();
  const navigate = useNavigate();
  const today = todayDhaka();
  const [date, setDate] = useState(today);
  const [output, setOutput] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const base = `/p/${p.id}/seasons/${sid}`;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    try {
      await api(`/profiles/${p.id}/seasons/${sid}/harvest`, {
        method: "POST", body: { actual_harvest_date: date, actual_output: output },
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <PageShell title={t("season.record_harvest")} back={base}>
        <StatusBanner tone="success" title={t("season.harvest_saved")} />
        <Button full onClick={() => navigate(`/p/${p.id}/entries/new?type=sale_cash&season_id=${sid}&back=${base}`)}>
          {t("season.record_sale")}
        </Button>
        <Button variant="secondary" full onClick={() => navigate(base)}>{t("season.later")}</Button>
      </PageShell>
    );
  }

  return (
    <PageShell title={t("season.record_harvest")} back={base}>
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Field label={t("season.actual_harvest_date")} type="date" value={date} max={addDays(today, 1)}
               onChange={(e) => setDate(e.target.value)} errorKey={fields.actual_harvest_date} />
        <AmountInput label={t("season.actual_output")} value={output} onChange={setOutput}
                     hint={t("season.actual_output_hint")} errorKey={fields.actual_output} />
        <Button type="submit" full busy={busy}>{t("common.save")}</Button>
      </form>
    </PageShell>
  );
}
