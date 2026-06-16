// Attorney queue — items grouped by contract, each showing the violated rule,
// matched contract clause text, and links to view the source documents.
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ContractQueueGroup, QueueAction, QueueItemDetail } from "../types";
import StatusBadge from "./StatusBadge";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SLA_TONE: Record<string, string> = {
  ok: "text-slate-400",
  warn: "text-amber-600 font-medium",
  breach: "text-red-600 font-semibold",
};

const LAYER_LABEL: Record<number, string> = { 1: "L1", 2: "L2 · Playbook", 3: "L3 · Standard Terms" };
const LAYER_COLOR: Record<number, string> = {
  1: "bg-blue-100 text-blue-700",
  2: "bg-violet-100 text-violet-700",
  3: "bg-teal-100 text-teal-700",
};

const ACTION_KEYS: QueueAction[] = ["approve", "reject", "escalate", "add_to_playbook"];
const ACTION_I18N: Record<QueueAction, string> = {
  approve: "queue.actions.approve",
  approve_with_edits: "queue.actions.approve",
  request_clarification: "queue.actions.approve",
  reject: "queue.actions.reject",
  escalate: "queue.actions.escalate",
  add_to_playbook: "queue.actions.addToPlaybook",
};
const ACTION_STYLE: Record<QueueAction, string> = {
  approve: "border-green-300 text-green-700 hover:bg-green-50",
  approve_with_edits: "border-green-300 text-green-700 hover:bg-green-50",
  request_clarification: "border-slate-300 text-slate-600 hover:bg-slate-100",
  reject: "border-red-300 text-red-700 hover:bg-red-50",
  escalate: "border-amber-300 text-amber-700 hover:bg-amber-50",
  add_to_playbook: "border-indigo-300 text-indigo-700 hover:bg-indigo-50",
};

// ---------------------------------------------------------------------------
// Single queue item card
// ---------------------------------------------------------------------------

function QueueItemCard({
  item, contractId, onAct,
}: { item: QueueItemDetail; contractId: string; onAct: (id: string, a: QueueAction) => void }) {
  const { t } = useTranslation();

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
      {/* Header row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${LAYER_COLOR[item.layer] ?? "bg-slate-100 text-slate-600"}`}>
          {LAYER_LABEL[item.layer] ?? `L${item.layer}`}
        </span>
        <StatusBadge status={item.status} />
        <span className="font-mono text-xs text-slate-400">{item.item_id}</span>
        <span className={`ml-auto text-xs ${SLA_TONE[item.sla_state]}`}>
          {t("queue.sla")}:{" "}
          {item.sla_due_at
            ? new Date(item.sla_due_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
            : "—"}
          {item.sla_state !== "ok" && (
            <span className="ml-1 uppercase">[{item.sla_state}]</span>
          )}
        </span>
      </div>

      {/* Reference rule */}
      {item.requirement_text && (
        <div className="rounded border border-violet-100 bg-violet-50 px-3 py-2">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-violet-600">
            {t("queue.referenceRule")}
          </p>
          <p className="text-sm text-slate-800 leading-relaxed">{item.requirement_text}</p>
        </div>
      )}

      {/* Matched contract clauses */}
      <div className="rounded border border-blue-100 bg-blue-50 px-3 py-2">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            {t("queue.contractClause")}
          </p>
          {item.matched_clauses.length > 0 && (
            <Link
              to={`/document/${contractId}?contract_id=${contractId}#block-${item.matched_clauses[0].block_id}`}
              className="text-xs text-indigo-600 hover:underline"
            >
              {t("queue.viewInContract")}
            </Link>
          )}
        </div>
        {item.matched_clauses.length > 0 ? (
          <ul className="space-y-2">
            {item.matched_clauses.map((cl) => (
              <li key={cl.block_id}>
                <span className="font-mono text-xs text-slate-400 mr-1">
                  {cl.block_id} · p.{cl.page}
                </span>
                <span className="text-sm text-slate-800 leading-relaxed">
                  {cl.text.length > 300 ? cl.text.slice(0, 300) + "…" : cl.text}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-400 italic">{t("queue.noClause")}</p>
        )}
      </div>

      {/* Reason / notes */}
      {item.reason && (
        <p className="text-sm text-slate-600">
          <span className="font-medium text-slate-700">{t("queue.reason")}: </span>
          {item.reason}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 pt-1">
        {ACTION_KEYS.map((a) => (
          <button
            key={a}
            onClick={() => onAct(item.queue_id, a)}
            className={`rounded border px-3 py-1 text-xs font-medium ${ACTION_STYLE[a]}`}
          >
            {t(ACTION_I18N[a])}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Contract group
// ---------------------------------------------------------------------------

function ContractGroup({
  group, onAct,
}: { group: ContractQueueGroup; onAct: (id: string, a: QueueAction) => void }) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      {/* Contract header */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-300 bg-slate-50 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-800 truncate">{group.contract_filename}</p>
          <p className="text-xs text-slate-500 font-mono">{group.contract_id.slice(0, 8)}…</p>
        </div>
        <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
          {t("queue.riskScore", { score: group.risk_score })}
        </span>
        <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-600">
          {t("queue.itemCount", { count: group.items.length })}
        </span>
        <Link
          to={`/document/${group.contract_id}?contract_id=${group.contract_id}`}
          className="rounded border border-indigo-300 bg-white px-3 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
        >
          {t("queue.viewContract")}
        </Link>
        <Link
          to={`/report/${group.contract_id}`}
          className="rounded border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
        >
          {t("queue.viewReport")}
        </Link>
      </div>

      {/* Items */}
      <div className="ml-4 space-y-3 border-l-2 border-slate-200 pl-4">
        {group.items.map((item) => (
          <QueueItemCard
            key={item.queue_id}
            item={item}
            contractId={group.contract_id}
            onAct={onAct}
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root export
// ---------------------------------------------------------------------------

export default function QueueList({
  groups, onAct,
}: { groups: ContractQueueGroup[]; onAct: (id: string, a: QueueAction) => void }) {
  const { t } = useTranslation();
  if (groups.length === 0) return <p className="text-slate-500">{t("queue.empty")}</p>;

  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <ContractGroup key={g.contract_id} group={g} onAct={onAct} />
      ))}
    </div>
  );
}
