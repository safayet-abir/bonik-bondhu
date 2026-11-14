import { Info } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { ErrorBanner, PageShell } from "../../components/PageShell";

/** SCR-A02: only name, phone, email, password (MP §8). */
export function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", phone: "", email: "", password: "" });
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    setError(null);
    try {
      await api("/auth/register", { method: "POST", body: form });
      void navigate("/login", { state: { phone: form.phone, notice: "auth.registered" } });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t("auth.register_title")}>
      <div className="flex justify-end">
        <LanguageSwitch />
      </div>
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Field label={t("auth.full_name")} value={form.full_name} onChange={set("full_name")}
               autoComplete="name" hint={t("auth.full_name_hint")} errorKey={fields.full_name} required />
        <Field label={t("auth.phone")} value={form.phone} onChange={set("phone")} type="tel"
               inputMode="tel" autoComplete="tel" hint="01712345678" errorKey={fields.phone} required />
        <Field label={t("auth.email")} value={form.email} onChange={set("email")} type="email"
               autoComplete="email" hint="name@example.com" errorKey={fields.email} required />
        <Field label={t("auth.password")} value={form.password} onChange={set("password")} type="password"
               autoComplete="new-password" hint={t("auth.password_hint")} errorKey={fields.password} required />
        <p className="flex gap-2 text-small text-bb-muted">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t("auth.unverified_note")}
        </p>
        <Button type="submit" full busy={busy}>
          {t("auth.register")}
        </Button>
      </form>
      <p className="text-center">
        {t("auth.have_account")}{" "}
        <Link to="/login" className="font-semibold text-bb-primary underline">
          {t("auth.login")}
        </Link>
      </p>
    </PageShell>
  );
}
