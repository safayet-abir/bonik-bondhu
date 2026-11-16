import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import { setLanguage, type Lang } from "../i18n";
import { useAuth } from "../state/Auth";

/** বাং | EN switch; instant, no reload (FR-I18N-02). When logged in the
 *  choice is also saved on the account (FR-AUTH-08). */
const TONE = {
  plate: { on: "border-bb-primary bg-bb-primary-soft text-bb-primary", off: "border-bb-border bg-bb-surface text-bb-muted" },
  // on the teal wall (welcome screen, owner header)
  // brass stays for the scale and the one action; the chosen language is an enamel plate
  wall: { on: "border-bb-enamel bg-bb-enamel text-bb-iron", off: "border-white/50 bg-transparent text-white" },
};

export function LanguageSwitch({ large = false, tone = "plate" }: { large?: boolean; tone?: keyof typeof TONE }) {
  const { t, i18n } = useTranslation();
  const { me } = useAuth();
  const current = i18n.language as Lang;
  const options: { lang: Lang; label: string }[] = [
    { lang: "bn", label: large ? t("lang.bn") : "বাং" },
    { lang: "en", label: large ? t("lang.en") : "EN" },
  ];

  function choose(lang: Lang) {
    setLanguage(lang);
    if (me && me.preferred_language !== lang) {
      void api("/auth/me", { method: "PATCH", body: { preferred_language: lang } }).catch(() => undefined);
    }
  }

  return (
    <div role="group" aria-label={t("lang.label")} className="inline-flex gap-2">
      {options.map(({ lang, label }) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={current === lang}
          onClick={() => choose(lang)}
          className={`inline-flex min-h-12 min-w-12 items-center justify-center gap-1 rounded-bb border-2 px-3 font-semibold transition-colors duration-150 ${
            current === lang ? TONE[tone].on : TONE[tone].off
          }`}
        >
          {large && current === lang ? <Check aria-hidden className="size-4" strokeWidth={3} /> : null}
          {label}
        </button>
      ))}
    </div>
  );
}
