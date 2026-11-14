import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import { setLanguage, type Lang } from "../i18n";
import { useAuth } from "../state/Auth";

/** বাং | EN switch; instant, no reload (FR-I18N-02). When logged in the
 *  choice is also saved on the account (FR-AUTH-08). */
export function LanguageSwitch({ large = false }: { large?: boolean }) {
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
          className={`min-h-12 min-w-12 rounded-bb border px-3 font-semibold ${
            current === lang
              ? "border-bb-primary bg-bb-primary-soft text-bb-primary"
              : "border-bb-border bg-bb-surface text-bb-muted"
          }`}
        >
          {label}
          {large && current === lang ? " ✓" : ""}
        </button>
      ))}
    </div>
  );
}
