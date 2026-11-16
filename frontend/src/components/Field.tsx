import { useId, type InputHTMLAttributes } from "react";
import { useTranslation } from "react-i18next";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  /** Example/helper text shown under the input (labels are never placeholder-only). */
  hint?: string;
  /** i18n message key from the server or client validation. */
  errorKey?: string;
};

export function Field({ label, hint, errorKey, className = "", ...rest }: Props) {
  const id = useId();
  const { t } = useTranslation();
  const describedBy = errorKey ? `${id}-err` : hint ? `${id}-hint` : undefined;
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      <input
        id={id}
        {...rest}
        aria-invalid={errorKey ? true : undefined}
        aria-describedby={describedBy}
        className={`h-12 rounded-bb border bg-bb-surface px-3 text-body outline-none focus:border-bb-primary focus-visible:ring-2 focus-visible:ring-bb-primary ${
          errorKey ? "border-bb-danger" : "border-bb-border"
        }`}
      />
      {errorKey ? (
        <p id={`${id}-err`} className="text-small text-bb-danger">
          {/* Unknown generic keys (e.g. err.field.uuid_parsing) fall back to a plain message */}
          {t(errorKey, { defaultValue: t("err.field.invalid") })}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-small text-bb-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
