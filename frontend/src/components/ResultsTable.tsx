// Per-item verification table across all three layers, with citations.
import { useTranslation } from "react-i18next";
import type { ReportRow } from "../types";
import StatusBadge from "./StatusBadge";

const ACTION_STYLE: Record<string, string> = {
  approve: "bg-green-100 text-green-700",
  approve_with_edits: "bg-teal-100 text-teal-700",
  request_clarification: "bg-amber-100 text-amber-700",
  reject: "bg-red-100 text-red-700",
  escalate: "bg-purple-100 text-purple-700",
  add_to_playbook: "bg-blue-100 text-blue-700",
};

function AttorneyBadge({ action }: { action: string }) {
  const { t } = useTranslation();
  const cls = ACTION_STYLE[action] ?? "bg-slate-100 text-slate-600";
  const label = t(`queue.attorneyAction.${action}`, { defaultValue: action });
  return (
    <span className={`ml-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

interface Props {
  rows: ReportRow[];
  queueDecisions?: Record<string, string>;
}

export default function ResultsTable({ rows, queueDecisions = {} }: Props) {
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
            <th className="px-3 py-2">{t("report.col.source")}</th>
            <th className="px-3 py-2">{t("report.col.clause")}</th>
            <th className="px-3 py-2">{t("report.col.notes")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const decision = queueDecisions[r.item_id];
            return (
              <tr key={`${r.layer}-${r.item_id}`} className="border-t border-slate-100 align-top">
                <td className="px-3 py-2 font-mono text-xs">{r.item_id}</td>
                <td className="px-3 py-2">{t(`report.layer.${r.layer}`)}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={r.status} />
                  {decision && <AttorneyBadge action={decision} />}
                </td>
                <td className="px-3 py-2">{(r.confidence * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 max-w-xs">{r.requirement_text}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">{r.source_label ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {r.superseded_by ? (
                    <span className="italic text-slate-500">
                      → {t("report.supersededBy", { id: r.superseded_by })}
                    </span>
                  ) : (
                    r.matched_clause_ids.join(", ") || "—"
                  )}
                </td>
                <td className="px-3 py-2 text-slate-500">{r.notes}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
