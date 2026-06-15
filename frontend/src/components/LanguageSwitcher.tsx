// Toggles between English and Japanese (3-month localization scope).
import { useTranslation } from "react-i18next";
import { setLocale, SUPPORTED_LOCALES, Locale } from "../i18n";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  return (
    <select
      aria-label="language"
      className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
      value={i18n.language}
      onChange={(e) => setLocale(e.target.value as Locale)}
    >
      {SUPPORTED_LOCALES.map((l) => (
        <option key={l} value={l}>{l.toUpperCase()}</option>
      ))}
    </select>
  );
}
