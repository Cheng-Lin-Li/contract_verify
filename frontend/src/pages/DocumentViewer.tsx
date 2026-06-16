// Document viewer: shows all CIR blocks with block IDs, page numbers, and type badges.
// Blocks cited in a verification report are highlighted (pass ?contract_id=... to annotate).
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import type { CIRBlock, CIRDocument, Report } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FORMAT_ICON: Record<string, string> = {
  pdf: "📄", docx: "📝", eml: "✉️", msg: "✉️", txt: "📃",
};

const ROLE_LABEL: Record<string, string> = {
  contract: "Contract",
  deal_source: "Deal source",
  playbook: "Playbook",
  standard_terms: "Standard terms",
};

const TYPE_COLOR: Record<string, string> = {
  paragraph: "bg-slate-100 text-slate-600",
  table:     "bg-blue-100 text-blue-700",
  image:     "bg-purple-100 text-purple-700",
};

// ---------------------------------------------------------------------------
// Block renderer
// ---------------------------------------------------------------------------

interface BlockCardProps {
  block: CIRBlock;
  /** item_ids (r-001, pb-002…) that reference this block */
  annotations: string[];
  highlighted: boolean;
}

function BlockCard({ block, annotations, highlighted }: BlockCardProps) {
  const [expanded, setExpanded] = useState(false);
  const truncLimit = 400;
  const isLong = block.text.length > truncLimit;
  const displayText = isLong && !expanded ? block.text.slice(0, truncLimit) + "…" : block.text;

  return (
    <div
      id={`block-${block.block_id}`}
      className={[
        "rounded-lg border p-4 transition-colors scroll-mt-20",
        highlighted
          ? "border-indigo-300 bg-indigo-50"
          : "border-slate-200 bg-white hover:border-slate-300",
      ].join(" ")}
    >
      {/* Block header row */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-white">
          {block.block_id}
        </span>
        <span className="text-xs text-slate-400">p.{block.page}</span>
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${TYPE_COLOR[block.type] ?? "bg-slate-100 text-slate-500"}`}>
          {block.type}
        </span>
        {annotations.map((id) => (
          <span key={id} className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs text-amber-800">
            {id}
          </span>
        ))}
      </div>

      {/* Content */}
      {block.type === "table" && block.table ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {block.table.map((row, ri) => (
                <tr key={ri} className={ri === 0 ? "bg-slate-50 font-medium" : ""}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="border border-slate-200 px-2 py-1 align-top text-slate-700">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : block.type === "image" ? (
        <p className="italic text-slate-400">[image block — no text content]</p>
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
          {displayText}
          {isLong && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="ml-2 text-indigo-500 hover:underline"
            >
              {expanded ? "less" : "more"}
            </button>
          )}
        </p>
      )}

      {block.ocr_conf != null && (
        <p className="mt-1 text-xs text-slate-400">OCR confidence: {(block.ocr_conf * 100).toFixed(0)}%</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page grouping
// ---------------------------------------------------------------------------

function groupByPage(blocks: CIRBlock[]): Map<number, CIRBlock[]> {
  const map = new Map<number, CIRBlock[]>();
  for (const b of blocks) {
    const pg = b.page ?? 1;
    if (!map.has(pg)) map.set(pg, []);
    map.get(pg)!.push(b);
  }
  return map;
}

// ---------------------------------------------------------------------------
// Document viewer page
// ---------------------------------------------------------------------------

export default function DocumentViewer() {
  const { docId } = useParams<{ docId: string }>();
  const [searchParams] = useSearchParams();
  const contractId = searchParams.get("contract_id");
  const { t } = useTranslation();

  const [doc, setDoc] = useState<CIRDocument | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!docId) return;
    setLoading(true);
    Promise.all([
      api.getDocument(docId),
      contractId ? api.getReport(contractId).catch(() => null) : Promise.resolve(null),
    ])
      .then(([d, r]) => { setDoc(d); setReport(r); })
      .catch((e: unknown) => {
        const status = (e as { response?: { status?: number } })?.response?.status;
        setError(status === 404 ? t("viewer.notFound") : String(e));
      })
      .finally(() => setLoading(false));
  }, [docId, contractId]);

  // Build annotation map: block_id → list of item_ids that reference it
  const annotationMap = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!report || !doc) return map;
    const isContract = doc.role === "contract";
    for (const row of report.rows) {
      if (isContract) {
        // Highlight blocks cited as matched clauses
        for (const bid of row.matched_clause_ids) {
          if (!map.has(bid)) map.set(bid, []);
          map.get(bid)!.push(row.item_id);
        }
      } else {
        // Highlight blocks that are the source of a requirement
        const sc = row.source_citation as Record<string, string> | null | undefined;
        if (sc && sc.doc_id === docId && sc.block_id) {
          if (!map.has(sc.block_id)) map.set(sc.block_id, []);
          map.get(sc.block_id)!.push(row.item_id);
        }
      }
    }
    return map;
  }, [report, doc, docId]);

  const highlightedBlocks = new Set(annotationMap.keys());

  if (loading) return <p className="text-slate-500">{t("common.loading")}</p>;
  if (error || !doc) return <p className="text-red-600">{error ?? t("common.error")}</p>;

  const byPage = groupByPage(doc.blocks);
  const sortedPages = [...byPage.keys()].sort((a, b) => a - b);
  const icon = FORMAT_ICON[doc.format] ?? "📄";
  const roleLabel = ROLE_LABEL[doc.role] ?? doc.role;

  // Metadata fields to show (email headers etc.)
  const metaFields = Object.entries(doc.metadata).filter(([k]) =>
    ["subject", "from", "to", "date", "author", "title"].includes(k)
  );

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      {/* Back link */}
      {contractId ? (
        <Link to={`/report/${contractId}`} className="text-sm text-indigo-600 hover:underline">
          ← {t("viewer.backToReport")}
        </Link>
      ) : (
        <Link to="/library" className="text-sm text-indigo-600 hover:underline">
          ← {t("viewer.backToLibrary")}
        </Link>
      )}

      {/* Document header */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-start gap-3">
          <span className="text-3xl">{icon}</span>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-semibold text-slate-800">{doc.filename}</h1>
            <div className="mt-1 flex flex-wrap gap-3 text-sm text-slate-500">
              <span className="capitalize">{roleLabel}</span>
              <span>·</span>
              <span className="uppercase">{doc.format}</span>
              <span>·</span>
              <span>{doc.pages} {doc.pages === 1 ? t("viewer.page") : t("viewer.pages")}</span>
              <span>·</span>
              <span className="font-mono text-xs text-slate-400">{doc.doc_id.slice(0, 8)}…</span>
            </div>
            {metaFields.length > 0 && (
              <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
                {metaFields.map(([k, v]) => (
                  <div key={k}>
                    <dt className="inline font-medium capitalize">{k}:</dt>{" "}
                    <dd className="inline">{v}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
          <div className="shrink-0 text-right text-sm text-slate-400">
            {doc.blocks.length} {t("viewer.blocks")}
            {highlightedBlocks.size > 0 && (
              <p className="text-xs text-indigo-500">{highlightedBlocks.size} {t("viewer.cited")}</p>
            )}
          </div>
        </div>
      </div>

      {/* Jump to cited blocks shortcut */}
      {highlightedBlocks.size > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
          <span className="font-medium text-amber-800">{t("viewer.citedBlocks")}: </span>
          <span className="flex flex-wrap gap-1.5 mt-1">
            {[...highlightedBlocks].map((bid) => (
              <a
                key={bid}
                href={`#block-${bid}`}
                className="rounded bg-amber-200 px-1.5 py-0.5 font-mono text-xs text-amber-900 hover:bg-amber-300"
              >
                {bid}
              </a>
            ))}
          </span>
        </div>
      )}

      {/* Blocks grouped by page */}
      {sortedPages.map((page) => (
        <div key={page}>
          {doc.pages > 1 && (
            <div className="sticky top-0 z-10 -mx-1 mb-2 rounded bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("viewer.pageLabel", { page })}
            </div>
          )}
          <div className="space-y-3">
            {byPage.get(page)!.map((block) => (
              <BlockCard
                key={block.block_id}
                block={block}
                annotations={annotationMap.get(block.block_id) ?? []}
                highlighted={highlightedBlocks.has(block.block_id)}
              />
            ))}
          </div>
        </div>
      ))}

      {doc.blocks.length === 0 && (
        <p className="text-center text-slate-400">{t("viewer.empty")}</p>
      )}
    </div>
  );
}
