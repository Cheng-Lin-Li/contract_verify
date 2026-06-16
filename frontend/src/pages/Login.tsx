import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(false);
    try { await login(username, password); navigate("/upload"); }
    catch { setError(true); }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form onSubmit={onSubmit} className="w-80 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold">{t("login.title")}</h1>
          <LanguageSwitcher />
        </div>
        <label className="block text-sm">{t("login.username")}</label>
        <input className="mb-3 mt-1 w-full rounded border border-slate-300 px-2 py-1"
               value={username} onChange={(e) => setUsername(e.target.value)} />
        <label className="block text-sm">{t("login.password")}</label>
        <input type="password" className="mb-4 mt-1 w-full rounded border border-slate-300 px-2 py-1"
               value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="mb-3 text-sm text-red-600">{t("login.error")}</p>}
        <button className="w-full rounded bg-ink py-2 text-white">{t("login.submit")}</button>
      </form>
    </div>
  );
}
