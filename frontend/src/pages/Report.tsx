// Unified verification report: scores, gate, entities, per-item table, document links.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useReport } from "../hooks/useContract";
import ScoreCards from "../components/ScoreCards";
import GateBanner from "../components/GateBanner";
import ResultsTable from "../components/ResultsTable";
import type { ContractSourceInfo, Entity } from "../types";

// ---------------------------------------------------------------------------
// Document links strip
// ---------------------------------------------------------------------------

const FORMAT_ICON: Record<string, string> = {
  pdf: "📄", docx: "📝", eml: "✉️", msg: "✉️", txt: "📃",
};

interface DocLinkProps {
  docId: string;
  filename: string;
  format: string;
  label?: string;
  contractId: string;
}

function DocLink({ docId, filename, format, label, contractId }: DocLinkProps) {
  return (
    <Link
      to={`/document/${docId}?contract_id=${contractId}`}
      className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-slate-50 hover:border-slate-300"
    >
      <span>{FORMAT_ICON[format] ?? "📄"}</span>
      <span className="max-w-[180px] truncate">{label ?? filename}</span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Report page
// ---------------------------------------------------------------------------

export default function Report() {
  const { contractId } = useParams<{ contractId: string }>();
  const { t } = useTranslation();
  const { report, loading, error } = useReport(contractId);
  const [sources, setSources] = useState<ContractSourceInfo[]>([]);

  useEffect(() => {
    if (!contractId) return;
    api.getContractSources(contractId).then(setSources).catch(() => {});
  }, [contractId]);

  if (loading) return <p className="text-slate-500">{t("common.loading")}</p>;
  if (error || !report) return <p className="text-red-600">{t("common.error")}</p>;

  const gov = report.entities?.governing_law as string | undefined;
  const parties = (report.entities?.parties as Entity[] | undefined) ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-xl font-semibold">{t("report.title")}</h1>
        <Link to="/contracts" className="shrink-0 text-sm text-indigo-600 hover:underline">
          ← {t("report.backToContracts")}
        </Link>
      </div>

      {report.library_warnings && report.library_warnings.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="font-medium text-amber-800">{t("report.libraryWarningTitle")}</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-amber-700 space-y-0.5">
            {report.library_warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <GateBanner scores={report.scores} />
      <ScoreCards scores={report.scores} />

      {/* Entities */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <span className="font-medium">{t("report.entities")}:</span>{" "}
        {parties.map((p) => p.value).join(", ") || "—"}
        {gov && <span className="ml-3 text-slate-500">{t("report.governingLaw")}: {gov}</span>}
      </div>

      {/* Document viewer links */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-3 text-sm font-medium text-slate-600">{t("report.documents")}</p>
        <div className="flex flex-wrap gap-2">
          {contractId && (
            <DocLink
              docId={contractId}
              filename={contractId.slice(0, 8)}
              format="pdf"
              label={t("report.contractDoc")}
              contractId={contractId}
            />
          )}
          {sources.map((s) => (
            <DocLink
              key={s.doc_id}
              docId={s.doc_id}
              filename={s.filename}
              format={s.format}
              contractId={contractId!}
            />
          ))}
        </div>
        {sources.length === 0 && contractId && (
          <p className="text-xs text-slate-400 mt-1">{t("report.noSources")}</p>
        )}
      </div>

      <ResultsTable rows={report.rows} queueDecisions={report.queue_decisions} />
    </div>
  );
}
