// Colour-coded status pill, localized label.
import { useTranslation } from "react-i18next";

const COLOR: Record<string, string> = {
  Covered: "bg-green-100 text-green-800", Compliant: "bg-green-100 text-green-800", Present: "bg-green-100 text-green-800",
  Partial: "bg-amber-100 text-amber-800", Deviation: "bg-amber-100 text-amber-800", "Non-standard": "bg-amber-100 text-amber-800",
  Missing: "bg-red-100 text-red-800", Contradicted: "bg-red-100 text-red-800", Violation: "bg-red-100 text-red-800",
  Superseded: "bg-slate-100 text-slate-600",
};

export default function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const cls = COLOR[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {t(`status.${status}`, status)}
    </span>
  );
}
