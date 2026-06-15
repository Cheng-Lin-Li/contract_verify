// Unified verification report: scores, gate, entities, per-item table.
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useReport } from "../hooks/useContract";
import ScoreCards from "../components/ScoreCards";
import GateBanner from "../components/GateBanner";
import ResultsTable from "../components/ResultsTable";
import type { Entity } from "../types";

export default function Report() {
  const { contractId } = useParams();
  const { t } = useTranslation();
  const { report, loading, error } = useReport(contractId);

  if (loading) return <p className="text-slate-500">{t("common.loading")}</p>;
  if (error || !report) return <p className="text-red-600">{t("common.error")}</p>;

  const gov = report.entities?.governing_law as string | undefined;
  const parties = (report.entities?.parties as Entity[] | undefined) ?? [];

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">{t("report.title")}</h1>
      <GateBanner scores={report.scores} />
      <ScoreCards scores={report.scores} />

      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <span className="font-medium">{t("report.entities")}:</span>{" "}
        {parties.map((p) => p.value).join(", ") || "—"}
        {gov && <span className="ml-3 text-slate-500">{t("report.governingLaw")}: {gov}</span>}
      </div>

      <ResultsTable rows={report.rows} />
    </div>
  );
}
