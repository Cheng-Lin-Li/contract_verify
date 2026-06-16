// Library page: upload playbook/standard-terms, view existing items and source documents.
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import axios from "axios";
import { api } from "../api/client";
import { useJobPolling } from "../hooks/useContract";
import type { JobOut, LibraryDocInfo, LibraryItem } from "../types";

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
// Rule / priority badges
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
// Items table (one group)
// ---------------------------------------------------------------------------

type Layer = "playbook" | "standard-terms";

function ItemsTable({ items, layer }: { items: LibraryItem[]; layer: Layer }) {
  const { t } = useTranslation();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) =>
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <div className="overflow-x-auto rounded border border-slate-200">
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
            const text = isExpanded
              ? item.text
              : item.text.slice(0, 120) + (item.text.length > 120 ? "…" : "");
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
  );
}

// ---------------------------------------------------------------------------
// Library items panel — grouped by source document
// ---------------------------------------------------------------------------

interface ItemsPanelProps {
  layer: Layer;
  items: LibraryItem[];
  docs: LibraryDocInfo[];
}

function LibraryItemsPanel({ layer, items, docs }: ItemsPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string | null>>(new Set());

  if (items.length === 0) return null;

  // Build a lookup from doc_id → filename.
  const docNameById = new Map(docs.map((d) => [d.doc_id, d.filename]));

  // Group items: null source_doc_id = built-in, otherwise by doc_id.
  const groups = new Map<string | null, LibraryItem[]>();
  groups.set(null, []);
  for (const item of items) {
    const key = item.source_doc_id ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  // Drop the null group if empty.
  if (groups.get(null)?.length === 0) groups.delete(null);

  const toggleGroup = (key: string | null) =>
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-slate-600 hover:text-slate-800"
      >
        <span>{t("library.itemCount", { count: items.length })}</span>
        <span className="text-slate-400">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {Array.from(groups.entries()).map(([docId, groupItems]) => {
            const label = docId
              ? (docNameById.get(docId) ?? t("library.noSourceDoc"))
              : t("library.groupBuiltIn");
            const isGroupExpanded = expandedGroups.has(docId);
            return (
              <div key={docId ?? "__builtin__"} className="rounded border border-slate-200">
                <button
                  onClick={() => toggleGroup(docId)}
                  className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50"
                >
                  <span className="flex items-center gap-2">
                    {docId === null && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-500">
                        {t("library.groupBuiltIn")}
                      </span>
                    )}
                    {docId !== null && (
                      <span className="truncate max-w-[260px]">{label}</span>
                    )}
                    <span className="font-normal text-slate-400">
                      ({t("library.itemCount", { count: groupItems.length })})
                    </span>
                  </span>
                  <span className="text-slate-400">{isGroupExpanded ? "▲" : "▼"}</span>
                </button>
                {isGroupExpanded && (
                  <div className="border-t border-slate-100">
                    <ItemsTable items={groupItems} layer={layer} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Library documents panel — with delete per document
// ---------------------------------------------------------------------------

const DOC_FORMAT_ICON: Record<string, string> = {
  pdf: "📄", docx: "📝", yaml: "📋", yml: "📋",
};

interface LibraryDocsPanelProps {
  layer: Layer;
  docs: LibraryDocInfo[];
  items: LibraryItem[];
  onDeleted: () => void;
}

function LibraryDocsPanel({ layer, docs, items, onDeleted }: LibraryDocsPanelProps) {
  const { t } = useTranslation();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  if (docs.length === 0) return null;

  const itemCountByDoc = new Map<string, number>();
  for (const item of items) {
    if (item.source_doc_id) {
      itemCountByDoc.set(item.source_doc_id, (itemCountByDoc.get(item.source_doc_id) ?? 0) + 1);
    }
  }

  async function handleDelete(doc: LibraryDocInfo) {
    const count = itemCountByDoc.get(doc.doc_id) ?? 0;
    const msg = t("library.deleteDocConfirm", { name: doc.filename, count });
    if (!window.confirm(msg)) return;

    setDeleting(doc.doc_id);
    setDeleteError(null);
    try {
      await api.deleteLibraryDocument(layer, doc.doc_id);
      onDeleted();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        const detail = err.response.data?.detail;
        if (detail?.type === "referenced") {
          setDeleteError(
            t("library.deleteDocReferenced", { count: detail.count })
          );
        } else {
          setDeleteError(
            t("library.deleteDocError", {
              message: typeof detail === "string" ? detail : JSON.stringify(detail),
            })
          );
        }
      } else {
        setDeleteError(t("library.deleteDocError", { message: String(err) }));
      }
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {t("library.sourceDocuments")}
      </p>

      {deleteError && (
        <div className="mb-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {deleteError}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {docs.map((doc) => (
          <div
            key={doc.doc_id}
            className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 pl-3 pr-1 py-1.5 text-sm text-slate-700"
          >
            <span>{DOC_FORMAT_ICON[doc.format] ?? "📄"}</span>
            <Link
              to={`/document/${doc.doc_id}`}
              className="max-w-[160px] truncate hover:text-indigo-700 hover:underline"
            >
              {doc.filename}
            </Link>
            <button
              onClick={() => handleDelete(doc)}
              disabled={deleting === doc.doc_id}
              title={t("library.deleteDoc")}
              className="ml-1 rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
            >
              {deleting === doc.doc_id ? "…" : "✕"}
            </button>
          </div>
        ))}
      </div>
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
  const storageKey = `library_job_${layer}`;
  // Initialise from localStorage so active jobs survive page navigation.
  const [jobId, setJobId] = useState<string | null>(
    () => localStorage.getItem(storageKey)
  );
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDuplicateError, setIsDuplicateError] = useState(false);
  const [uploadCompleted, setUploadCompleted] = useState(false);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [docs, setDocs] = useState<LibraryDocInfo[]>([]);

  function persistJobId(id: string | null) {
    if (id) localStorage.setItem(storageKey, id);
    else localStorage.removeItem(storageKey);
    setJobId(id);
  }

  const job = useJobPolling(jobId, 500, () => persistJobId(null));

  // Fetch items and docs whenever refreshKey changes.
  useEffect(() => {
    api.listLibrary(layer).then(setItems).catch(() => {});
    api.listLibraryDocuments(layer).then(setDocs).catch(() => {});
  }, [layer, refreshKey]);

  useEffect(() => {
    if (job?.status === "completed") {
      setUploadCompleted(true);
      setRefreshKey((k) => k + 1);
      persistJobId(null);
      setFiles(null);
      if (fileRef.current) fileRef.current.value = "";
    } else if (job?.status === "failed") {
      persistJobId(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.status]);

  async function handleUpload() {
    if (!files?.length) return;
    setError(null);
    setIsDuplicateError(false);
    setUploadCompleted(false);
    try {
      const result = await api.uploadLibraryFiles(layer, files);
      persistJobId(result.job_id);
    } catch (e) {
      if (axios.isAxiosError(e) && e.response) {
        const detail = e.response.data?.detail;
        if (detail?.type === "duplicate") {
          setIsDuplicateError(true);
          setError(
            t("library.duplicateUpload", { names: (detail.filenames as string[]).join(", ") })
          );
        } else {
          setError(t("library.error", {
            message: typeof detail === "string" ? detail : JSON.stringify(detail),
          }));
        }
      } else {
        setError(t("library.error", { message: String(e) }));
      }
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFiles(e.target.files);
    setError(null);
    setIsDuplicateError(false);
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

      {uploadCompleted && (
        <p className="mt-3 text-sm text-green-700">{t("library.uploadDone")}</p>
      )}

      {/* Duplicate warning (amber) vs generic error (red) */}
      {error && (
        <p className={`mt-3 text-sm ${isDuplicateError ? "text-amber-700" : "text-red-600"}`}>
          {error}
        </p>
      )}
      {!error && job?.status === "failed" && (
        <p className="mt-3 text-sm text-red-600">
          {t("library.error", { message: job?.error ?? "unknown" })}
        </p>
      )}

      {/* Source documents with delete */}
      <LibraryDocsPanel
        layer={layer}
        docs={docs}
        items={items}
        onDeleted={() => setRefreshKey((k) => k + 1)}
      />

      {/* Extracted items grouped by source document */}
      <LibraryItemsPanel layer={layer} items={items} docs={docs} />
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
