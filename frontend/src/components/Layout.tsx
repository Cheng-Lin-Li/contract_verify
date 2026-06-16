// App shell: top nav + role-aware links + language switch.
import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, hasRole } from "../auth/AuthContext";
import LanguageSwitcher from "./LanguageSwitcher";

export default function Layout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const link = "px-3 py-2 rounded text-sm font-medium";
  const active = ({ isActive }: { isActive: boolean }) =>
    `${link} ${isActive ? "bg-ink text-white" : "text-slate-600 hover:bg-slate-200"}`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <span className="mr-4 font-semibold">{t("app.title")}</span>
          <NavLink to="/contracts" className={active}>{t("nav.contracts")}</NavLink>
          <NavLink to="/upload" className={active}>{t("nav.upload")}</NavLink>
          {hasRole(user, "attorney", "gc_team", "admin") && (
            <NavLink to="/queue" className={active}>{t("nav.queue")}</NavLink>
          )}
          {hasRole(user, "attorney", "gc_team", "admin") && (
            <NavLink to="/library" className={active}>{t("nav.library")}</NavLink>
          )}
          <div className="ml-auto flex items-center gap-3">
            <LanguageSwitcher />
            <span className="text-sm text-slate-500">{user?.username} · {user?.role}</span>
            <button onClick={logout} className="text-sm text-slate-600 hover:underline">
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6"><Outlet /></main>
    </div>
  );
}
