import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading) return <div className="p-8 text-slate-500">{t("common.loading")}</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
