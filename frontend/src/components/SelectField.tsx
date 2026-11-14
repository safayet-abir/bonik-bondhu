import { useId } from "react";
import { useTranslation } from "react-i18next";

type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  hint?: string;
  errorKey?: string;
};

/** Native select (works with every phone keyboard / screen reader). */
export function SelectField({ label, value, onChange, options, hint, errorKey }: Props) {
  const id = useId();
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="font-semibold">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}
              aria-invalid={errorKey ? true : undefined}
              aria-describedby={errorKey ? `${id}-err` : hint ? `${id}-hint` : undefined}
              className={`h-12 rounded-bb border bg-bb-surface px-3 ${errorKey ? "border-bb-danger" : "border-bb-border"}`}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {errorKey ? (
        <p id={`${id}-err`} className="text-small text-bb-danger">
          {t(errorKey, { defaultValue: t("err.field.invalid") })}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-small text-bb-muted">{hint}</p>
      ) : null}
    </div>
  );
}
