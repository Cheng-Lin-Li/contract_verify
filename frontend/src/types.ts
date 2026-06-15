// Shared types mirroring backend/app/api/schemas.py (the HTTP contract).

export type Role = "operator" | "gc_team" | "attorney" | "admin" | "auditor";
export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface TokenResponse { access_token: string; token_type: string; role: Role; }
export interface User { id: string; username: string; role: Role; }

export interface ScoreSummary {
  coverage_score: number;
  risk_score: number;
  playbook_compliance: Record<string, number>;
  standard_terms_completeness: Record<string, number>;
  auto_confirm: boolean;
  blocking_reasons: string[];
}

export interface ReportRow {
  item_id: string;
  layer: 1 | 2 | 3;
  type: string;
  priority?: string | null;
  status: string;
  confidence: number;
  requirement_text: string;
  source_citation?: Record<string, unknown> | null;
  source_label?: string | null;
  matched_clause_ids: string[];
  superseded_by?: string | null;
  notes: string;
}

export interface Entity { value: string; block_id: string; }

export interface Report {
  contract_id: string;
  scores: ScoreSummary;
  rows: ReportRow[];
  entities: Record<string, Entity[] | string | null>;
  attorney_queue: string[];
}

export interface JobOut {
  job_id: string; contract_id: string; status: JobStatus; progress: number; error?: string | null;
  stage?: string | null;
  current_page?: number | null;
  total_pages?: number | null;
  stage_file?: string | null;
}

export interface QueueItem {
  queue_id: string; contract_id: string; item_id: string; layer: number;
  status: string; reason: string; risk_score: number;
  sla_due_at?: string | null; sla_state: "ok" | "warn" | "breach"; assigned_to?: string | null;
}

export type QueueAction =
  | "approve" | "approve_with_edits" | "request_clarification"
  | "reject" | "escalate" | "add_to_playbook";

export interface Deployment { mode: string; residency: Record<string, string>; warnings: string[]; }

export interface ContractSummary {
  contract_id: string;
  job_id?: string | null;
  status: string;
  coverage_score?: number | null;
  risk_score?: number | null;
  auto_confirm?: boolean | null;
  blocking_count: number;
  submitted_at?: number | null;
  contract_filename?: string | null;
  error?: string | null;
  stage?: string | null;
  progress: number;
}

export interface LibraryItem {
  item_id: string;
  text: string;
  type: string;
  priority: string;
  rule?: string | null;
}
