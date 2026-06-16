import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractQueueGroup, QueueAction } from "../types";

export function useQueue() {
  const [groups, setGroups] = useState<ContractQueueGroup[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    setLoading(true);
    return api.listQueue().then(setGroups).finally(() => setLoading(false));
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const act = useCallback(async (queueId: string, action: QueueAction) => {
    await api.actOnQueueItem(queueId, action);
    await refresh();
  }, [refresh]);

  return { groups, loading, act };
}
