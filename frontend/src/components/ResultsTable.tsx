// Per-item verification table across all three layers, with citations.
import { useTranslation } from "react-i18next";
import type { ReportRow } from "../types";
import StatusBadge from "./StatusBadge";

export default function ResultsTable({ rows }: { rows: ReportRow[] }) {
  const { t } = useTranslation();
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">{t("report.col.item")}</th>
            <th className="px-3 py-2">{t("report.col.layer")}</th>
            <th className="px-3 py-2">{t("report.col.status")}</th>
            <th className="px-3 py-2">{t("report.col.confidence")}</th>
            <th className="px-3 py-2">{t("report.col.requirement")}</th>
            <th className="px-3 py-2">{t("report.col.clause")}</th>
            <th className="px-3 py-2">{t("report.col.notes")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.layer}-${r.item_id}`} className="border-t border-slate-100 align-top">
              <td className="px-3 py-2 font-mono text-xs">{r.item_id}</td>
              <td className="px-3 py-2">{t(`report.layer.${r.layer}`)}</td>
              <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
              <td className="px-3 py-2">{(r.confidence * 100).toFixed(0)}%</td>
              <td className="px-3 py-2 max-w-xs">{r.requirement_text}</td>
              <td className="px-3 py-2 font-mono text-xs">{r.matched_clause_ids.join(", ") || "—"}</td>
              <td className="px-3 py-2 text-slate-500">{r.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
