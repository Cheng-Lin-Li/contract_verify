// The five headline scores as cards.
import { useTranslation } from "react-i18next";
import type { ScoreSummary } from "../types";

function Card({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${tone}`}>{value}</div>
    </div>
  );
}

function tally(m: Record<string, number>): string {
  const entries = Object.entries(m || {});
  return entries.length ? entries.map(([k, v]) => `${k}: ${v}`).join(" · ") : "—";
}

export default function ScoreCards({ scores }: { scores: ScoreSummary }) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Card label={t("report.coverage")} value={`${scores.coverage_score}%`}
            tone={scores.coverage_score >= 80 ? "text-covered" : "text-partial"} />
      <Card label={t("report.risk")} value={String(scores.risk_score)}
            tone={scores.risk_score >= 60 ? "text-missing" : ""} />
      <Card label={t("report.compliance")} value={tally(scores.playbook_compliance)} />
      <Card label={t("report.completeness")} value={tally(scores.standard_terms_completeness)} />
    </div>
  );
}
