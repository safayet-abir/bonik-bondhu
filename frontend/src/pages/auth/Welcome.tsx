import { Check, Landmark, LogIn, NotebookPen, Scale, Share2, TriangleAlert, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { getHealth, type Health } from "../../api/client";
import { Balance, BalanceMark } from "../../components/Balance";
import { LanguageSwitch } from "../../components/LanguageSwitch";
import type { Lang } from "../../i18n";
import { formatTaka, toBanglaDigits } from "../../lib/format";

// DEMO numbers for the weighing on the first screen (labelled on the page; the real check uses the owner's records)
const WEEKLY_FREE_CASH = 21500;
const INSTALLMENTS = 12;
const MIN_AMOUNT = 50000;
const MAX_AMOUNT = 400000;

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
  const steps = [
    { icon: NotebookPen, title: t("land.step1"), text: t("land.step1_text") },
    { icon: Scale, title: t("land.step2"), text: t("land.step2_text") },
    { icon: Share2, title: t("land.step3"), text: t("land.step3_text") },
  ];

  return (
    <main className="min-h-dvh bg-bb-wall text-white">
      <header className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 pt-4 sm:px-8">
        <p className="flex items-center gap-2">
          <BalanceMark className="size-9 shrink-0" />
          <span className="flex flex-col leading-tight">
            <span lang="bn" className="font-display text-title font-semibold">বণিক বন্ধু</span>
            <span lang="en" className="text-caption text-[#d6ece8]">Bonik Bondhu</span>
          </span>
        </p>
        <LanguageSwitch large tone="wall" />
      </header>

      <section className="mx-auto flex max-w-2xl flex-col items-center px-4 pb-10 pt-2 sm:px-8">
        <div className="w-full max-w-[560px] lg:max-w-[460px]">
          <Balance left={WEEKLY_FREE_CASH} right={installment} settleFrom={-14} label={t("land.scale_label")} />
        </div>
        <div className="-mt-1 grid w-full max-w-[560px] lg:max-w-[460px] grid-cols-2 gap-3 text-small">
          <p className="flex flex-col">
            <span className="text-[#d6ece8]">{t("land.cash")}</span>
            <span className="tabular font-display text-card font-semibold">{taka(WEEKLY_FREE_CASH)}</span>
          </p>
          <p className="flex flex-col text-right">
            <span className="text-[#d6ece8]">{t("land.installment")}</span>
            <span className="tabular font-display text-card font-semibold">{taka(installment)}</span>
          </p>
        </div>

        <label className="mt-4 flex w-full max-w-[560px] lg:max-w-[460px] flex-col gap-2">
          <span className="flex items-baseline justify-between gap-3 font-semibold">
            {t("land.amount")}
            <span className="tabular font-display text-title">{taka(amount)}</span>
          </span>
          <input type="range" className="bb-range" min={MIN_AMOUNT} max={MAX_AMOUNT} step={10000} value={amount}
                 aria-valuetext={taka(amount)} onChange={(e) => setAmount(Number(e.target.value))} />
        </label>

        <p aria-live="polite"
           className={`mt-4 flex w-full max-w-[560px] lg:max-w-[460px] items-center gap-3 rounded-bb px-4 py-3 font-semibold shadow-[0_6px_16px_-8px_rgb(0_0_0/0.45)] ${
             fits ? "bg-bb-enamel text-bb-iron" : "bg-bb-danger text-white"}`}>
          {fits ? <Check aria-hidden className="size-6 shrink-0 text-bb-wall" strokeWidth={3} />
                : <TriangleAlert aria-hidden className="size-6 shrink-0" />}
          {fits ? t("land.fits", { left: taka(WEEKLY_FREE_CASH - installment) })
                : t("land.short", { short: taka(installment - WEEKLY_FREE_CASH) })}
        </p>

        <h1 className="mt-6 text-center text-[1.9rem] font-semibold leading-tight sm:text-[3rem]">{t("land.tagline")}</h1>
        <p className="mt-3 max-w-[52ch] text-center text-[#d6ece8]">{t("land.sub")}</p>

        <div className="mt-6 flex w-full max-w-[420px] flex-col gap-3">
          <button type="button" onClick={() => navigate("/register")}
                  className="inline-flex min-h-14 items-center justify-center gap-2 rounded-bb bg-bb-brass px-4 text-card font-semibold text-bb-iron shadow-[0_8px_18px_-10px_rgb(0_0_0/0.6)] transition-transform duration-150 active:translate-y-px">
            <UserPlus aria-hidden className="size-5" />{t("welcome.create_account")}
          </button>
          <button type="button" onClick={() => navigate("/login")}
                  className="inline-flex min-h-12 items-center justify-center gap-2 rounded-bb border-2 border-white/70 px-4 font-semibold text-white transition-colors duration-150 hover:bg-white/10">
            <LogIn aria-hidden className="size-5" />{t("welcome.login")}
          </button>
        </div>
        <p className="mt-4 max-w-[60ch] text-center text-caption text-[#d6ece8]">
          <span className="mr-1 rounded-full bg-bb-demo px-2 py-0.5 font-semibold text-white">{t("demo.badge")}</span>
          {t("land.demo_note")}
        </p>
      </section>

      <section className="bg-bb-wall-deep">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-8">
          <h2 className="text-title font-semibold">{t("land.how")}</h2>
          <ol className="mt-6 grid gap-6 sm:grid-cols-3">
            {steps.map(({ icon: Icon, title, text }, i) => (
              <li key={title} className="flex gap-4 sm:flex-col">
                <span aria-hidden className="relative flex h-14 w-16 shrink-0 items-end justify-center">
                  {/* a stamped iron weight with the step number cast into it */}
                  <span className="absolute top-0 size-3 rounded-full bg-bb-iron" />
                  <span className="flex h-11 w-16 items-center justify-center bg-bb-iron font-display text-title font-semibold text-bb-brass [clip-path:polygon(10%_0,90%_0,100%_100%,0_100%)]">
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

          <div className="mt-10 flex flex-col gap-2 rounded-bb bg-bb-enamel p-5 text-bb-iron sm:flex-row sm:items-center sm:gap-6">
            <Landmark aria-hidden className="size-8 shrink-0 text-bb-wall" />
            <p className="flex flex-col">
              <span className="font-display text-card font-semibold">{t("land.lenders")}</span>
              <span className="text-bb-muted">{t("land.lenders_text")}</span>
            </p>
          </div>

          <p className="mt-10 font-display text-card font-semibold">{t("land.never")}</p>
          <p className="mt-2 flex items-center gap-2 text-caption text-[#d6ece8]" aria-live="polite">
            <span aria-hidden className={`inline-block size-2 rounded-full ${statusOk ? "bg-bb-brass" : "bg-bb-danger"}`} />
            {t("system.status")}: {statusText}
          </p>
        </div>
      </section>
    </main>
  );
}
