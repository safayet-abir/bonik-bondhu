import { Check, Landmark, LogIn, NotebookPen, Scale, Share2, Sprout, Store, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { getHealth, type Health } from "../../api/client";
import { Balance } from "../../components/Balance";
import { IconTile, Logo, Photo, PhotoCredit } from "../../components/Brand";
import { DemoBadge } from "../../components/DemoBadge";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import type { Lang } from "../../i18n";
import { formatTaka, toBanglaDigits } from "../../lib/format";

// DEMO numbers for the weighing on the first screen (labelled beside them; the real check uses the owner's records)
const WEEKLY_FREE_CASH = 21500;
const INSTALLMENTS = 12;
const MIN_AMOUNT = 50000;
const MAX_AMOUNT = 400000;

/** The shortfall mark: a weight with a notch filed out of it (world "Daripalla": state is a mark, not a colour). */
function NotchMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={className}>
      <path d="M3 21 V8 Q3 6 5 6 H10 L12 11 L14 6 H19 Q21 6 21 8 V21 Z" fill="currentColor" />
      <circle cx={12} cy={3.5} r={2} fill="none" stroke="currentColor" strokeWidth={1.8} />
    </svg>
  );
}

/** SCR-A01 Welcome (Plan Ultra F3, world "Daripalla"): the mechanism is the first screen — a loan weighed against
 *  a week's cash on the shop's brass balance. Language choice and the two account actions stay on it
 *  (FR-I18N-01). Still shows the server status from /health (P0 DoD). */
export function Welcome() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const navigate = useNavigate();
  const [health, setHealth] = useState<Health | "error" | null>(null);
  const [amount, setAmount] = useState(200000);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setHealth("error"));
    return () => {
      alive = false;
    };
  }, []);

  const statusText =
    health === null ? t("system.checking")
    : health === "error" ? t("err.network")
    : health.db === "ok" ? t("system.ok")
    : t("system.degraded");
  const statusOk = health !== null && health !== "error" && health.db === "ok";

  const installment = Math.round(amount / INSTALLMENTS);
  const fits = installment <= WEEKLY_FREE_CASH;
  const taka = (n: number) => formatTaka(String(n), lang);
  const audiences = [
    { photo: "shop-keraniganj" as const, icon: Store, tone: "teal" as const, title: t("land.aud_shop"), text: t("land.aud_shop_text") },
    { photo: "harvest-carry" as const, icon: Sprout, tone: "leaf" as const, title: t("land.aud_farm"), text: t("land.aud_farm_text") },
    { photo: "bazaar-spices" as const, icon: Landmark, tone: "sky" as const, title: t("land.lenders"), text: t("land.lenders_text") },
  ];
  const steps = [
    { icon: NotebookPen, title: t("land.step1"), text: t("land.step1_text") },
    { icon: Scale, title: t("land.step2"), text: t("land.step2_text") },
    { icon: Share2, title: t("land.step3"), text: t("land.step3_text") },
  ];

  return (
    <main className="min-h-dvh bg-bb-wall text-white">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 pt-4 sm:px-8">
        <Logo />
        <LanguageSwitch large tone="wall" />
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-x-16 px-4 pb-10 pt-1 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:pt-6">
        {/* the weighing: scale, readouts, slider, verdict, and the DEMO stamp right under the numbers */}
        <div className="flex w-full flex-col items-center">
          <div className="w-[70%] max-w-[480px] lg:w-full">
            <Balance left={WEEKLY_FREE_CASH} right={installment} settleFrom={-14} label={t("land.scale_label")} lang={lang} />
          </div>
          <div className="-mt-1 grid w-full max-w-[480px] grid-cols-2 gap-3 text-small">
            <p className="flex flex-col">
              <span className="text-[#d6ece8]">{t("land.cash")}</span>
              <span className="tabular font-display text-card font-semibold">{taka(WEEKLY_FREE_CASH)}</span>
            </p>
            <p className="flex flex-col text-right">
              <span className="text-[#d6ece8]">{t("land.installment")}</span>
              <span className="tabular font-display text-card font-semibold">{taka(installment)}</span>
            </p>
          </div>
          <label className="mt-2 flex w-full max-w-[480px] flex-col">
            <span className="flex items-baseline justify-between gap-3 font-semibold">
              {t("land.amount")}
              <span className="tabular font-display text-title">{taka(amount)}</span>
            </span>
            <input type="range" className="bb-range" min={MIN_AMOUNT} max={MAX_AMOUNT} step={10000} value={amount}
                   aria-valuetext={taka(amount)} onChange={(e) => setAmount(Number(e.target.value))} />
          </label>
          <p aria-live="polite"
             className={`flex w-full max-w-[480px] items-center gap-3 rounded-bb px-4 py-2.5 font-semibold shadow-[0_6px_16px_-8px_rgb(0_0_0/0.45)] ${
               fits ? "bg-bb-enamel text-bb-iron" : "bg-bb-danger text-white"}`}>
            {fits ? <Check aria-hidden className="size-6 shrink-0 text-bb-wall" strokeWidth={3} />
                  : <NotchMark className="size-6 shrink-0" />}
            {fits ? t("land.fits", { left: taka(WEEKLY_FREE_CASH - installment) })
                  : t("land.short", { short: taka(installment - WEEKLY_FREE_CASH) })}
          </p>
          <p className="mt-2 w-full max-w-[480px] text-caption text-[#d6ece8]">
            <DemoBadge /> {t("land.demo_note")}
          </p>
        </div>

        {/* the promise and the two actions */}
        <div className="mt-4 flex flex-col items-center text-center lg:mt-0 lg:items-start lg:text-left">
          <h1 className="text-[1.9rem] font-semibold leading-tight sm:text-[3rem] lg:text-[3.75rem]">{t("land.tagline")}</h1>
          <p className="mt-2 max-w-[52ch] text-small text-[#d6ece8] sm:text-body lg:text-card">{t("land.sub")}</p>
          <div className="mt-4 flex w-full max-w-[420px] flex-col gap-3 lg:mt-6">
            <button type="button" onClick={() => navigate("/register")}
                    className="inline-flex min-h-14 items-center justify-center gap-2 rounded-bb bg-bb-brass px-4 text-card font-semibold text-bb-iron shadow-[0_8px_18px_-10px_rgb(0_0_0/0.6)] transition-transform duration-150 active:translate-y-px">
              <UserPlus aria-hidden className="size-5" />{t("welcome.create_account")}
            </button>
            <button type="button" onClick={() => navigate("/login")}
                    className="inline-flex min-h-12 items-center justify-center gap-2 rounded-bb border-2 border-white/70 px-4 font-semibold text-white transition-colors duration-150 hover:bg-white/10">
              <LogIn aria-hidden className="size-5" />{t("welcome.login")}
            </button>
          </div>
        </div>
      </section>

      {/* who it is for: real bazaar and field photos (credited), one colour each */}
      <section className="bg-bb-bg text-bb-iron">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-8">
          <h2 className="text-[1.75rem] font-semibold sm:text-[2.25rem]">{t("land.for_who")}</h2>
          <ul className="mt-8 grid gap-7 md:grid-cols-3">
            {audiences.map(({ photo, icon, tone, title, text }) => (
              <li key={photo} className="bb-hard flex flex-col overflow-hidden rounded-2xl bg-bb-surface">
                <div className="aspect-[4/3] overflow-hidden border-b-2 border-bb-iron"><Photo slug={photo} /></div>
                <div className="flex flex-1 flex-col gap-2 p-5">
                  <span className="flex items-center gap-3 font-display text-card font-semibold">
                    <IconTile icon={icon} tone={tone} />{title}
                  </span>
                  <p className="flex-1 text-bb-muted">{text}</p>
                  <PhotoCredit slug={photo} className="text-bb-muted" />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="bg-bb-wall-deep">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-8">
          <h2 className="text-title font-semibold">{t("land.how")}</h2>
          <ol className="mt-6 grid gap-6 sm:grid-cols-3">
            {steps.map(({ icon: Icon, title, text }, i) => (
              <li key={title} className="flex gap-4 sm:flex-col">
                <span aria-hidden className="relative flex h-14 w-16 shrink-0 items-end justify-center">
                  {/* a cast iron weight with the step number stamped into it */}
                  <span className="absolute top-0 size-3.5 rounded-full border-[3px] border-bb-iron" />
                  <span className="flex h-11 w-16 items-center justify-center rounded-t-md bg-bb-iron font-display text-title font-semibold text-bb-brass">
                    {lang === "bn" ? toBanglaDigits(String(i + 1)) : i + 1}
                  </span>
                </span>
                <span className="flex flex-col gap-1">
                  <span className="flex items-center gap-2 font-display text-card font-semibold">
                    <Icon aria-hidden className="size-5 text-bb-brass" />{title}
                  </span>
                  <span className="text-[#d6ece8]">{text}</span>
                </span>
              </li>
            ))}
          </ol>

        </div>
      </section>

      {/* the promise on the field: the last thing a visitor reads, with the one action again */}
      <section className="relative isolate overflow-hidden bg-bb-iron">
        <span className="absolute inset-0 -z-10">
          <Photo slug="paddy-path" decorative drift />
          <span className="absolute inset-0 bg-gradient-to-r from-bb-iron via-bb-iron/85 to-bb-iron/40" />
        </span>
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-5 px-4 py-16 sm:px-8 sm:py-24">
          <Logo />
          <p className="max-w-[22ch] font-display text-[1.9rem] font-semibold leading-tight sm:text-[2.6rem]">{t("land.never")}</p>
          {/* a link (not a second button with the hero's name): it is navigation, and keeps one "create" button per page */}
          <Link to="/register"
                className="bb-hard inline-flex min-h-14 items-center gap-2 rounded-xl bg-bb-brass px-6 text-card font-semibold text-bb-iron transition-transform duration-100 active:translate-x-px active:translate-y-px">
            <UserPlus aria-hidden className="size-5" />{t("welcome.create_account")}
          </Link>
          <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-[#d6ece8]">
            <span className="flex items-center gap-2" aria-live="polite">
              <span aria-hidden className={`inline-block size-2 rounded-full ${statusOk ? "bg-bb-brass" : "bg-bb-danger"}`} />
              {t("system.status")}: {statusText}
            </span>
            <PhotoCredit slug="paddy-path" />
            <a href="/photos/CREDITS.md" className="underline-offset-2 hover:underline">{t("brand.credits")}</a>
          </p>
        </div>
      </section>
    </main>
  );
}
