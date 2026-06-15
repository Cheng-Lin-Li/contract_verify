// Library page: upload playbook/standard-terms, view existing items.
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useJobPolling } from "../hooks/useContract";
import type { JobOut, LibraryItem } from "../types";

// ---------------------------------------------------------------------------
// Progress panel (upload progress)
// ---------------------------------------------------------------------------

function ProgressPanel({ job }: { job: JobOut }) {
  const { t } = useTranslation();

  const stageLabel =
    t(`library.stage.${job.stage ?? "queued"}`, { defaultValue: job.stage ?? "…" });

  const pageLabel = (() => {
    const cur = job.current_page ?? 0;
    const tot = job.total_pages ?? 0;
    if (job.stage === "extract") return t("library.progress.item", { current: cur, total: tot });
    if (!cur && !tot) return t("library.progress.scanning");
    const ext = (job.stage_file ?? "").split(".").pop()?.toLowerCase();
    const key = ext === "pdf" ? "page" : "section";
    return tot > 0
      ? t(`library.progress.${key}`, { current: cur, total: tot })
      : t("library.progress.scanning");
  })();

  const pct = Math.round(job.progress * 100);

  return (
    <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm">
      <div className="mb-1 flex items-center justify-between font-medium text-blue-800">
        <span>{stageLabel}{job.stage_file ? ` — ${job.stage_file}` : ""}</span>
        <span className="text-blue-600">{pct}%</span>
      </div>
      <div className="mb-1.5 h-2 w-full overflow-hidden rounded-full bg-blue-200">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-blue-700">{pageLabel}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rule badge
// ---------------------------------------------------------------------------

const RULE_STYLES: Record<string, string> = {
  must_have:     "bg-green-100 text-green-700",
  must_not_have: "bg-red-100 text-red-700",
  preferred:     "bg-blue-100 text-blue-700",
};

const PRIORITY_STYLES: Record<string, string> = {
  Critical: "bg-red-100 text-red-700",
  High:     "bg-orange-100 text-orange-700",
  Medium:   "bg-yellow-100 text-yellow-700",
  Low:      "bg-slate-100 text-slate-600",
};

function Chip({ label, cls }: { label: string; cls: string }) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Library items panel
// ---------------------------------------------------------------------------

type Layer = "playbook" | "standard-terms";

interface ItemsPanelProps {
  layer: Layer;
  refreshKey: number;
}

function LibraryItemsPanel({ layer, refreshKey }: ItemsPanelProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.listLibrary(layer).then(setItems).catch(() => {});
  }, [layer, refreshKey]);

  if (items.length === 0) return null;

  const toggleRow = (id: string) =>
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-slate-600 hover:text-slate-800"
      >
        <span>
          {t("library.itemCount", { count: items.length })}
        </span>
        <span className="text-slate-400">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="mt-3 overflow-x-auto rounded border border-slate-200">
          <table className="w-full text-xs">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-3 py-2">{t("library.col.id")}</th>
                <th className="px-3 py-2">{t("library.col.type")}</th>
                <th className="px-3 py-2">{t("library.col.priority")}</th>
                {layer === "playbook" && <th className="px-3 py-2">{t("library.col.rule")}</th>}
                <th className="px-3 py-2">{t("library.col.text")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => {
                const isExpanded = expandedRows.has(item.item_id);
                const text = isExpanded ? item.text : item.text.slice(0, 120) + (item.text.length > 120 ? "…" : "");
                return (
                  <tr key={item.item_id} className="align-top hover:bg-slate-50">
                    <td className="px-3 py-2 font-mono text-slate-400 whitespace-nowrap">{item.item_id}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <Chip label={item.type} cls="bg-slate-100 text-slate-600" />
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <Chip label={item.priority} cls={PRIORITY_STYLES[item.priority] ?? "bg-slate-100 text-slate-600"} />
                    </td>
                    {layer === "playbook" && (
                      <td className="px-3 py-2 whitespace-nowrap">
                        {item.rule && (
                          <Chip
                            label={t(`library.rule.${item.rule}`, { defaultValue: item.rule })}
                            cls={RULE_STYLES[item.rule] ?? "bg-slate-100 text-slate-600"}
                          />
                        )}
                      </td>
                    )}
                    <td className="px-3 py-2 text-slate-600 leading-relaxed max-w-xs">
                      <span
                        className="cursor-pointer"
                        onClick={() => toggleRow(item.item_id)}
                        title={isExpanded ? "" : item.text}
                      >
                        {text}
                        {item.text.length > 120 && (
                          <span className="ml-1 text-indigo-500">
                            {isExpanded ? t("library.collapse") : t("library.expand")}
                          </span>
                        )}
                      </span>
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

// ---------------------------------------------------------------------------
// Upload section (playbook or standard-terms)
// ---------------------------------------------------------------------------

interface SectionProps {
  layer: Layer;
  title: string;
  desc: string;
}

function UploadSection({ layer, title, desc }: SectionProps) {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const job = useJobPolling(jobId, 500);

  useEffect(() => {
    if (job?.status === "completed") {
      setRefreshKey((k) => k + 1);
      setJobId(null);
      setFiles(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [job?.status]);

  async function handleUpload() {
    if (!files?.length) return;
    setError(null);
    try {
      const result = await api.uploadLibraryFiles(layer, files);
      setJobId(result.job_id);
    } catch (e) {
      setError(t("library.error", { message: String(e) }));
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFiles(e.target.files);
    setError(null);
  }

  const running = !!jobId && job?.status !== "completed" && job?.status !== "failed";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="mb-1 text-base font-semibold text-slate-800">{title}</h2>
      <p className="mb-4 text-sm text-slate-500">{desc}</p>

      {/* File drop zone */}
      <div
        className="cursor-pointer rounded-md border-2 border-dashed border-slate-300 px-4 py-5 text-center text-sm text-slate-500 transition-colors hover:border-blue-400 hover:text-blue-600"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const dt = e.dataTransfer.files;
          if (dt?.length) { setFiles(dt); setError(null); }
        }}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.docx,.yaml,.yml"
          className="hidden"
          onChange={handleFileChange}
        />
        {files?.length
          ? Array.from(files).map((f) => f.name).join(", ")
          : t("upload.dropHint")}
      </div>

      <button
        disabled={!files?.length || running}
        onClick={handleUpload}
        className="mt-3 rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {running ? t("library.uploading") : t("library.uploadBtn")}
      </button>

      {running && job && <ProgressPanel job={job} />}

      {job?.status === "completed" && (
        <p className="mt-3 text-sm text-green-700">{t("library.uploadDone")}</p>
      )}

      {(error || job?.status === "failed") && (
        <p className="mt-3 text-sm text-red-600">
          {error ?? t("library.error", { message: job?.error ?? "unknown" })}
        </p>
      )}

      {/* Items viewer */}
      <LibraryItemsPanel layer={layer} refreshKey={refreshKey} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Library() {
  const { t } = useTranslation();
  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-semibold">{t("library.title")}</h1>
      <UploadSection
        layer="playbook"
        title={t("library.playbookTitle")}
        desc={t("library.playbookDesc")}
      />
      <UploadSection
        layer="standard-terms"
        title={t("library.stdTermsTitle")}
        desc={t("library.stdTermsDesc")}
      />
    </div>
  );
}
