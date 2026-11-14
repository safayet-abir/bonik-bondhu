import { Inbox, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api } from "../../api/client";
import type { LenderCase, Page } from "../../api/types";
import { Button } from "../../components/Button";
import { DemoBadge } from "../../components/DemoBadge";
import { EmptyState } from "../../components/EmptyState";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { ErrorBanner, Loading } from "../../components/PageShell";
import type { Lang } from "../../i18n";
import { formatDate } from "../../lib/dates";
import { useAuth } from "../../state/Auth";

/** SCR-L01 case list (desktop-first). P1: proves lender role routing; access
 *  requests and case files are added in P5. */
export function Cases() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const navigate = useNavigate();
  const { me, logout } = useAuth();
  const [cases, setCases] = useState<LenderCase[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<Page<LenderCase>>("/lender/cases").then((r) => setCases(r.items)).catch(setError);
  }, []);

  const org = me?.lender?.organization;
  return (
    <div className="min-h-dvh">
      <header className="border-b border-bb-border bg-bb-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <p className="flex-1 font-semibold">
            {org?.name} {org?.is_demo ? <DemoBadge /> : null}
            <span className="block text-small font-normal text-bb-muted">{me?.full_name}</span>
          </p>
          <LanguageSwitch />
          <Button variant="secondary" icon={<LogOut aria-hidden className="size-5" />}
                  onClick={() => void logout().then(() => navigate("/login"))}>
            {t("auth.logout")}
          </Button>
        </div>
      </header>
      <main className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6">
        <h1 className="text-title font-semibold">{t("lender.cases")}</h1>
        <ErrorBanner error={error} />
        {!cases && !error ? <Loading /> : null}
        {cases && cases.length === 0 ? (
          <EmptyState icon={<Inbox className="size-10" />} message={t("lender.no_cases")} />
        ) : null}
        {cases && cases.length > 0 ? (
          <table className="w-full rounded-bb border border-bb-border bg-bb-surface text-left">
            <thead className="text-small text-bb-muted">
              <tr>
                <th className="p-3">{t("lender.applicant")}</th>
                <th className="p-3">{t("lender.status")}</th>
                <th className="p-3">{t("lender.valid_until")}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.consent_id} className="border-t border-bb-border">
                  <td className="p-3">{c.applicant ? c.applicant.display_name : t("lender.awaiting_owner")}</td>
                  <td className="p-3">{t(`consent.status.${c.is_expired ? "expired" : c.status}`)}</td>
                  <td className="p-3">{c.valid_until ? formatDate(c.valid_until.slice(0, 10), lang) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </main>
    </div>
  );
}
