import {
  ChevronLeft, ChevronRight, HandCoins, Home, Landmark, Lightbulb, LogIn, Menu, MessageCircle, NotebookPen, Scale,
  Share2, Sprout, Store, TrendingUp, Wheat, type LucideIcon,
} from "lucide-react";
import { createContext, useContext, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";

import { toBanglaDigits } from "../lib/format";
import { IconTile, Logo, Photo, PhotoCredit, TONES, type PhotoSlug, type Tone } from "./Brand";

/** One frame for every screen (design round 3). Each part of the app is a "section" with its own bazaar or
 *  field photo, colour and icon; the title band, the desktop side panel and the guest split-screen read it. */

export type Section =
  | "auth" | "profiles" | "home" | "entries" | "money" | "financing" | "advisor" | "more" | "farm" | "harvest" | "lender";

export const SCENES: Record<Section, { photo: PhotoSlug; tone: Tone; icon: LucideIcon }> = {
  auth: { photo: "bazaar-vegetables", tone: "turmeric", icon: LogIn },
  profiles: { photo: "shop-keraniganj", tone: "teal", icon: Store },
  home: { photo: "shop-keraniganj", tone: "teal", icon: Home },
  entries: { photo: "vegetable-sellers", tone: "leaf", icon: NotebookPen },
  money: { photo: "bazaar-spices", tone: "turmeric", icon: TrendingUp },
  financing: { photo: "bazaar-potatoes", tone: "chili", icon: HandCoins },
  advisor: { photo: "tea-stall-art", tone: "plum", icon: MessageCircle },
  more: { photo: "bazaar-vegetables", tone: "sky", icon: Menu },
  farm: { photo: "paddy-path", tone: "leaf", icon: Sprout },
  harvest: { photo: "harvest-carry", tone: "turmeric", icon: Wheat },
  lender: { photo: "harvest-wetland", tone: "sky", icon: Landmark },
};

/** Which section a path belongs to. `farm` = the active profile is a crop farm (its home is Seasons). */
export function sectionFor(pathname: string, farm = false): Section {
  if (pathname.startsWith("/lender")) return "lender";
  if (pathname.startsWith("/profiles")) return "profiles";
  const m = /^\/p\/[^/]+\/([^/]+)(\/.*)?$/.exec(pathname);
  if (!m) return "auth";
  const [, seg, rest = ""] = m;
  switch (seg) {
    case "home": return farm ? "farm" : "home";
    case "entries": case "photo": return "entries";
    case "summary": case "forecast": return "money";
    case "financing": case "assessment": case "sharing": return "financing";
    case "advisor": return "advisor";
    case "seasons": return /\/(harvest|summary)$/.test(rest) ? "harvest" : "farm";
    default: return "more";
  }
}

/** Set by OwnerLayout: screens inside the owner frame get the side panel there; anything else is a guest screen. */
export const FrameContext = createContext<Section | null>(null);

export function useSection(): Section {
  const framed = useContext(FrameContext);
  const { pathname } = useLocation();
  return framed ?? sectionFor(pathname);
}

/** The teal signboard band with the section's photo behind it. Text stays on the solid side of the fade (AA). */
export function SignBand({ section, photoClass = "", className = "", children }: {
  section: Section; photoClass?: string; className?: string; children: ReactNode;
}) {
  return (
    <div className={`relative isolate overflow-hidden bg-bb-wall text-white ${className}`}>
      <span className={`absolute inset-0 -z-10 ${photoClass}`}>
        <Photo slug={SCENES[section].photo} decorative />
        <span className="absolute inset-0 bg-gradient-to-r from-bb-wall from-40% via-bb-wall/90 to-bb-wall/70" />
      </span>
      {children}
    </div>
  );
}

/** Desktop side panel (≥1280 px): the section's photo, a line about what this part does, tips you can page
 *  through, and the promise. Only words — never numbers that look like data. */
export function ScenePanel({ section }: { section: Section }) {
  const { t, i18n } = useTranslation();
  const [tip, setTip] = useState(0);
  const s = SCENES[section];
  const n = (v: number) => (i18n.language === "bn" ? toBanglaDigits(String(v)) : String(v));
  return (
    <aside aria-label={t("scene.aside")} className="sticky top-24 flex flex-col gap-5 pb-10">
      <figure className="bb-hard relative overflow-hidden rounded-2xl bg-bb-iron">
        <div className="aspect-[4/5] max-h-[48vh] w-full overflow-hidden">
          <Photo slug={s.photo} drift />
        </div>
        <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-bb-iron via-bb-iron/80 to-transparent p-5 pt-20 text-white">
          <span className="flex items-center gap-2.5">
            <IconTile icon={s.icon} tone={s.tone} size="sm" />
            <span className="font-display text-card font-semibold">{t(`scene.${section}.title`)}</span>
          </span>
          <span className="mt-1.5 block text-small text-[#e6efec]">{t(`scene.${section}.line`)}</span>
          <PhotoCredit slug={s.photo} className="mt-2 block text-[#c9d6d2]" />
        </figcaption>
      </figure>

      <section aria-label={t("scene.tip_label")} className={`bb-hard rounded-2xl p-5 ${TONES[s.tone]}`}>
        <div className="flex items-center gap-2">
          <Lightbulb aria-hidden className="size-5" />
          <h2 className="flex-1 font-display text-card font-semibold">{t("scene.tip_label")}</h2>
          <span className="tabular text-small font-semibold">{n(tip + 1)}/{n(3)}</span>
        </div>
        <p key={tip} aria-live="polite" className="bb-fade mt-2 min-h-[3.4em] text-bb-iron">
          {t(`scene.${section}.tip${tip + 1}`)}
        </p>
        <div className="mt-3 flex gap-2">
          {[{ d: -1, icon: ChevronLeft, label: t("scene.prev") }, { d: 1, icon: ChevronRight, label: t("scene.next") }].map(
            ({ d, icon: Icon, label }) => (
              <button key={d} type="button" aria-label={label} onClick={() => setTip((tip + d + 3) % 3)}
                      className="bb-hard-sm inline-flex size-11 items-center justify-center rounded-lg bg-bb-surface text-bb-iron transition-transform duration-100 active:translate-x-px active:translate-y-px">
                <Icon aria-hidden className="size-5" />
              </button>
            ))}
        </div>
      </section>

      <p className="flex items-center gap-2.5 text-small font-semibold text-bb-muted">
        <img src="/brand/logo-mark.svg" alt="" className="size-7" />
        {t("land.never")}
      </p>
    </aside>
  );
}

/** Screens outside the owner frame (login, register, choose business, not found): on a wide screen the left
 *  half is the bazaar with the promise; the form sits on the right. Phones see only the form column. */
export function GuestFrame({ section, children }: { section: Section; children: ReactNode }) {
  const { t } = useTranslation();
  const s = SCENES[section];
  const steps = [
    { icon: NotebookPen, tone: "leaf" as const, label: t("land.step1") },
    { icon: Scale, tone: "turmeric" as const, label: t("land.step2") },
    { icon: Share2, tone: "sky" as const, label: t("land.step3") },
  ];
  return (
    <div className="lg:grid lg:min-h-dvh lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      <div className="relative isolate hidden overflow-hidden bg-bb-iron text-white lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col lg:justify-between lg:p-10">
        <span className="absolute inset-0 -z-10">
          <Photo slug={s.photo} drift />
          <span className="absolute inset-0 bg-gradient-to-b from-bb-wall/90 via-bb-wall/35 to-bb-iron" />
        </span>
        <Logo to="/" />
        <div>
          <p className="max-w-[16ch] font-display text-[2.75rem] font-semibold leading-[1.1]">{t("land.tagline")}</p>
          <p className="mt-3 max-w-[46ch] text-[#e6efec]">{t("land.sub")}</p>
          <ul className="mt-6 flex flex-wrap gap-3">
            {steps.map(({ icon, tone, label }) => (
              <li key={label} className="flex items-center gap-2 rounded-xl bg-bb-iron/70 py-1.5 pl-1.5 pr-3 font-semibold">
                <IconTile icon={icon} tone={tone} size="sm" />{label}
              </li>
            ))}
          </ul>
          <PhotoCredit slug={s.photo} className="mt-6 block text-[#c9d6d2]" />
        </div>
      </div>
      <div className="min-w-0 lg:flex lg:flex-col lg:justify-center lg:py-12">
        <div className="lg:mx-auto lg:w-full lg:max-w-[520px]">{children}</div>
      </div>
    </div>
  );
}
