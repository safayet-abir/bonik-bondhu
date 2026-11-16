import { ChevronDown, HandCoins, Home, List, Menu, MessageCircle, Sprout } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { DemoBadge } from "../../components/DemoBadge";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import { Loading } from "../../components/PageShell";
import { ActiveProfileProvider, useActiveProfile } from "../../state/ActiveProfile";
import { ProfileIcon } from "./Profiles";

/** Header (UI spec §4.3): active profile always visible (FR-PROF-04),
 *  DEMO badge, language switch. Bottom nav (§4.1/4.2) lists only screens that
 *  exist: Home/Seasons · Entries · Financing · Advisor · More ("Add" lives on
 *  Home and Entries). Farm profiles
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
    { to: `${base}/financing`, icon: HandCoins, label: t("nav.financing") },
    { to: `${base}/advisor`, icon: MessageCircle, label: t("nav.advisor") },
    { to: `${base}/more`, icon: Menu, label: t("nav.more") },
  ];
  return (
    <div className="flex min-h-dvh flex-col pb-16">
      <header className="sticky top-0 z-10 bg-bb-wall text-white shadow-[0_6px_14px_-10px_rgb(0_0_0/0.6)]">
        {/* a11y reflow: the name truncates (min-w-0); at 200 % zoom the badge/language wrap to a second line */}
        <div className="mx-auto flex max-w-[480px] flex-wrap items-center gap-2 px-4 py-2">
          <Link to="/profiles" className="flex min-h-12 min-w-0 flex-1 items-center gap-2 font-display text-card font-semibold"
                aria-label={t("profiles.switch")}>
            <ProfileIcon type={p.activity_type} className="size-5 shrink-0 text-bb-brass" />
            <span className="truncate">{p.display_name}</span>
            <ChevronDown aria-hidden className="size-4 shrink-0 text-[#d6ece8]" />
          </Link>
          {p.is_demo ? <DemoBadge /> : null}
          <LanguageSwitch tone="wall" />
        </div>
      </header>
      <div className="flex-1">
        <Outlet />
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-bb-border bg-bb-surface">
        <ul className="mx-auto grid h-16 max-w-[480px] grid-cols-5">
          {nav.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink to={to} end
                       className={({ isActive }) =>
                         `relative flex h-full flex-col items-center justify-center text-caption transition-colors duration-150 ${
                           isActive
                             ? "font-semibold text-bb-primary before:absolute before:inset-x-4 before:top-0 before:h-[3px] before:rounded-b before:bg-bb-brass"
                             : "text-bb-muted"
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
