import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { QueueAction, QueueItem } from "../types";

export function useQueue() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(() => {
    setLoading(true);
    return api.listQueue().then(setItems).finally(() => setLoading(false));
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const act = useCallback(async (id: string, action: QueueAction) => {
    await api.actOnQueueItem(id, action);
    await refresh();
  }, [refresh]);
  return { items, loading, act };
}
