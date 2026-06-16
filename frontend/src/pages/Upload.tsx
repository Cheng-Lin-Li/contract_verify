// Upload a contract + deal sources, run verification in background, show progress, route to report.
import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useJobPolling } from "../hooks/useContract";
import type { JobOut } from "../types";

// ---------------------------------------------------------------------------
// DropZone
// ---------------------------------------------------------------------------

interface DropZoneProps {
  label: string;
  accept: string;
  multiple?: boolean;
  files: File[];
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

function DropZone({ label, accept, multiple = false, files, onFiles, disabled }: DropZoneProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handle = (fl: FileList | null) => {
    if (!fl || disabled) return;
    onFiles(multiple ? Array.from(fl) : [fl[0]]);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        className={[
          "relative flex min-h-[88px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 text-center transition-colors",
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-50"
            : dragging
              ? "cursor-copy border-indigo-500 bg-indigo-50"
              : "cursor-pointer border-slate-300 hover:border-slate-400 hover:bg-slate-50",
        ].join(" ")}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
        onDragEnter={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files); }}
        onClick={() => { if (!disabled) inputRef.current?.click(); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => handle(e.target.files)}
        />
        {files.length > 0 ? (
          <ul className="w-full space-y-1 text-left">
            {files.map((f) => (
              <li key={f.name} className="flex items-center gap-2 text-sm text-slate-700">
                <span className="shrink-0 text-slate-400">&#128196;</span>
                <span className="min-w-0 truncate">{f.name}</span>
                <span className="ml-auto shrink-0 text-xs text-slate-400">
                  {(f.size / 1024).toFixed(0)} KB
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">{t("upload.dropHint")}</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProgressPanel
// ---------------------------------------------------------------------------

function ProgressPanel({ job }: { job: JobOut }) {
  const { t } = useTranslation();
  const pct = Math.round((job.progress ?? 0) * 100);
  const stageLabel = t(`upload.stage.${job.stage ?? "queued"}`, { defaultValue: job.stage ?? "" });

  return (
    <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
      <div className="mb-1.5 flex items-center justify-between text-sm font-medium text-indigo-700">
        <span>{stageLabel}</span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-indigo-200">
        <div
          className="h-full rounded-full bg-indigo-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      {job.stage_file && (
        <p className="mt-2 truncate text-xs text-indigo-600">{job.stage_file}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Upload page
// ---------------------------------------------------------------------------

export default function Upload() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [contract, setContract] = useState<File[]>([]);
  const [sources, setSources] = useState<File[]>([]);
  const [contractType, setContractType] = useState("services");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const job = useJobPolling(jobId, 1000);

  useEffect(() => {
    if (job?.status === "completed" && job.contract_id) {
      navigate(`/report/${job.contract_id}`);
    }
  }, [job, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!contract[0]) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const form = new FormData();
      form.append("contract", contract[0]);
      sources.forEach((f) => form.append("sources", f));
      const created = await api.uploadContract(form, contractType);
      setJobId(created.job_id);
    } catch (err) {
      setSubmitError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  const running = !!jobId && job?.status !== "failed" && job?.status !== "completed";
  const busy = submitting || running;

  return (
    <div className="max-w-xl">
      <h1 className="mb-4 text-xl font-semibold">{t("upload.title")}</h1>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
      >
        <DropZone
          label={t("upload.contract")}
          accept=".pdf,.docx,.txt"
          files={contract}
          onFiles={setContract}
          disabled={busy}
        />
        <DropZone
          label={t("upload.sources")}
          accept=".pdf,.docx,.eml,.txt,.msg"
          multiple
          files={sources}
          onFiles={setSources}
          disabled={busy}
        />
        <div>
          <label className="block text-sm font-medium text-slate-700">
            {t("upload.contractType")}
          </label>
          <input
            value={contractType}
            onChange={(e) => setContractType(e.target.value)}
            disabled={busy}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-50"
          />
        </div>

        <button
          type="submit"
          disabled={!contract[0] || busy}
          className="w-full rounded bg-ink px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? t("upload.running") : t("upload.submit")}
        </button>

        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        {job?.status === "failed" && (
          <p className="text-sm text-red-600">{job.error}</p>
        )}
      </form>

      {jobId && job && (job.status === "running" || job.status === "queued") && (
        <ProgressPanel job={job} />
      )}
    </div>
  );
}
