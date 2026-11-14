import { Info } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import type { AreaUnit, Season, SeasonName } from "../../api/types";
import { AmountInput } from "../../components/AmountInput";
import { Button } from "../../components/Button";
import { Chips } from "../../components/Chips";
import { Field } from "../../components/Field";
import { ErrorBanner, Loading, PageShell } from "../../components/PageShell";
import { SelectField } from "../../components/SelectField";
import { StatusBanner } from "../../components/StatusBanner";
import type { Lang } from "../../i18n";
import { formatNumber, normalizeDigits } from "../../lib/format";
import { useActiveProfile } from "../../state/ActiveProfile";

const SEASON_NAMES: SeasonName[] = ["boro", "aman", "aus", "winter_vegetables", "other"];
const UNITS: AreaUnit[] = ["decimal", "acre", "bigha", "sq_ft"];
const RANGE = ["low", "expected", "high"] as const;

type Form = {
  crop_name: string; variety: string; season_name: SeasonName; season_label: string;
  area_value: string; area_unit: AreaUnit; decimals_per_bigha: string;
  sowing_date: string; expected_harvest_date: string;
  output: Record<(typeof RANGE)[number], string>; price: Record<(typeof RANGE)[number], string>;
};

const strip = (v: string | null) => (v ? v.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1") : "");

function fromSeason(s: Season): Form {
  return {
    crop_name: s.crop_name, variety: s.variety ?? "", season_name: s.season_name, season_label: s.season_label ?? "",
    area_value: s.area_value, area_unit: s.area_unit, decimals_per_bigha: s.decimals_per_bigha ?? "",
    sowing_date: s.sowing_date, expected_harvest_date: s.expected_harvest_date,
    output: { low: strip(s.expected_output_low), expected: strip(s.expected_output_expected), high: strip(s.expected_output_high) },
    price: { low: strip(s.expected_price_low), expected: strip(s.expected_price_expected), high: strip(s.expected_price_high) },
  };
}

const EMPTY: Form = {
  crop_name: "", variety: "", season_name: "boro", season_label: "", area_value: "", area_unit: "decimal",
  decimals_per_bigha: "", sowing_date: "", expected_harvest_date: "",
  output: { low: "", expected: "", high: "" }, price: { low: "", expected: "", high: "" },
};

/** Display-only preview; the server converts and stores area_acres (SUG-14). */
function previewAcres(f: Form): number | null {
  const v = Number(f.area_value);
  if (!f.area_value || !Number.isFinite(v) || v <= 0) return null;
  if (f.area_unit === "acre") return v;
  if (f.area_unit === "decimal") return v / 100;
  if (f.area_unit === "sq_ft") return v / 43560;
  const k = Number(f.decimals_per_bigha);
  return f.decimals_per_bigha && k > 0 ? (v * k) / 100 : null;
}

/** SCR-F02 Create / edit season (FR-SEA-01..03). */
export function SeasonForm() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const p = useActiveProfile();
  const { sid } = useParams();
  const navigate = useNavigate();
  const [f, setF] = useState<Form | null>(sid ? null : EMPTY);
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (sid) api<Season>(`/profiles/${p.id}/seasons/${sid}`).then((s) => setF(fromSeason(s))).catch(setError);
  }, [p.id, sid]);

  if (!f) return <PageShell><ErrorBanner error={error} />{error ? null : <Loading />}</PageShell>;
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF({ ...f, [k]: v });
  const acres = previewAcres(f);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!f) return;
    setBusy(true);
    setFields({});
    setError(null);
    const body = {
      crop_name: f.crop_name, variety: f.variety || null, season_name: f.season_name, season_label: f.season_label || null,
      area_value: f.area_value, area_unit: f.area_unit,
      decimals_per_bigha: f.area_unit === "bigha" ? f.decimals_per_bigha || null : null,
      sowing_date: f.sowing_date, expected_harvest_date: f.expected_harvest_date,
      ...Object.fromEntries(RANGE.map((r) => [`expected_output_${r}`, f.output[r] || null])),
      ...Object.fromEntries(RANGE.map((r) => [`expected_price_${r}`, f.price[r] || null])),
    };
    try {
      const s = await api<Season>(sid ? `/profiles/${p.id}/seasons/${sid}` : `/profiles/${p.id}/seasons`,
                                  { method: sid ? "PATCH" : "POST", body });
      void navigate(`/p/${p.id}/seasons/${s.id}`, { state: { notice: "entry.saved" } });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t(sid ? "season.edit" : "season.new")} back={sid ? `/p/${p.id}/seasons/${sid}` : `/p/${p.id}/home`}>
      <ErrorBanner error={error} />
      {Object.keys(fields).length ? <StatusBanner tone="danger" title={t("err.validation")} /> : null}
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("season.crop")} value={f.crop_name} maxLength={60} hint={t("season.crop_hint")}
                 onChange={(e) => set("crop_name", e.target.value)} errorKey={fields.crop_name} />
          <Field label={t("season.variety")} value={f.variety} maxLength={120} hint={t("season.variety_hint")}
                 onChange={(e) => set("variety", e.target.value)} errorKey={fields.variety} />
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-semibold">{t("season.season")}</span>
          <Chips label={t("season.season")} value={f.season_name} onChange={(v) => set("season_name", v)}
                 options={SEASON_NAMES.map((n) => ({ value: n, label: t(`season.name.${n}`) }))} />
        </div>
        <Field label={t("season.label")} value={f.season_label} maxLength={120} hint={t("season.label_hint")}
               onChange={(e) => set("season_label", e.target.value)} errorKey={fields.season_label} />

        <div className="grid grid-cols-2 gap-3">
          <Field label={t("season.area")} value={f.area_value} inputMode="decimal"
                 onChange={(e) => set("area_value", normalizeDigits(e.target.value))} errorKey={fields.area_value} />
          <SelectField label={t("season.unit")} value={f.area_unit} onChange={(v) => set("area_unit", v as AreaUnit)}
                       options={UNITS.map((u) => ({ value: u, label: t(`season.unit.${u}`) }))} />
        </div>
        {f.area_unit === "bigha" ? (
          <Field label={t("season.bigha_factor")} value={f.decimals_per_bigha} inputMode="decimal"
                 hint={t("season.bigha_factor_hint")}
                 onChange={(e) => set("decimals_per_bigha", normalizeDigits(e.target.value))}
                 errorKey={fields.decimals_per_bigha} />
        ) : null}
        {acres !== null ? (
          <p className="text-small text-bb-muted">= {t("season.acres", { n: formatNumber(acres.toFixed(4), lang) })}</p>
        ) : null}

        <div className="grid grid-cols-2 gap-3">
          <Field label={t("season.sowing")} type="date" value={f.sowing_date}
                 onChange={(e) => set("sowing_date", e.target.value)} errorKey={fields.sowing_date} />
          <Field label={t("season.harvest")} type="date" value={f.expected_harvest_date}
                 onChange={(e) => set("expected_harvest_date", e.target.value)} errorKey={fields.expected_harvest_date} />
        </div>

        {(["output", "price"] as const).map((group) => (
          <fieldset key={group} className="flex flex-col gap-2">
            <legend className="font-semibold">{t(`season.${group}_range`)}</legend>
            <div className="grid grid-cols-3 gap-2">
              {RANGE.map((r) => (
                <AmountInput key={r} label={t(`range.${r}`)} value={f[group][r]}
                             onChange={(v) => set(group, { ...f[group], [r]: v })}
                             errorKey={fields[`expected_${group}_${r}`]} />
              ))}
            </div>
          </fieldset>
        ))}
        <p className="flex gap-2 text-small text-bb-muted">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t("season.estimates_note")}
        </p>
        <Button type="submit" full busy={busy}>{t("common.save")}</Button>
      </form>
    </PageShell>
  );
}
