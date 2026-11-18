import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError, type FieldErrors } from "../api/client";
import type { ApplicantDetailsOut } from "../api/types";
import { useActiveProfile } from "../state/ActiveProfile";
import { Button } from "./Button";
import { Card } from "./Card";
import { Field } from "./Field";
import { ErrorBanner, Loading } from "./PageShell";

type Draft = {
  full_legal_name: string; date_of_birth: string; nid_number: string; address: string;
  nominee_name: string; nominee_relation: string; trade_licence: string; years_in_business: string;
};
const empty: Draft = { full_legal_name: "", date_of_birth: "", nid_number: "", address: "",
  nominee_name: "", nominee_relation: "", trade_licence: "", years_in_business: "" };
const groups: (keyof Draft)[][] = [["full_legal_name", "date_of_birth", "nid_number"],
  ["address", "nominee_name", "nominee_relation"], ["trade_licence", "years_in_business"]];

/** Private fields are replacement-only: GET never returns their stored raw values. */
export function ApplicantDetails() {
  const p = useActiveProfile();
  const { t } = useTranslation();
  const [saved, setSaved] = useState<ApplicantDetailsOut | null>(null);
  const [draft, setDraft] = useState<Draft>(empty);
  const [step, setStep] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [fields, setFields] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(false);

  useEffect(() => {
    let active = true;
    api<ApplicantDetailsOut>(`/profiles/${p.id}/applicant-details`)
      .then((data) => { if (active) setSaved(data); })
      .catch((err) => { if (active) setError(err); });
    return () => { active = false; };
  }, [p.id]);

  function edit() {
    const d = { ...empty };
    if (saved) {
      for (const key of ["full_legal_name", "address", "nominee_name", "nominee_relation", "trade_licence"] as const)
        d[key] = saved[key] ?? "";
      d.years_in_business = saved.years_in_business == null ? "" : String(saved.years_in_business);
    }
    setDraft(d); setStep(0); setFields({}); setNotice(false);
  }

  async function save() {
    setBusy(true); setError(null); setFields({});
    const body: Record<string, unknown> = {};
    for (const key of ["full_legal_name", "address", "nominee_name", "nominee_relation", "trade_licence"] as const)
      body[key] = draft[key].trim() || null;
    body.years_in_business = draft.years_in_business === "" ? null : Number(draft.years_in_business);
    if (draft.nid_number.trim()) body.nid_number = draft.nid_number.trim();
    if (draft.date_of_birth) body.date_of_birth = draft.date_of_birth;
    try {
      const data = await api<ApplicantDetailsOut>(`/profiles/${p.id}/applicant-details`, { method: "PUT", body });
      setSaved(data); setDraft({ ...empty }); setStep(null); setNotice(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setFields(err.fields);
        const first = groups.findIndex((g) => g.some((key) => key in err.fields));
        if (first >= 0) setStep(first);
      }
      setError(err);
    } finally { setBusy(false); }
  }

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-semibold">{t("applicant.title")}</h2>
      <p className="text-small">{t("applicant.declared")}</p>
      <p className="text-caption text-bb-muted">{t("applicant.privacy")}</p>
      <ErrorBanner error={error} />
      {!saved && !error ? <Loading /> : null}
      {saved ? <>
        <label className="text-small" htmlFor="applicant-completeness">{t("applicant.completeness", {
          completed: saved.completeness.completed, total: saved.completeness.total,
        })}</label>
        <progress id="applicant-completeness" value={saved.completeness.completed}
                  max={saved.completeness.total} className="h-3 w-full accent-bb-primary" />
        <p className="text-small">{t("applicant.nid_number")}: {saved.nid_masked ?? t("applicant.not_added")}</p>
        <p className="text-small">{t("applicant.date_of_birth")}: {saved.has_date_of_birth ? t("applicant.hidden") : t("applicant.not_added")}</p>
        {notice ? <p role="status" className="text-small">{t("applicant.saved")}</p> : null}
        {step == null ? <Button variant="secondary" onClick={edit}>{t("applicant.edit")}</Button> : <>
          <p className="font-semibold">{t("applicant.step", { n: step + 1 })}</p>
          <form autoComplete="off" onSubmit={(e) => { e.preventDefault(); void save(); }} className="flex flex-col gap-3" noValidate>
            {groups[step].map((key) => <Field key={key} label={t(`applicant.${key}`)}
              type={key === "date_of_birth" ? "date" : key === "nid_number" ? "password" : key === "years_in_business" ? "number" : "text"}
              inputMode={key === "nid_number" || key === "years_in_business" ? "numeric" : undefined}
              autoComplete="off" value={draft[key]} errorKey={fields[key]} min={key === "years_in_business" ? 0 : undefined}
              max={key === "years_in_business" ? 80 : undefined}
              maxLength={key === "address" ? 300 : key === "nid_number" ? 17 : key === "nominee_relation" ? 80 : key === "trade_licence" ? 100 : 120}
              hint={key === "nid_number" || key === "date_of_birth" ? t("applicant.keep_private") : key === "trade_licence" ? t("applicant.optional") : undefined}
              onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))} />)}
            <div className="flex flex-wrap gap-3">
              {step > 0 ? <Button type="button" variant="secondary" onClick={() => setStep(step - 1)}>{t("applicant.back")}</Button> : null}
              {step < 2 ? <Button type="button" variant="secondary" onClick={() => setStep(step + 1)}>{t("applicant.continue")}</Button> : null}
              <Button type="submit" busy={busy}>{t("applicant.save")}</Button>
              <Button type="button" variant="secondary" disabled={busy} onClick={() => { setStep(null); setDraft({ ...empty }); setError(null); }}>{t("common.cancel")}</Button>
            </div>
          </form>
        </>}
      </> : null}
    </Card>
  );
}
