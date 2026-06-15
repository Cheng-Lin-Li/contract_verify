// Attorney queue list with SLA state and decision buttons.
import { useTranslation } from "react-i18next";
import type { QueueAction, QueueItem } from "../types";
import StatusBadge from "./StatusBadge";

const SLA_TONE: Record<string, string> = {
  ok: "text-slate-500", warn: "text-amber-600", breach: "text-red-600 font-semibold",
};

export default function QueueList(
  { items, onAct }: { items: QueueItem[]; onAct: (id: string, a: QueueAction) => void },
) {
  const { t } = useTranslation();
  if (items.length === 0) return <p className="text-slate-500">{t("queue.empty")}</p>;
  return (
    <ul className="space-y-3">
      {items.map((it) => (
        <li key={it.queue_id} className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <StatusBadge status={it.status} />
            <span className="font-mono text-xs">{it.item_id}</span>
            <span className={`ml-auto text-xs ${SLA_TONE[it.sla_state]}`}>
              {t("queue.sla")}: {it.sla_state}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-700">{t("queue.reason")}: {it.reason}</p>
          <p className="text-xs text-slate-500">{t("queue.risk")}: {it.risk_score}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(["approve", "reject", "escalate", "add_to_playbook"] as QueueAction[]).map((a) => (
              <button key={a} onClick={() => onAct(it.queue_id, a)}
                className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100">
                {t(`queue.actions.${a === "add_to_playbook" ? "addToPlaybook" : a}`)}
              </button>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
