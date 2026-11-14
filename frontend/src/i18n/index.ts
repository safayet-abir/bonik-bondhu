// Bilingual UI (FR-I18N-01/02). Flat keys: server message_keys such as
// "entry.err.amount" are translated directly, so "." is not a separator.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import bn from "./bn.json";
import en from "./en.json";

export type Lang = "bn" | "en";
const STORAGE_KEY = "bb.lang"; // only `lang` may live in localStorage (TRD §3)

function storedLang(): Lang {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "en" ? "en" : "bn"; // Bangla first (ASM-06)
  } catch {
    return "bn";
  }
}

export function setLanguage(lang: Lang): void {
  void i18n.changeLanguage(lang);
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* storage unavailable (private mode): language still switches */
  }
}

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

void i18n.use(initReactI18next).init({
  resources: { bn: { translation: bn }, en: { translation: en } },
  lng: storedLang(),
  fallbackLng: "bn",
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false }, // React already escapes
});

document.documentElement.lang = i18n.language;

export default i18n;
