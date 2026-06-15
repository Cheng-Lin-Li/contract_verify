// i18next setup with English + Japanese (the 3-month localization scope).
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "../locales/en.json";
import ja from "../locales/ja.json";

export const SUPPORTED_LOCALES = ["en", "ja"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

const stored = (localStorage.getItem("cv_locale") as Locale) || "en";

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ja: { translation: ja } },
  lng: stored,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function setLocale(locale: Locale): void {
  localStorage.setItem("cv_locale", locale);
  void i18n.changeLanguage(locale);
}

export default i18n;
