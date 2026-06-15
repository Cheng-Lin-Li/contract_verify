// Hooks for polling a verification job and loading a report.
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { JobOut, Report } from "../types";

export function useReport(contractId?: string) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!contractId) return;
    setLoading(true);
    api.getReport(contractId)
      .then(setReport)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [contractId]);
  return { report, loading, error };
}

// Polls a job until it completes; returns the latest status.
export function useJobPolling(jobId: string | null, intervalMs = 1500): JobOut | null {
  const [job, setJob] = useState<JobOut | null>(null);
  useEffect(() => {
    if (!jobId) return;
    let timer: ReturnType<typeof setInterval>;
    const tick = () =>
      api.getJob(jobId).then((j) => {
        setJob(j);
        if (j.status === "completed" || j.status === "failed") clearInterval(timer);
      });
    void tick();
    timer = setInterval(tick, intervalMs);
    return () => clearInterval(timer);
  }, [jobId, intervalMs]);
  return job;
}
