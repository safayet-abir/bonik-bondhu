import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { api, ApiError, type FieldErrors } from "../../api/client";
import { Button } from "../../components/Button";
import { Field } from "../../components/Field";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { ErrorBanner, PageShell } from "../../components/PageShell";
import { StatusBanner } from "../../components/StatusBanner";
import { useAuth } from "../../state/Auth";

type LoginState = { phone?: string; notice?: string; reason?: string } | null;

/** SCR-A03: phone + password; then route by role from /auth/me (App flow §1). */
export function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const state = useLocation().state as LoginState;
  const { refresh } = useAuth();
  const [phone, setPhone] = useState(state?.phone ?? "");
  const [password, setPassword] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFields({});
    setError(null);
    try {
      await api("/auth/login", { method: "POST", body: { phone, password } });
      const me = await refresh();
      if (me?.role === "lender_officer") void navigate("/lender/cases", { replace: true });
      else void navigate("/profiles", { replace: true, state: { fromLogin: true } });
    } catch (err) {
      setPassword("");
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") setFields(err.fields);
      else setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title={t("auth.login")}>
      <div className="flex justify-end">
        <LanguageSwitch />
      </div>
      {state?.notice ? <StatusBanner tone="success" title={t(state.notice)} /> : null}
      {state?.reason ? <StatusBanner tone="info" title={t(state.reason)} /> : null}
      <ErrorBanner error={error} />
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Field label={t("auth.phone")} value={phone} onChange={(e) => setPhone(e.target.value)} type="tel"
               inputMode="tel" autoComplete="tel" errorKey={fields.phone} required />
        <Field label={t("auth.password")} value={password} onChange={(e) => setPassword(e.target.value)}
               type="password" autoComplete="current-password" errorKey={fields.password} required />
        <Button type="submit" full busy={busy}>
          {t("auth.login")}
        </Button>
      </form>
      <p className="text-center text-small text-bb-muted">{t("auth.forgot")}</p>
      <p className="text-center">
        <Link to="/register" className="font-semibold text-bb-primary underline">
          {t("welcome.create_account")}
        </Link>
      </p>
    </PageShell>
  );
}
