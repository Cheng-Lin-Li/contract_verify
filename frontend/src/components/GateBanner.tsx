// Auto-confirm vs routed-to-attorney banner with blocking reasons.
import { useTranslation } from "react-i18next";
import type { ScoreSummary } from "../types";

export default function GateBanner({ scores }: { scores: ScoreSummary }) {
  const { t } = useTranslation();
  if (scores.auto_confirm) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-800">
        ✓ {t("report.autoConfirm")}
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
      <div className="font-medium">⚠ {t("report.blocked")}</div>
      {scores.blocking_reasons.length > 0 && (
        <ul className="mt-1 list-inside list-disc text-sm">
          {scores.blocking_reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      )}
    </div>
  );
}
