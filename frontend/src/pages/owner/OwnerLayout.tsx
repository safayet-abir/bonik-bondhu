import { ChevronDown, Home, List, Menu, PlusCircle, Sprout } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { DemoBadge } from "../../components/DemoBadge";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { Loading } from "../../components/PageShell";
import { ActiveProfileProvider, useActiveProfile } from "../../state/ActiveProfile";
import { ProfileIcon } from "./Profiles";

/** Header (UI spec §4.3): active profile always visible (FR-PROF-04),
 *  DEMO badge, language switch. Bottom nav (§4.1/4.2) lists only screens that
 *  exist in this phase; Financing and Advisor join in P3/P6. Farm profiles
 *  start on Seasons and never get a Forecast entry (FR-SEA-08). */
function OwnerChrome() {
  const { t } = useTranslation();
  const p = useActiveProfile();
  const base = `/p/${p.id}`;
  const farm = p.activity_type === "crop_farm";
  const nav = [
    farm
      ? { to: `${base}/home`, icon: Sprout, label: t("nav.seasons") }
      : { to: `${base}/home`, icon: Home, label: t("nav.home") },
    { to: `${base}/entries`, icon: List, label: t("nav.entries") },
    { to: `${base}/entries/new`, icon: PlusCircle, label: t("nav.add") },
    { to: `${base}/more`, icon: Menu, label: t("nav.more") },
  ];
  return (
    <div className="flex min-h-dvh flex-col pb-16">
      <header className="sticky top-0 z-10 border-b border-bb-border bg-bb-surface">
        <div className="mx-auto flex max-w-[480px] items-center gap-2 px-4 py-2">
          <Link to="/profiles" className="flex min-h-12 flex-1 items-center gap-2 font-semibold"
                aria-label={t("profiles.switch")}>
            <ProfileIcon type={p.activity_type} className="size-5 text-bb-primary" />
            <span className="truncate">{p.display_name}</span>
            <ChevronDown aria-hidden className="size-4 text-bb-muted" />
          </Link>
          {p.is_demo ? <DemoBadge /> : null}
          <LanguageSwitch />
        </div>
      </header>
      <div className="flex-1">
        <Outlet />
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-bb-border bg-bb-surface">
        <ul className="mx-auto grid h-16 max-w-[480px] grid-cols-4">
          {nav.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink to={to} end
                       className={({ isActive }) =>
                         `flex h-full flex-col items-center justify-center text-caption ${
                           isActive ? "font-semibold text-bb-primary" : "text-bb-muted"
                         }`}>
                <Icon aria-hidden className="size-5" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

export function OwnerLayout() {
  return (
    <ActiveProfileProvider fallback={<Loading />}>
      <OwnerChrome />
    </ActiveProfileProvider>
  );
}
