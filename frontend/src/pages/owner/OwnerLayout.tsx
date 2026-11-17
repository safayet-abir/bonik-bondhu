import { ChevronDown, HandCoins, Home, List, Menu, MessageCircle, Sprout, type LucideIcon } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import { IconTile, Logo, type Tone } from "../../components/Brand";
import { DemoBadge } from "../../components/DemoBadge";
import { FrameContext, ScenePanel, sectionFor } from "../../components/Frame";
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
  const section = sectionFor(useLocation().pathname, farm);
  const where = useMemo(() => ({ section, farm }), [section, farm]);
  const nav: { to: string; icon: LucideIcon; label: string; tone: Tone }[] = [
    farm
      ? { to: `${base}/home`, icon: Sprout, label: t("nav.seasons"), tone: "leaf" }
      : { to: `${base}/home`, icon: Home, label: t("nav.home"), tone: "teal" },
    { to: `${base}/entries`, icon: List, label: t("nav.entries"), tone: farm ? "turmeric" : "leaf" },
    { to: `${base}/financing`, icon: HandCoins, label: t("nav.financing"), tone: "chili" },
    { to: `${base}/advisor`, icon: MessageCircle, label: t("nav.advisor"), tone: "plum" },
    { to: `${base}/more`, icon: Menu, label: t("nav.more"), tone: "sky" },
  ];
  // Phones: header, the page, a bottom tab bar. Wide screens (≥1024): the same nav becomes a column of colour
  // tiles on the left; ≥1280 adds the section's scene panel on the right so the screen is never empty.
  return (
    <FrameContext.Provider value={where}>
      <div className="flex min-h-dvh flex-col pb-16 lg:pb-0">
        <header className="sticky top-0 z-10 bg-bb-wall text-white shadow-[0_6px_14px_-10px_rgb(0_0_0/0.6)]">
          {/* a11y reflow: the name truncates (min-w-0); at 200 % zoom the badge/language wrap to a second line */}
          <div className="mx-auto flex max-w-[480px] flex-wrap items-center gap-2 px-4 py-2 lg:max-w-[1400px] lg:gap-4 lg:px-8">
            <span className="mr-4 hidden lg:block"><Logo to={`${base}/home`} /></span>
            <Link to="/profiles" className="flex min-h-12 min-w-0 flex-1 items-center gap-2 font-display text-card font-semibold lg:flex-none lg:rounded-xl lg:bg-bb-wall-deep lg:px-3"
                  aria-label={t("profiles.switch")}>
              <ProfileIcon type={p.activity_type} className="size-5 shrink-0 text-bb-brass" />
              <span className="truncate">{p.display_name}</span>
              <ChevronDown aria-hidden className="size-4 shrink-0 text-[#d6ece8]" />
            </Link>
            <span className="hidden flex-1 lg:block" />
            {p.is_demo ? <DemoBadge /> : null}
            <LanguageSwitch tone="wall" />
          </div>
        </header>
        <div className="flex-1 lg:mx-auto lg:grid lg:w-full lg:max-w-[1400px] lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-8 lg:px-8 xl:grid-cols-[220px_minmax(0,600px)_minmax(0,1fr)]">
          <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-bb-border bg-bb-surface lg:sticky lg:top-20 lg:order-first lg:self-start lg:border-0 lg:bg-transparent lg:pt-6">
            <ul className="mx-auto grid h-16 max-w-[480px] grid-cols-5 lg:flex lg:h-auto lg:flex-col lg:gap-2">
              {nav.map(({ to, icon: Icon, label, tone }) => (
                <li key={to}>
                  <NavLink to={to} end
                           className={({ isActive }) =>
                             `relative flex h-full flex-col items-center justify-center text-caption transition-colors duration-150 lg:min-h-14 lg:flex-row lg:justify-start lg:gap-3 lg:rounded-xl lg:border-2 lg:px-2.5 lg:text-body lg:before:hidden ${
                               isActive
                                 ? "font-semibold text-bb-primary before:absolute before:inset-x-4 before:top-0 before:h-[3px] before:rounded-b before:bg-bb-brass lg:bb-hard-sm lg:bg-bb-surface lg:text-bb-iron"
                                 : "text-bb-muted lg:border-transparent lg:text-bb-text lg:hover:bg-bb-surface"
                             }`}>
                    <Icon aria-hidden className="size-5 lg:hidden" />
                    <span className="hidden lg:inline-flex"><IconTile icon={Icon} tone={tone} size="sm" /></span>
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="min-w-0 lg:pb-12">
            <Outlet />
          </div>
          <div className="hidden xl:block xl:pt-6">
            <ScenePanel key={section} section={section} farm={farm} />
          </div>
        </div>
      </div>
    </FrameContext.Provider>
  );
}

export function OwnerLayout() {
  return (
    <ActiveProfileProvider fallback={<Loading />}>
      <OwnerChrome />
    </ActiveProfileProvider>
  );
}
