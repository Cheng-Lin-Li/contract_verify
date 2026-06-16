import { useTranslation } from "react-i18next";
import { useQueue } from "../hooks/useQueue";
import QueueList from "../components/QueueList";

export default function Queue() {
  const { t } = useTranslation();
  const { groups, loading, act } = useQueue();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{t("queue.title")}</h1>
      {loading ? <p className="text-slate-500">{t("common.loading")}</p>
               : <QueueList groups={groups} onAct={act} />}
    </div>
  );
}
