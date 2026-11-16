import { Inbox, LogOut, Send } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";

import { BalanceMark } from "../../components/Balance";
import { Button } from "../../components/Button";
import { DemoBadge } from "../../components/DemoBadge";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { useAuth } from "../../state/Auth";

/** Lender portal frame (UI spec §4.3): Cases · Request access · Logout.
 *  Desktop-first; no entry, farm or owner screens exist here (FR-LEN-07). */
export function LenderShell({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { me, logout } = useAuth();
  const org = me?.lender?.organization;
  const link = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-12 items-center gap-2 rounded-lg px-3 font-semibold ${isActive ? "bg-bb-primary-soft text-bb-primary" : "text-bb-text"}`;
  return (
    <div className="min-h-dvh">
      {/* the lender's desk: an enamel header under a strip of the shop wall the case comes from */}
      <header className="border-t-4 border-b border-t-bb-wall border-b-bb-border bg-bb-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <BalanceMark className="size-8 shrink-0" />
          <p className="flex-1 font-display text-card font-semibold">
            {org?.name} {org?.is_demo ? <DemoBadge /> : null}
            <span className="block font-sans text-small font-normal text-bb-muted">{me?.full_name}</span>
          </p>
          <nav aria-label={t("lender.nav")} className="flex gap-1">
            <NavLink to="/lender/cases" end className={link}><Inbox aria-hidden className="size-5" />{t("lender.cases")}</NavLink>
            <NavLink to="/lender/request" className={link}><Send aria-hidden className="size-5" />{t("lender.request_access")}</NavLink>
          </nav>
          <LanguageSwitch />
          <Button variant="secondary" icon={<LogOut aria-hidden className="size-5" />}
                  onClick={() => void logout().then(() => navigate("/login"))}>
            {t("auth.logout")}
          </Button>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6">
        <h1 className="text-title font-semibold">{title}</h1>
        {children}
      </main>
    </div>
  );
}
