import { Inbox, LogOut, Send } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";

import { Logo } from "../../components/Brand";
import { Button } from "../../components/Button";
import { SignBand } from "../../components/Frame";
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
    `flex min-h-12 items-center gap-2 rounded-xl px-3 font-semibold ${isActive ? "bb-hard-sm bg-bb-surface text-bb-iron" : "text-white hover:bg-bb-wall-deep"}`;
  return (
    <div className="min-h-dvh">
      {/* the lender's desk: the same wall and logo as the owner's app, the case's field photo behind the title */}
      <header className="bg-bb-wall text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-2">
          <Logo className="mr-2" />
          <p className="flex-1 font-display text-card font-semibold">
            {org?.name} {org?.is_demo ? <DemoBadge /> : null}
            <span className="block font-sans text-small font-normal text-[#d6ece8]">{me?.full_name}</span>
          </p>
          <nav aria-label={t("lender.nav")} className="flex gap-2">
            <NavLink to="/lender/cases" end className={link}><Inbox aria-hidden className="size-5" />{t("lender.cases")}</NavLink>
            <NavLink to="/lender/request" className={link}><Send aria-hidden className="size-5" />{t("lender.request_access")}</NavLink>
          </nav>
          <LanguageSwitch tone="wall" />
          <Button variant="secondary" icon={<LogOut aria-hidden className="size-5" />}
                  onClick={() => void logout().then(() => navigate("/login"))}>
            {t("auth.logout")}
          </Button>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6">
        <SignBand section="lender" className="rounded-2xl bb-hard">
          <div className="flex min-h-24 flex-col justify-center gap-1 px-6 py-5">
            <h1 className="text-[1.75rem] font-semibold leading-tight">{title}</h1>
            <p className="text-[#e6efec]">{t("scene.lender.line")}</p>
          </div>
        </SignBand>
        {children}
      </main>
    </div>
  );
}
