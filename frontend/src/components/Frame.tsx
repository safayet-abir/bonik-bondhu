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

type SceneDef = {
  photo: PhotoSlug; tone: Tone; icon: LucideIcon;
  /** a crop farm sees its own field, not the bazaar; `text` = the section has farm wording (scene.<section>_farm.*) */
  farm?: { photo: PhotoSlug; icon?: LucideIcon; text?: boolean };
  /** screens for everyone (sign-in, choose business, lender desk) show a shop and a field side by side */
  both?: boolean;
};

export const SCENES: Record<Section, SceneDef> = {
  auth: { photo: "bazaar-vegetables", tone: "turmeric", icon: LogIn, both: true },
  profiles: { photo: "shop-keraniganj", tone: "teal", icon: Store, both: true },
  home: { photo: "shop-keraniganj", tone: "teal", icon: Home },
  entries: { photo: "vegetable-sellers", tone: "leaf", icon: NotebookPen, farm: { photo: "plough-oxen", text: true } },
  money: { photo: "bazaar-spices", tone: "turmeric", icon: TrendingUp },
  financing: { photo: "bazaar-potatoes", tone: "chili", icon: HandCoins, farm: { photo: "rice-trader", text: true } },
  advisor: { photo: "tea-stall-art", tone: "plum", icon: MessageCircle, farm: { photo: "farmer-field", text: true } },
  more: { photo: "bazaar-vegetables", tone: "sky", icon: Menu, farm: { photo: "farmer-portrait" } },
  farm: { photo: "paddy-path", tone: "leaf", icon: Sprout },
  harvest: { photo: "harvest-carry", tone: "turmeric", icon: Wheat },
  lender: { photo: "harvest-wetland", tone: "sky", icon: Landmark, both: true },
};

/** The two worlds the app serves, used wherever a screen is for both. */
export const PAIR: { photo: PhotoSlug; icon: LucideIcon; tone: Tone; label: string }[] = [
  { photo: "shop-keraniganj", icon: Store, tone: "teal", label: "profile.type.shop" },
  { photo: "harvest-carry", icon: Sprout, tone: "leaf", label: "profile.type.crop_farm" },
];

/** Resolve a section for this business: its photo, icon, tone and the i18n key base for its words. */
export function sceneOf(section: Section, farm: boolean) {
  const s = SCENES[section];
  const f = farm ? s.farm : undefined;
  return { photo: f?.photo ?? s.photo, icon: f?.icon ?? s.icon, tone: s.tone, key: f?.text ? `${section}_farm` : section, both: s.both };
}

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
export type Where = { section: Section; farm: boolean };
export const FrameContext = createContext<Where | null>(null);

export function useSection(): Where {
  const framed = useContext(FrameContext);
  const { pathname } = useLocation();
  return framed ?? { section: sectionFor(pathname), farm: false };
}

/** The teal signboard band with the section's photo behind it (a shop and a field side by side on screens for
 *  both). Text stays on the solid side of the fade (AA). `photo` overrides the scene (lender case of one kind). */
export function SignBand({ section, farm = false, photo, photoClass = "", className = "", children }: {
  section: Section; farm?: boolean; photo?: PhotoSlug; photoClass?: string; className?: string; children: ReactNode;
}) {
  const sc = sceneOf(section, farm);
  return (
    <div className={`relative isolate overflow-hidden bg-bb-wall text-white ${className}`}>
      <span className={`absolute inset-0 -z-10 ${photoClass}`}>
        {sc.both && !photo ? (
          <span className="absolute inset-y-0 right-0 flex w-3/5">
            {PAIR.map((p) => <span key={p.photo} className="h-full flex-1"><Photo slug={p.photo} decorative /></span>)}
          </span>
        ) : <Photo slug={photo ?? sc.photo} decorative />}
        <span className="absolute inset-0 bg-gradient-to-r from-bb-wall from-30% via-bb-wall/85 to-bb-wall/55" />
      </span>
      {children}
    </div>
  );
}

/** Phones and tablets, screens for everyone (sign in, register, choose business): the logo over a shop and a
 *  field side by side, named — the same promise the desktop split screen makes. */
export function GuestHero() {
  const { t } = useTranslation();
  return (
    <div className="relative isolate h-44 overflow-hidden bg-bb-wall text-white sm:h-56 lg:hidden">
      <span className="absolute inset-0 -z-10 flex">
        {PAIR.map((p) => <span key={p.photo} className="h-full flex-1"><Photo slug={p.photo} decorative drift /></span>)}
        <span className="absolute inset-0 bg-gradient-to-b from-bb-wall/85 via-bb-wall/25 to-bb-wall" />
      </span>
      <div className="mx-auto flex h-full max-w-[480px] flex-col justify-between px-4 pb-2 pt-3">
        <Logo to="/" />
        <ul className="flex flex-wrap gap-2">
          {PAIR.map((p) => (
            <li key={p.label} className="flex items-center gap-2 rounded-xl bg-bb-iron/75 py-1 pl-1 pr-3 text-small font-semibold">
              <IconTile icon={p.icon} tone={p.tone} size="sm" />{t(p.label)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** Desktop side panel (≥1280 px): the section's photo, a line about what this part does, tips you can page
 *  through, and the promise. Only words — never numbers that look like data. */
export function ScenePanel({ section, farm, compact, photo }: Where & { compact?: boolean; photo?: PhotoSlug }) {
  const { t, i18n } = useTranslation();
  const [tip, setTip] = useState(0);
  const s = { ...sceneOf(section, farm), ...(photo ? { photo } : {}) };
  const n = (v: number) => (i18n.language === "bn" ? toBanglaDigits(String(v)) : String(v));
  // compact = under the page on phones and tablets (photo above the tips; side by side from 640 px)
  return (
    <aside aria-label={t("scene.aside")}
           className={compact ? "grid gap-4 sm:grid-cols-2 sm:items-stretch" : "sticky top-24 flex flex-col gap-5 pb-10"}>
      <figure className="bb-hard relative overflow-hidden rounded-2xl bg-bb-iron">
        <div className={`w-full overflow-hidden ${compact ? "aspect-[4/3] sm:aspect-auto sm:h-full sm:min-h-64" : "aspect-[4/5] max-h-[48vh]"}`}>
          <Photo slug={s.photo} drift />
        </div>
        <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-bb-iron via-bb-iron/80 to-transparent p-5 pt-20 text-white">
          <span className="flex items-center gap-2.5">
            <IconTile icon={s.icon} tone={s.tone} size="sm" />
            <span className="font-display text-card font-semibold">{t(`scene.${s.key}.title`)}</span>
          </span>
          <span className="mt-1.5 block text-small text-[#e6efec]">{t(`scene.${s.key}.line`)}</span>
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
          {t(`scene.${s.key}.tip${tip + 1}`)}
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

      <p className={`flex items-center gap-2.5 text-small font-semibold text-bb-muted ${compact ? "sm:col-span-2" : ""}`}>
        <img src="/brand/logo-mark.svg" alt="" className="size-7" />
        {t("land.never")}
      </p>
    </aside>
  );
}

/** Screens outside the owner frame (login, register, choose business, not found): on a wide screen the left
 *  half is the bazaar with the promise; the form sits on the right. Phones see only the form column. */
export function GuestFrame({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const steps = [
    { icon: NotebookPen, tone: "leaf" as const, label: t("land.step1") },
    { icon: Scale, tone: "turmeric" as const, label: t("land.step2") },
    { icon: Share2, tone: "sky" as const, label: t("land.step3") },
  ];
  return (
    <div className="lg:grid lg:min-h-dvh lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      <div className="relative isolate hidden overflow-hidden bg-bb-iron text-white lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col lg:justify-between lg:p-10">
        {/* for both: a shop on top, a field below, each named — whoever signs in sees their own world */}
        <span className="absolute inset-0 -z-10 flex flex-col">
          {PAIR.map((p) => (
            <span key={p.photo} className="relative flex-1 overflow-hidden">
              <Photo slug={p.photo} drift />
            </span>
          ))}
          <span className="absolute inset-0 bg-gradient-to-b from-bb-wall/90 via-bb-iron/25 to-bb-iron" />
        </span>
        <div className="flex items-start justify-between gap-4">
          <Logo to="/" />
          <ul className="flex flex-col items-end gap-2">
            {PAIR.map((p) => (
              <li key={p.label} className="flex items-center gap-2 rounded-xl bg-bb-iron/75 py-1.5 pl-1.5 pr-3 font-semibold">
                <IconTile icon={p.icon} tone={p.tone} size="sm" />{t(p.label)}
              </li>
            ))}
          </ul>
        </div>
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
          <span className="mt-6 flex flex-col gap-0.5 text-[#c9d6d2]">
            {PAIR.map((p) => <PhotoCredit key={p.photo} slug={p.photo} />)}
          </span>
        </div>
      </div>
      <div className="min-w-0 lg:flex lg:flex-col lg:justify-center lg:py-12">
        <div className="lg:mx-auto lg:w-full lg:max-w-[520px]">{children}</div>
      </div>
    </div>
  );
}
