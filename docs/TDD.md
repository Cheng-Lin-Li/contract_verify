# contract_verify — Technical Design Document

**Three-Layer Contract Verification · On-Premises, Cloud, or Hybrid**

| | |
|---|---|
| **Version** | 0.9.0 (MVP) |
| **Status** | Design guideline |
| **Architecture** | Three-layer verification engine |
| **Deployment** | On-premises, cloud, or hybrid · data-residency configurable · air-gap capable |
| **Classification** | Confidential |

This document is the engineering design guideline for contract_verify. The product verifies every contract against three reference layers — (1) deal business requirements, (2) the company playbook, and (3) standard contract terms — in a single grounded pass. Delivery is split into a **2-day MVP** and a **3-month full project**; the sections below describe the 3-month target architecture, and each major technology choice is given with its rationale and the alternative considered.

> **Deployment is a configuration, not a fork.** The same build runs on-premises, in a cloud tenant, or as a hybrid that keeps sensitive data on-prem while running compute or public-facing pieces in the cloud. See §19.

---

## 1. System Architecture

contract_verify is a modular, service-oriented system. In the MVP all services run on a single self-hosted host (data-sovereign by default); the same stack deploys on-premises, in the cloud, or hybrid, and can run fully air-gapped when on-prem (see §19).

```
UI / CLI        React frontend + Click CLI (function-test harness)
API Gateway     FastAPI — auth, RBAC, privilege enforcement, routing
Orchestration   Celery + Redis — pipeline stages as discrete tasks
Verification    Ingest → Extract (3 layers) → Reconcile → Match → Score → Report
Knowledge       Qdrant (vectors) + PostgreSQL (structured) + MinIO (blobs)
LLM Layer       Ollama (local, RTX 4070 Ti default) ↔ cloud via .env switch
Audit Bus       Append-only PostgreSQL log with immutability trigger
```

The three reference layers are not three separate products — they are three reference sets fed through one verification pipeline. Layer 1 (requirements) is extracted per-deal from uploaded sources; Layers 2 (playbook) and 3 (standard terms) are pre-loaded libraries retrieved at verification time.

Every stateful component — vectors, relational data, blobs, audit — sits behind an interface, so each can be pointed at a local instance (on-prem) or a managed cloud service (cloud/hybrid) without touching application code.

---

## 2. Delivery Plan & Scope Tiers (2-Day MVP · 3-Month Project)

There are two hard deadlines: a 2-day MVP that proves the three-layer thesis end-to-end, and the full project shipped within three months with AI coding assistance. Scope is split into three tiers.

| Capability | 2-Day MVP | 3-Month Project | Backlog (Phase 1+) |
|---|---|---|---|
| Three-layer verification | All three (core) | Hardened | — |
| Interface | CLI only | + minimal React (upload, report, queue) | Playbook builder UI, polish |
| Ingestion | PDF/DOCX/email text-layer | + robust parsing, tables, tracked changes | — |
| OCR | Optional (Tesseract, text-layer) | Tesseract + PaddleOCR/PP-Structure (tables & images) | PaddleOCR-VL (0.9B VLM), EasyOCR, cloud Vision |
| LLM | Ollama or cloud via `.env` | Full provider adapter | OpenAI, Azure OpenAI |
| Orchestration | In-process (sync) | FastAPI + BackgroundTasks | Celery + Redis at scale |
| State / storage | SQLite + filesystem **+ S3/MinIO blob adapter** | Postgres + full storage interface (local or cloud) | — |
| Retrieval | Direct-LLM match (small docs) | Qdrant dense vectors | Hybrid dense + sparse (BM25) |
| Scoring | Coverage + Confidence | + Compliance, Completeness, Risk | — |
| Reconciliation | Basic dedupe | Within-layer supersede / contradict | Cross-layer conflict |
| Report | JSON + simple HTML, cited | + annotated views | DOCX tracked-changes redline |
| Attorney workflow | Flag list in the report | Queue + routing + SLA countdown | Escalation ladder + alerts |
| Access control | Single-user (none) | RBAC + manual privilege tagging | Auto-detect privilege |
| Audit trail | Append-only JSONL / SQLite | Immutable Postgres trigger | — |
| Deployment | On-prem/cloud/hybrid config + residency guardrail (CLI `doctor`) | Per-model Compose profiles + install guides | Managed cloud offering, customer-VPC blueprints |
| Localization | English (JA-ready stack; JA = demo stretch) | English + Japanese (UI + JA OCR + JA prompts) | Further languages + full UI-switch breadth |

**2-Day MVP — minimal stack.** Python 3.11 single process · Click CLI · Ollama local LLM (or cloud via `.env`) · SQLite for state + append-only audit · local filesystem for blobs · pdfminer / python-docx / stdlib-email ingestion · direct-LLM matching over small documents (no vector cluster) · prompts in `prompts/en/PROMPTS.md` · structlog · `DEPLOYMENT_MODE` + per-component residency guardrail. Deliberately **not** in the 2-day MVP: FastAPI service, Celery/Redis, Qdrant, MinIO, React frontend, RBAC/auth, immutable DB triggers, OCR switching.

**Scope guardrail.** Every deferred item sits behind an interface that exists in the MVP (storage adapter, OCR adapter, LLM provider adapter, retrieval interface), so the 3-month work is swap-in, not refactor. The same interfaces are what let storage and LLM be local or cloud per deployment model.

---

## 3. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| Local-LLM default, cloud-switchable | Requirements live in emails and attachments — exactly the sensitive material privacy-constrained customers cannot send to a third-party cloud. Local default keeps the privacy promise out of the box; cloud is an opt-in config flag, not a rewrite. |
| One pipeline, three reference layers | Running coverage, playbook, and standard-terms checks in a single pass guarantees nothing falls through the cracks and lets all three cite the same parsed contract representation. |
| Everything grounded + cited | Every status (Covered / Compliant / Missing) must link to a reference item AND a contract clause, or it is not trusted. This drives the data model and the audit trail. |
| Confidence-gated automation | Extraction from casual sources is probabilistic. A per-determination confidence score routes low-certainty results to humans instead of asserting false positives. |
| Provider/engine abstraction | OCR engine, LLM provider, and every data store are swapped via `.env`, never hardcoded, so the same build runs fully local, fully cloud, or hybrid. |
| Deployment is configuration, with a guardrail | On-prem, cloud, and hybrid are the *same code* selected by `DEPLOYMENT_MODE` plus per-component settings. A residency check (`validate_deployment` / CLI `doctor`) warns whenever a component's real placement would move data off the host against the declared mode — so flexibility never silently breaks the privacy promise. |

---

## 4. Technology Stack — Choices & Rationale

### 4.1 Backend & API

| Component | Choice | Why / alternative |
|---|---|---|
| API framework | FastAPI 0.111+ | Native async (verification is I/O-bound on LLM + DB), automatic OpenAPI docs, Pydantic validation mirroring our reference-item schemas. Alt: Django REST — heavier, sync-first. |
| Validation | Pydantic v2 | Reference items are strongly typed; enforces schema at the API boundary and serializes LLM JSON safely. |
| Task queue | Celery 5.3 + Redis 7 | Each pipeline stage is a retryable task with independent timeouts; LLM calls must not block the request thread. Alt: RQ (weaker), Temporal (heavy for single-host MVP). |
| Auth / RBAC | FastAPI-Users + JWT | Privilege-aware access is a hard requirement; battle-tested auth without building it; JWT keeps the API stateless. |

### 4.2 Data & Knowledge Stores

Each store is reachable as a local instance (on-prem) or a managed cloud service (cloud/hybrid) behind the same interface.

| Component | Choice | Why / alternative |
|---|---|---|
| Vector DB | Qdrant 1.9+ | Self-hostable (data-sovereign) or Qdrant Cloud; native hybrid dense+sparse search, payload filtering to scope retrieval per layer/contract type. Alt: Pinecone (cloud-only), pgvector (weaker hybrid/filtering). |
| Relational DB | PostgreSQL 16 | Reference items, results, users, append-only audit; JSONB for the CIR; row-level triggers enforce audit immutability. Runs locally or as managed Postgres (RDS/Cloud SQL) in cloud/hybrid. |
| Object store | MinIO / S3 | **Implemented in the MVP** as a swappable `BlobStore` (filesystem ⇄ S3-compatible). One `boto3`-backed client targets MinIO on-prem or AWS S3 in the cloud via `S3_ENDPOINT_URL`; selected when `BLOB_DIR` is an `s3://` URL. Alt: raw FS (no metadata). |
| ORM / migrations | SQLAlchemy 2.x + Alembic | Async ORM matching FastAPI; versioned, reviewable schema migrations (the schema is evidence). |

### 4.3 Document Ingestion & OCR

| Component | Choice | Why / alternative |
|---|---|---|
| DOCX parsing | python-docx | Paragraphs, styles, tables, and tracked changes (w:ins/w:del) — must distinguish negotiated edits from final text. |
| PDF text | pdfminer.six | Character-level text with coordinates → precise clause citations. |
| PDF forms | PyPDF2 | AcroForm field extraction for form-style contracts. |
| Email | stdlib `email` + extract-msg | EML/MIME via standard library; extract-msg for Outlook .msg; attachments recursively unpacked. |
| OCR — default | Tesseract 5 | Open-source, fully local, good on clean text scans — right default for data-sovereign deployments and the 2-day MVP. Switchable via `OCR_ENGINE`. |
| OCR — tables & images (3-month) | PaddleOCR / PP-Structure | In-scope because deal sources, emails, and playbooks contain tables and embedded images. PP-Structure does layout analysis + table recognition and runs comfortably on the 16 GB RTX 4070 Ti. |
| OCR — high-accuracy VLM (backlog) | PaddleOCR-VL (0.9B) | SOTA parsing of text/tables/formulas/charts in 109 languages, but very new and needs vLLM-optimized serving to fit 16 GB. Clean drop-in behind the same adapter. |
| OCR — other (backlog) | EasyOCR / cloud Vision | EasyOCR for mixed scripts; cloud Vision when accuracy outweighs data-sovereignty (a cloud OCR call is treated as data egress by the residency guardrail). |

**Table & image handling.** The CIR preserves table blocks as structured row/column matrices and image blocks as extracted blobs (§5). Every table cell and image caption keeps its `block_id` so verification can cite "the SLA table on p.3" as evidence.

### 4.4 LLM & Embeddings

| Component | Choice | Why / alternative |
|---|---|---|
| Local runtime | Ollama (llama.cpp) | One-command CUDA serving on the RTX 4070 Ti; OpenAI-compatible endpoint so the same adapter targets local or cloud. Alt: raw llama.cpp (ops burden), vLLM (heavy for single-GPU MVP). |
| Default extraction model | Qwen3 14B (q4_K_M) | Best instruction-following / structured-JSON balance in the 16 GB-VRAM class (~12 GB). |
| Throughput alternative | Mistral Small 3 / Ministral 3 14B | ~70 tok/s fully on-GPU when speed matters more than peak reasoning. |
| Lightweight fallback | Llama 3.3 8B | ~6–10 GB when running alongside OCR + embeddings on the same card. |
| Embeddings (local) | bge-m3 / nomic-embed-text | Strong retrieval, multilingual (enables Japanese + cross-lingual matching), CPU-friendly. |
| Cloud switch | Anthropic Claude API | `LLM_PROVIDER=anthropic` routes all calls with no app changes; Voyage embeddings on the cloud path. Used in cloud/hybrid, or when a customer accepts cloud and wants peak accuracy. |

### 4.5 Frontend, CLI & Ops

| Component | Choice | Why / alternative |
|---|---|---|
| Frontend | React 18 + Tailwind | Verification report and attorney queue are interactive, citation-linked views; in hybrid the UI can be the public-facing cloud piece while data stays on-prem. |
| CLI | Click 8 | Every pipeline stage callable from the terminal for function tests without the UI; includes `doctor` for the deployment/residency check. |
| Logging | structlog + stdlib logging | Structured JSON logs keyed by doc_id/stage/duration; level and path from `.env`. |
| Containerisation | Docker Compose v2 | One-command bring-up on a single host; the same Compose stack runs on-prem, in a cloud VM/VPC, or split for hybrid; K8s-ready for Phase 1. |

---

## 5. Ingestion Pipeline & Canonical Internal Representation

All inputs — deal sources, the contract, and the two reference libraries — normalise into one **Canonical Internal Representation (CIR)**: structured JSON with text blocks, tables, images, and per-block coordinates for citation.

| Input | Layer | Format | Handling |
|---|---|---|---|
| Deal sources | 1 | EML, PDF, DOCX, attachments | Parsed + OCR as needed; requirements extracted per-deal |
| The contract | target | PDF, DOCX | Parsed to CIR; the document every layer is matched against |
| Company playbook | 2 | DOCX/Markdown library | Loaded once, versioned, embedded into Qdrant |
| Standard-terms library | 3 | Curated YAML/Markdown per contract type | Loaded once, versioned, embedded into Qdrant |

```json
{
  "doc_id": "uuid",
  "role": "deal_source | contract | playbook | standard_terms",
  "format": "pdf | docx | eml",
  "sha256": "...",
  "pages": 4,
  "blocks": [
    { "block_id": "b-001", "type": "paragraph | table | image",
      "page": 1, "bbox": {"x0":72,"y0":144,"x1":540,"y1":168},
      "text": "...", "ocr_conf": 0.97, "table": null }
  ],
  "metadata": { "from": "...", "subject": "...", "date": "..." }
}
```

---

## 6. Reference Data Model (Three Layers)

Each layer extracts into a common reference-item shape so one matcher and one scorer serve all three.

```
ReferenceItem {
  item_id   : str            # r-007, pb-012, st-003
  layer     : 1 | 2 | 3      # requirement | playbook | standard_term
  text      : str
  type      : str            # payment, data, SLA, IP, liability, ...
  priority  : Critical | High | Medium | Low
  source_ref: {doc_id, block_id, page, line}   # Layer 1 only
  rule      : must_have | must_not_have | preferred   # Layer 2 only
  binding   : bool           # signed term sheet vs casual email (Layer 1)
}

VerificationResult {
  item_id, layer, status, matched_clause_ids: [...],
  confidence: 0.00-1.00, evidence: {source_ref, contract_ref}, notes
}
```

**Status enums.** L1: Covered / Partial / Missing / Contradicted / Superseded · L2: Compliant / Deviation / Violation · L3: Present / Missing / Non-standard.

---

## 7. Knowledge Store & Retrieval

- Qdrant collections carry payload fields `layer`, `type`, `contract_type`, `approved`, `jurisdiction` — so retrieval is scoped (e.g. only Layer-2 playbook items for this contract type).
- Hybrid search: dense cosine (0.7) + BM25 sparse (0.3) — catches both semantic matches ("late-payment penalty" ≈ "interest on overdue amounts") and exact terms ("net-60").
- Every retrieval result returns `ref_url` (`/docs/{doc_id}#block-{block_id}`) so the UI and attorney queue deep-link to the exact source passage.

---

## 8. Extraction, Reconciliation & Matching

**Extraction.** LLM-based extraction with a structured prompt (stored in `prompts/en/PROMPTS.md`, never in code) returning a JSON array of `ReferenceItem`s; a rule-based pass (regex/keyword) cross-checks and triggers a second LLM pass on disagreement.

**Reconciliation (Layer 1 + cross-layer).** Within Layer 1: dedupe near-identical asks; detect supersession (later source overrides earlier) and contradiction (conflicting asks) using timestamps + semantic comparison. Cross-layer: flag where a deal requirement conflicts with a playbook must-not-have.

**Contract-entity enrichment.** Before matching, a light rule-based pass (`references/entities.py`) extracts the concrete data points coverage hinges on — **parties, dates, monetary amounts, percentages, payment net-N terms, and governing law** — from the contract CIR, each cited to its block. The result is attached to `contract.metadata['entities']` and recorded in the audit trail. This is deliberately an *internal grounding enrichment*, not a standalone metadata-export feature: its job is to sharpen the verification decision and citations. (Litigation-only fields such as judge names are out of scope — the user is a commercial-contract stakeholder, not a litigator. A learned NER pass can later sit behind the same function.)

**Recency-ordered supersession.** Deal sources are ordered by recency before reconciliation (undated sources first, then by the email `Date` header), so the later revision wins regardless of the order files were supplied or globbed.

**Verification matching.** Each `ReferenceItem` is matched against the contract CIR via hybrid retrieval; the top candidate clauses go to the LLM verifier, which assigns the per-layer status, the matched clause ids, and a confidence score with cited evidence. A deterministic **value-grounding check** then runs on top: if a Layer-1 requirement reads *Covered* but the requirement and the matched clause state different same-kind values (a different liability cap, payment net-term, or SLA percentage), the status is downgraded to *Partial* with a cited note — turning "the topic is covered" into "covered, but a key number differs." Same-value matches are left untouched, and value absence in the clause is not treated as a conflict.

---

## 9. Scoring Engines

**Coverage Score (Layer 1, headline)**

```
CVS = Σ(priority_weight × coverage_credit) / Σ priority_weight × 100
priority_weight : Critical=4, High=3, Medium=2, Low=1
coverage_credit : Covered=1.0, Partial=0.5, Superseded(latest covered)=1.0,
                  Missing=0, Contradicted=0  (Contradicted forces attorney flag)
```

**Playbook Compliance (Layer 2):** Compliant / Deviation (within tolerance, logged) / Violation (must-have absent or must-not-have present). Any open Violation blocks auto-confirmation.

**Standard-Terms Completeness (Layer 3):** Present / Missing / Non-standard. Missing core protections surfaced even when no one asked for them.

**Confidence Score (gates all three)**

```
CS = 0.30·extract + 0.30·match + 0.20·(1-contradiction) + 0.15·llm + 0.05·source
CS < 0.70  → human confirmation (even if status reads positive)
CS ≥ 0.85  → eligible for auto-confirmation
```

**Risk Score (supporting, from Layers 2+3):** a 0–100 aggregate of playbook Violations and missing/non-standard core terms; contributes to attorney routing alongside coverage gaps.

**Combined auto-confirmation gate.** Never auto-confirm while any of: a Critical requirement Missing/Contradicted (L1); a playbook Violation (L2); a core standard protection Missing (L3); or any determination with CS < 0.70.

---

## 10. Explainable Verification Report

- Single per-item table across all three layers; each row shows status, the reference item (with source citation), and the matched/missing contract clause (with clause citation).
- Outputs: HTML (interactive, citation links), annotated DOCX (python-docx tracked changes for proposed inserts), and JSON (for API/CLM and audit storage).
- Report-generation prompts live in `prompts/en/PROMPTS.md`; temperature 0.1 for determinism, second pass at 0.4 only when CS < 0.80.

---

## 11. Attorney Review Queue & Routing

Items route to the attorney queue when any trigger fires: a Critical requirement Missing/Contradicted, a playbook Violation, a missing core standard term, Risk Score ≥ threshold, or any determination with CS < 0.70.

| Context packet item | Content |
|---|---|
| Original sources & contract | Viewer links to deal sources and the contract |
| Unified verification report | Per-item statuses across all three layers, with citations |
| Scores | Coverage, Playbook Compliance, Completeness, Risk, Confidence |
| Proposed redline | Annotated DOCX for missing/partial items |
| Audit snapshot | Full event log to this point (includes deployment mode + residency) |

Attorney actions: approve, approve-with-edits, request clarification, reject, escalate, or add to playbook (which embeds the new position into Qdrant and versions Layer 2). SLA countdown starts on queue entry, with reminder/escalation at 50% / 80% / breach.

---

## 12. Privilege Controls & Access Model

| Role | Can view | Can act |
|---|---|---|
| Operator | Own submissions + verification reports | Submit; view own; download confirmed report |
| GC Team | All submissions + full reports | Review queue; comment; escalate |
| Supervising Attorney | All + audit + privileged docs | All + approve/reject + edit playbook |
| Admin | All + system config | User/role management; configuration |
| Auditor (read-only) | Audit trail + confirmed docs | Export audit log; no writes |

Privileged documents are tagged at ingestion and accessible only to Attorney/Admin; the LLM is never run on them without one-time explicit attorney consent. In hybrid/cloud deployments, privilege tagging can additionally pin a document to local-only processing.

---

## 13. Audit Trail Schema

Every reference-to-clause link and model action is written to an append-only log; a `BEFORE UPDATE/DELETE` trigger makes rows immutable at the DB layer. Each run also records its **deployment mode and data residency**, so an auditor can prove where a given contract was processed.

```sql
CREATE TABLE audit_events (
  event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_id        UUID, actor_role TEXT,
  event_type      TEXT,         -- ingest, extract, reconcile, match, score, route, approve, deployment...
  layer           SMALLINT,     -- 1|2|3|NULL
  doc_id          UUID, item_id TEXT, contract_clause_id TEXT,
  model_name      TEXT, model_version TEXT,
  prompt_hash     TEXT, input_hash TEXT, output_hash TEXT,
  status          TEXT,         -- Covered/Compliant/Missing/...
  confidence      NUMERIC(5,4), risk_score SMALLINT,
  details         JSONB, ip_address INET, session_id UUID
);

CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION audit_immutable();
```

---

## 14. LLM Configuration

**Local default (RTX 4070 Ti, 16 GB VRAM)**

| Task | Model | VRAM |
|---|---|---|
| Extraction / verification | Qwen3 14B q4_K_M | ~12 GB |
| Throughput mode | Mistral Small 3 / Ministral 3 14B | ~13 GB |
| Lightweight fallback | Llama 3.3 8B | ~6–10 GB |
| Embeddings | bge-m3 / nomic-embed-text | ~1–2 GB |

```
DEPLOYMENT_MODE=on_prem             # on_prem | cloud | hybrid
LLM_PROVIDER=ollama                 # ollama | anthropic | openai | azure_openai
LLM_BASE_URL=http://localhost:11434
LLM_EXTRACTION_MODEL=qwen3:14b-instruct-q4_K_M
LLM_VERIFY_MODEL=qwen3:14b-instruct-q4_K_M
EMBEDDING_MODEL=bge-m3
# Cloud / hybrid override:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# LLM_EXTRACTION_MODEL=claude-sonnet-4-6
# EMBEDDING_MODEL=voyage-3
```

---

## 15. Repository Structure

The skeleton carries internationalization seams (marked `[i18n]`). English + Japanese localization is delivered in the 3-month build (§18); the seams keep further languages additive. They are empty placeholders in the 2-day MVP.

```
contract_verify/
├─ backend/app/
│   ├─ api/            # FastAPI routers (ingest, verify, playbook, audit)
│   ├─ core/           # config (incl. deployment-mode + residency), logging, security, privilege
│   ├─ i18n/           # [i18n] message-catalog loader for API/report strings
│   ├─ ingestion/      # parsers + OCR adapter + lang_detect.py [i18n stub]
│   ├─ references/     # layer 1/2/3 extractors + reconciliation
│   ├─ verify/         # matcher + per-layer status engines
│   ├─ scoring/        # coverage, compliance, completeness, confidence, risk
│   ├─ report/         # html/docx/json report + citations
│   ├─ knowledge/      # Qdrant client, embeddings, retrieval
│   ├─ queue/          # attorney queue + routing rules
│   ├─ audit/          # immutable event writer
│   ├─ models/         # SQLAlchemy ORM
│   ├─ storage/        # blob + document store adapters (local FS / S3-compatible)
│   └─ llm/            # provider adapter (ollama/anthropic/openai)
├─ backend/cli/        # Click function-test harness (incl. `doctor`)
├─ backend/prompts/    # en/PROMPTS.md (per-language prompt catalogs [i18n])
├─ frontend/           # React UI (the public-facing piece in hybrid)
├─ docker/             # docker-compose.yml + Dockerfiles (on-prem / cloud / hybrid profiles)
├─ docs/               # PRD.md, TDD.md, AUDIT_SCHEMA.md
├─ .env.example
└─ README.md
```

---

## 16. CLI — Function-Test Harness

```
python -m contract_verify.cli doctor                          # deployment mode + data residency
python -m contract_verify.cli ingest    --file contract.pdf --role contract
python -m contract_verify.cli ingest    --file thread.eml   --role deal_source
python -m contract_verify.cli playbook  seed --dir ./playbook/
python -m contract_verify.cli stdterms  seed --dir ./standard_terms/
python -m contract_verify.cli extract   --doc-id <uuid> --layer 1
python -m contract_verify.cli verify    --contract <uuid>      # all 3 layers
python -m contract_verify.cli score     --contract <uuid>
python -m contract_verify.cli report    --contract <uuid> --out report.html
python -m contract_verify.cli pipeline  --contract contract.pdf --sources ./deal/
python -m contract_verify.cli audit     --contract <uuid> --format json
```

*(In this MVP repo the entry point is `python -m cli.main <command>` with `PYTHONPATH=backend`.)*

---

## 17. Logging

structlog emits JSON logs; level, file path, format, and rotation come from `.env`. Each pipeline stage logs entry + exit with `duration_ms` and `doc_id`. The pipeline additionally logs the deployment mode and component residency at the start of every run, and emits a `deployment_guardrail` warning for any inconsistency.

```
LOG_LEVEL=INFO            # DEBUG|INFO|WARNING|ERROR
LOG_FILE=/var/log/contract_verify/app.log
LOG_FORMAT=json           # json|console
LOG_ROTATION_BYTES=10485760
LOG_BACKUP_COUNT=5
```

---

## 18. Internationalization & Localization (English + Japanese)

The 2-day MVP ships English, with Japanese as an optional demo stretch (the matching stack is already multilingual). **English + Japanese is firmly in the 3-month scope** — UI language switch, Japanese OCR, Japanese prompt catalog, and validation. Further languages and broader UI-switch coverage are backlog.

**Why EN + JA is low-risk:** multilingual models already chosen (bge-m3, Qwen3, and the Claude cloud option); Japanese OCR via PaddleOCR/PP-Structure (already in 3-month scope); externalized prompts and UI strings so adding `ja` is additive. Japanese specifics: no-whitespace segmentation, full/half-width NFKC normalization, vertical-text OCR edge cases, per-source language detection, cross-language matching via bge-m3, and locale formatting (年月日, ¥).

```
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en            # 3-month: en,ja  (further languages: backlog)
```

---

## 19. Deployment Models & Operations (On-Prem · Cloud · Hybrid)

Deployment is **declarative and code-identical** across three models. `DEPLOYMENT_MODE` states the intent; each component (LLM, OCR, database, blobs, audit) is independently pointed at a local or cloud provider/store; and a residency guardrail (`Settings.validate_deployment`, surfaced by the CLI `doctor` command and logged per run) warns when reality contradicts the declared mode.

### 19.1 The three models

| Model | `DEPLOYMENT_MODE` | LLM | OCR | DB / blobs / audit | When |
|---|---|---|---|---|---|
| **On-premises** (default) | `on_prem` | Ollama (local GPU) | Tesseract/Paddle (local) | Local Postgres/MinIO or SQLite/FS | Defense, healthcare, finance, legal; maximum data control; air-gap |
| **Cloud** | `cloud` | Anthropic (or local in a cloud GPU VM) | local lib in-container or cloud Vision | Managed Postgres + S3 + cloud Qdrant | Customers standardized on a cloud, no on-prem hardware |
| **Hybrid** | `hybrid` | Cloud LLM for accuracy/scale | local in-container | **Local** Postgres/MinIO (data stays on-prem) | Want cloud compute or a public web app, but documents/audit must stay on-prem |

**Hybrid is the defining new capability:** sensitive customer data (the deal documents, the relational store, and the audit trail) is pinned to the customer's premises, while compute that benefits from the cloud (a frontier LLM, elastic OCR) or public-facing applications (the React UI behind a cloud load balancer) run in the cloud. Because every store and provider is an interface, this is purely configuration.

### 19.2 Data-residency guardrail

A component is classified `local` or `cloud` from its actual configuration:

- **LLM** — `local` for `ollama`; `cloud` for `anthropic`/`openai`/`azure_openai` (an external API call = document egress).
- **OCR** — `local` for an in-process library (Tesseract/Paddle); `cloud` for a vision API.
- **Database / audit** — `local` for a `sqlite://` URL or filesystem path; `cloud` for a remote `postgresql://` host or `s3://` URL.
- **Blobs** — `local` for a filesystem `BLOB_DIR`; `cloud` for an `s3://` URL. The blob backend is a working adapter in this MVP (`LocalBlobStore` ⇄ `S3BlobStore`): a hybrid run physically uploads each document to MinIO/S3 (key `s3://bucket/prefix/{doc_id}/{filename}`) while the SQLite DB and the audit log stay local, and the resulting `s3://` URI is recorded in the audit trail.

`validate_deployment()` then warns when:

- `on_prem` has **any** cloud component (data would leave the host),
- `cloud` still has a **local data store** (it won't persist/be reachable in a tenant),
- `hybrid` is **degenerate** (no real split — either nothing is cloud, or no data stays local).

```
$ python -m cli.main doctor
Deployment mode : hybrid
Component residency:
  - llm      : cloud
  - ocr      : local
  - database : local
  - blobs    : local
  - audit    : local
No guardrail warnings: placement is consistent with the declared mode.
```

### 19.3 Topologies

| Topology | Description | Mode |
|---|---|---|
| Single-host on-prem (default) | All services via Docker Compose on one customer host with the RTX 4070 Ti. Data never leaves the host. | `on_prem` |
| Air-gapped on-prem | Same stack, zero internet at runtime; weights/images pre-provisioned; cloud disabled. | `on_prem` |
| Multi-host on-prem | GPU/LLM node split from app + DB nodes on the customer LAN. | `on_prem` |
| Hybrid (data-local, compute-cloud) | Documents, Postgres, MinIO, audit on-prem; cloud LLM and/or cloud-hosted UI. | `hybrid` |
| Full cloud / customer VPC | Identical Compose/K8s stack in the customer's cloud tenant with managed stores. | `cloud` |

### 19.4 System requirements (on-prem / hybrid data-plane host)

| Resource | Minimum | Recommended |
|---|---|---|
| GPU | NVIDIA, CC ≥ 8.0, 16 GB VRAM (RTX 4070 Ti) — required only when the LLM runs locally | RTX 4070 Ti / 4080 / A10 (16–24 GB) |
| CPU | 8 cores | 16 cores |
| RAM | 32 GB | 64 GB |
| Disk | 100 GB SSD | 500 GB+ NVMe |
| OS | Ubuntu 22.04 LTS (x86-64) | Ubuntu 22.04/24.04 LTS |
| Runtime | Docker + NVIDIA Container Toolkit, CUDA 12.x | Same, pinned versions |
| Network | None at runtime for on-prem air-gap; outbound HTTPS to the cloud LLM for hybrid | Internal LAN / VPN for users |

*(In hybrid, a GPU is optional if the LLM is the cloud component; the host then just runs the data plane.)*

### 19.5 Air-gapped / offline operation (on-prem only)

- Model weights pre-provisioned (Ollama models, OCR models side-loaded); no runtime pull.
- Container images shipped as tarballs (`docker save / load`); Python wheels and npm packages pinned and vendored.
- No telemetry, no phone-home; licensing offline/key-file based.
- Cloud strictly opt-in: `DEPLOYMENT_MODE`/`LLM_PROVIDER`/`OCR_ENGINE` default to local; the guardrail flags any accidental cloud component.

### 19.6 Data residency & security

In on-prem and in hybrid, all documents, extracted requirements, relational data, and the audit log remain on the customer host/network; only the model prompt/response transits to a cloud LLM if one is configured (hybrid), and privilege-pinned documents can be excluded from that. In cloud, data lives in the customer's tenant. Secrets via `.env` or the customer's secret store; TLS terminated by the customer's reverse proxy.

### 19.7 Backup, restore & upgrade

PostgreSQL (pg_dump + WAL/PITR), Qdrant (collection snapshots), MinIO (bucket backup/replication). Upgrades are versioned container images + Alembic migrations; on a single host: stop → migrate → start. Disaster recovery: restore the three stores onto a fresh host from backup.

### 19.8 Install outline (full steps in README)

```
# 1. Provision host: Docker + NVIDIA Container Toolkit + CUDA 12.x (GPU only if LLM is local)
# 2. Load images (air-gapped):  docker load -i contract_verify-images.tar
# 3. Provision models (local LLM): ollama create / pull
# 4. Configure:                 cp .env.example .env   (set DEPLOYMENT_MODE + providers/stores)
# 5. Verify placement:          python -m cli.main doctor
# 6. Start:                     docker compose up -d
# 7. Migrate + seed:            alembic upgrade head; cli playbook seed; cli stdterms seed
# 8. Smoke test:                python -m cli.main pipeline --contract sample.pdf --sources ./deal/
```

> **Deployment guarantee.** On-prem (incl. air-gapped) keeps everything on the host with no internet required. Hybrid keeps sensitive data on-prem while using cloud compute. Cloud runs everything in the customer's tenant. The guardrail makes the chosen promise verifiable — it refuses to let `on_prem` silently turn into data egress.

---

## 20. Deferred Backlog (Post-3-Month Project)

| # | Item | Interface it slots into |
|---|---|---|
| 1 | Managed cloud offering + customer-VPC blueprints | Deployment / storage + LLM adapters |
| 2 | Additional languages beyond EN/JA + broader UI-switch coverage | `i18n/`, `locales/<lang>/`, `prompts/<lang>/` |
| 3 | PaddleOCR-VL (0.9B VLM); EasyOCR; cloud Vision | OCR adapter |
| 4 | OpenAI / Azure OpenAI providers | LLM provider adapter |
| 5 | Celery + Redis async at scale | Orchestration |
| 6 | Cross-layer conflict reconciliation (requirement vs playbook) | Reconciliation |
| 7 | DOCX tracked-changes redline output | Report |
| 8 | "Add to playbook" learning loop + re-embed | Knowledge store |
| 9 | Post-signature obligation tracking, renewal/drift alerts | Verification + scheduler |
| 10 | Portfolio coverage analytics, counterparty patterns | Analytics |
| 11 | CLM webhooks, DocuSign integration | Integration adapters |

Each backlog item improves scale, breadth, accuracy, or polish on top of a working core, and each lands behind an interface already defined.

---

## Appendix A — Key `.env` Reference

```
APP_VERSION=0.9.0
DEPLOYMENT_MODE=on_prem         # on_prem | cloud | hybrid

DATABASE_URL=sqlite:///./contract_verify.db   # local; or postgresql://host/db (cloud)
BLOB_DIR=./var/blobs                          # local path; or s3://bucket/prefix (MinIO/S3)
# S3/MinIO (used only when BLOB_DIR is s3://):
# S3_ENDPOINT_URL=http://localhost:9000        # blank for AWS S3
# S3_ACCESS_KEY=...
# S3_SECRET_KEY=...
# S3_REGION=us-east-1
AUDIT_LOG_PATH=./var/audit.jsonl              # local path; or s3://bucket/... (cloud)

OCR_ENGINE=tesseract            # MVP:tesseract | 3-mo:paddleocr | backlog:paddleocr_vl,easyocr,google_vision
LLM_PROVIDER=ollama             # ollama | anthropic | openai | azure_openai
LLM_EXTRACTION_MODEL=qwen3:14b-instruct-q4_K_M
EMBEDDING_MODEL=bge-m3

CS_HUMAN_REVIEW_THRESHOLD=0.70
CS_AUTO_CONFIRM_THRESHOLD=0.85
RISK_ATTORNEY_THRESHOLD=60

DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en            # 3-month: en,ja

LOG_LEVEL=INFO
LOG_FILE=/var/log/contract_verify/app.log
LOG_FORMAT=json

SECRET_KEY=<openssl rand -hex 32>
```

All prompts live in `backend/prompts/en/PROMPTS.md` (per-language catalogs in the 3-month build); no prompt text or tunable constant is hardcoded in source.

---

## Appendix B — Where to read this in the MVP code

| Area | Start here |
|---|---|
| Deployment mode + residency guardrail | `app/config.py` (`deployment_mode`, `component_residency`, `validate_deployment`), CLI `doctor` |
| Data shapes | `app/core/models.py`, `app/core/enums.py` |
| Ingestion | `app/ingestion/ingest_service.py` |
| Extraction & reconcile | `app/references/` (`extractor.py`, `reconcile.py`) |
| Contract entities + value-conflict grounding | `app/references/entities.py` (`extract_contract_entities`, `value_conflict`) |
| Matching & retrieval | `app/verify/matcher.py`, `app/retrieval/retriever.py` |
| Scoring & gate | `app/scoring/` |
| Report & audit | `app/report/report_builder.py`, `app/audit/audit_log.py` |
| Storage adapters (local/cloud seam) | `app/storage/store.py` — `BlobStore`/`LocalBlobStore`/`S3BlobStore`, `get_blob_store`, `parse_s3_url` |
| LLM providers | `app/llm/` (`ollama`, `anthropic`, `fake`) |
| Orchestration | `app/pipeline.py` |
| Prompts | `backend/prompts/en/PROMPTS.md` |
| Tests | `backend/tests/` + `run_tests.py` |

*Baseline values (coverage credits, priority weights, confidence thresholds, risk threshold) are configurable per customer deployment. Not legal advice — high-risk gaps require supervising-attorney sign-off.*
