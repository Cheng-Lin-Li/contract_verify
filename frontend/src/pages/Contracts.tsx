// Contracts dashboard: list all past verifications with status and scores.
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import type { ContractSummary } from "../types";

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status, stage, progress }: { status: string; stage?: string | null; progress: number }) {
  const { t } = useTranslation();

  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        &#10003; {t("contracts.status.completed")}
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        &#10005; {t("contracts.status.failed")}
      </span>
    );
  }
  if (status === "running" || status === "queued") {
    const pct = Math.round(progress * 100);
    const stageLabel = t(`upload.stage.${stage ?? "queued"}`, { defaultValue: stage ?? "" });
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
        {stageLabel} {pct > 0 ? `${pct}%` : ""}
      </span>
    );
  }
  return <span className="text-xs text-slate-400">{status}</span>;
}

// ---------------------------------------------------------------------------
// Coverage cell
// ---------------------------------------------------------------------------

function CoverageCell({ score }: { score?: number | null }) {
  if (score == null) return <span className="text-slate-300">—</span>;
  const pct = Math.round(score);
  const color = pct >= 80 ? "text-green-600" : pct >= 60 ? "text-amber-600" : "text-red-600";
  return (
    <span className={`font-medium tabular-nums ${color}`}>{pct}%</span>
  );
}

// ---------------------------------------------------------------------------
// Auto-confirm cell
// ---------------------------------------------------------------------------

function AutoConfirmCell({ value }: { value?: boolean | null }) {
  if (value == null) return <span className="text-slate-300">—</span>;
  return value
    ? <span className="text-green-600 font-medium">&#10003; Yes</span>
    : <span className="text-amber-600 font-medium">&#10007; No</span>;
}

// ---------------------------------------------------------------------------
// Review status badge
// ---------------------------------------------------------------------------

const REVIEW_STYLE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  in_review: "bg-amber-100 text-amber-700",
  cleared: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  escalated: "bg-purple-100 text-purple-700",
};

function ReviewBadge({ status }: { status?: string | null }) {
  const { t } = useTranslation();
  if (!status) return <span className="text-slate-300">—</span>;
  const cls = REVIEW_STYLE[status] ?? "bg-slate-100 text-slate-600";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {t(`contracts.reviewStatus.${status}`, { defaultValue: status })}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Date formatter
// ---------------------------------------------------------------------------

function fmtDate(ts?: number | null): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Contracts page
// ---------------------------------------------------------------------------

export default function Contracts() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const data = await api.listContracts();
        if (active) setContracts(data);
      } catch {
        // silently ignore auth errors on poll
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    // Poll while any job is still running so the status updates live.
    const timer = setInterval(async () => {
      const data = await api.listContracts().catch(() => null);
      if (data && active) setContracts(data);
    }, 2000);

    return () => { active = false; clearInterval(timer); };
  }, []);

  async function handleDelete(e: React.MouseEvent, contractId: string, name: string) {
    e.stopPropagation();
    if (!window.confirm(t("contracts.deleteConfirm", { name }))) return;
    setDeleting(contractId);
    try {
      await api.deleteContract(contractId);
      setContracts((prev) => prev.filter((c) => c.contract_id !== contractId));
    } catch {
      // ignore — contract may already be gone
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("contracts.title")}</h1>
        <button
          onClick={() => navigate("/upload")}
          className="rounded bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          + {t("contracts.newVerification")}
        </button>
      </div>

      {loading && <p className="text-slate-500">{t("common.loading")}</p>}

      {!loading && contracts.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
          {t("contracts.empty")}
        </div>
      )}

      {contracts.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("contracts.col.contract")}</th>
                <th className="px-4 py-3">{t("contracts.col.status")}</th>
                <th className="px-4 py-3">{t("contracts.col.coverage")}</th>
                <th className="px-4 py-3">{t("contracts.col.autoConfirm")}</th>
                <th className="px-4 py-3">{t("contracts.col.blocking")}</th>
                <th className="px-4 py-3">{t("contracts.col.review")}</th>
                <th className="px-4 py-3">{t("contracts.col.submitted")}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {contracts.map((c) => {
                const key = c.contract_id || c.job_id || "";
                const displayName = c.contract_filename || (c.contract_id ? c.contract_id.slice(0, 8) : (c.job_id?.slice(0, 8) ?? "—"));
                const canView = c.status === "completed" && !!c.contract_id;

                return (
                  <tr
                    key={key}
                    className={canView ? "cursor-pointer hover:bg-slate-50" : ""}
                    onClick={() => canView && navigate(`/report/${c.contract_id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-slate-800">
                      <span title={c.contract_id || c.job_id || ""}>{displayName}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} stage={c.stage} progress={c.progress} />
                      {c.status === "failed" && c.error && (
                        <p className="mt-0.5 text-xs text-red-500 truncate max-w-[200px]" title={c.error}>
                          {c.error}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <CoverageCell score={c.coverage_score} />
                    </td>
                    <td className="px-4 py-3">
                      <AutoConfirmCell value={c.auto_confirm} />
                    </td>
                    <td className="px-4 py-3">
                      {c.blocking_count > 0
                        ? <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{c.blocking_count}</span>
                        : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <ReviewBadge status={c.review_status} />
                      {!!c.queue_pending && (
                        <span className="ml-1.5 text-xs text-amber-600">{c.queue_pending} pending</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 tabular-nums whitespace-nowrap">
                      {fmtDate(c.submitted_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {canView && (
                          <button
                            onClick={(e) => { e.stopPropagation(); navigate(`/report/${c.contract_id}`); }}
                            className="rounded border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                          >
                            {t("contracts.viewReport")}
                          </button>
                        )}
                        {c.contract_id && (
                          <button
                            onClick={(e) => handleDelete(e, c.contract_id, displayName)}
                            disabled={deleting === c.contract_id}
                            className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            {deleting === c.contract_id ? "…" : t("contracts.delete")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
