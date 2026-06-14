# contract_verify

**Requirements coverage for business contracts — three-layer verification, deployable on-premises, in the cloud, or hybrid.**

`contract_verify` checks every contract against **three reference layers at once** and tells a business stakeholder — not a lawyer — whether the final document actually captured what the deal needed:

1. **Layer 1 — Business requirements** extracted from the deal's own scattered sources (emails, PDFs, DOCX, attachments): *"Did the contract capture what I asked for?"*
2. **Layer 2 — Company playbook** of approved positions: *"Does it comply with our standard positions?"*
3. **Layer 3 — Standard market terms** for the contract type: *"Is it complete and well-formed?"*

Every result — *Covered*, *Compliant*, *Missing*, *Violation* — cites the reference item **and** the matching (or missing) contract clause. Low-confidence and high-risk items are routed to a supervising attorney. The system runs **on-premises (air-gap capable), in a cloud tenant, or as a hybrid** that keeps sensitive documents and the audit trail on-prem while using cloud compute — the difference is configuration, not code.

> This repository is the **0.9.0 MVP**: the three-layer verification core on a CLI. See [`docs/TDD.md`](docs/TDD.md) for the architecture and [`docs/PRD.md`](docs/PRD.md) for the product framing, including the 3-month productionization plan and the rationale behind every technology choice.

---

## Table of contents

- [What's in the box](#whats-in-the-box)
- [Quickstart A — offline demo (no GPU, no network)](#quickstart-a--offline-demo-no-gpu-no-network)
- [Quickstart B — local LLM with Ollama (RTX 4070 Ti)](#quickstart-b--local-llm-with-ollama-rtx-4070-ti)
- [Switching to a cloud LLM](#switching-to-a-cloud-llm)
- [The CLI](#the-cli)
- [Configuration (.env)](#configuration-env)
- [Running the tests](#running-the-tests)
- [How a run works](#how-a-run-works)
- [Repository layout](#repository-layout)
- [Troubleshooting](#troubleshooting)

---

## What's in the box

| | |
|---|---|
| **Interface** | Click CLI — every pipeline stage is independently runnable (no UI needed) |
| **Pipeline** | ingest → extract (3 layers) → reconcile → verify → score → report, fully audited |
| **Grounding** | contract-entity pass (parties, dates, amounts, governing law) cited to blocks; value-aware matching downgrades *Covered* → *Partial* when a key number (cap, net-term, %) differs |
| **LLM** | `ollama` (local default) · `anthropic` (cloud opt-in) · `fake` (deterministic, offline) |
| **Ingestion** | PDF (`pdfminer.six`), DOCX (`python-docx`), email + attachments (stdlib), text/markdown |
| **OCR** | Tesseract (swappable via `OCR_ENGINE`) |
| **Scores** | Coverage · Playbook Compliance · Standard-Terms Completeness · Confidence · Risk |
| **Outputs** | cited HTML + JSON report, append-only JSONL audit trail |
| **Storage** | SQLite + local filesystem (Postgres/Qdrant/MinIO arrive in the 3-month build) |

---

## Quickstart A — offline demo (no GPU, no network)

The fastest way to see a full three-layer verification. It uses the built-in **`fake`** LLM provider — a deterministic, rule-based stand-in — so it needs **no GPU, no Ollama, and no internet**. This is also exactly what the test suite runs on.

**Requirements:** Python 3.11+ and these light packages: `click`, `jinja2`, `python-dotenv`, `pyyaml` (and `pdfminer.six` / `python-docx` only if you feed it PDF/DOCX — the sample demo uses text + email).

```bash
# 1. Clone
git clone https://github.com/Cheng-Lin-Li/contract_verify.git
cd contract_verify

# 2. (Recommended) virtual environment
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 3. Install the core deps
pip install -r backend/requirements.txt
#   ...or the minimal set for the offline demo only:
#   pip install click jinja2 python-dotenv pyyaml

# 4. Configure (local defaults; no cloud keys needed)
cp .env.example .env

# 5. Run the full pipeline on the bundled sample contract — with the fake provider
LLM_PROVIDER=fake PYTHONPATH=backend python -m cli.main pipeline \
  --contract samples/contract/contract.txt \
  --sources  samples/deal \
  --playbook samples/playbook \
  --stdterms samples/standard_terms \
  --contract-type services \
  --out report.html \
  --json-out report.json
```

You should see a summary like:

```
Coverage 83.33 · Risk 45 · Auto-confirm: False
Blocking reasons:
  - Low confidence (0.69) on r-002
  - ...
HTML report -> report.html
JSON report -> report.json
```

Open **`report.html`** in a browser: one row per reference item across all three layers, each citing its source and the matched/missing contract clause.

> **What the sample demonstrates:** the signed term sheet asks for *net-30* but a follow-up email revises it to *net-45* — the engine marks the older term **Superseded**. The contract omits a **data-deletion** clause and an **indemnity** clause (a core standard protection), so those surface as gaps and the run is **not** auto-confirmed — it routes to the attorney queue.
>
> *Note:* confidence values from the `fake` provider are illustrative (it has no real model uncertainty); with a real model they reflect genuine extraction/match strength.

---

## Quickstart B — local LLM with Ollama (RTX 4070 Ti)

For real extraction quality, point the same pipeline at a local model. This is the **default production configuration** and keeps every document on your host.

**1. Install [Ollama](https://ollama.com/download)** and pull the default models:

```bash
ollama pull qwen3:14b-instruct-q4_K_M    # extraction + verification (~12 GB VRAM)
ollama pull bge-m3                        # embeddings (multilingual)
# Lighter alternative if VRAM is tight:
# ollama pull llama3.3:8b
```

**2. Confirm Ollama is serving** (default `http://localhost:11434`):

```bash
ollama list
```

**3. Point `.env` at Ollama** (this is the default in `.env.example`):

```ini
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_EXTRACTION_MODEL=qwen3:14b-instruct-q4_K_M
LLM_VERIFY_MODEL=qwen3:14b-instruct-q4_K_M
EMBEDDING_MODEL=bge-m3
```

**4. Run the same command without the `LLM_PROVIDER=fake` override:**

```bash
PYTHONPATH=backend python -m cli.main pipeline \
  --contract samples/contract/contract.txt \
  --sources  samples/deal \
  --playbook samples/playbook \
  --stdterms samples/standard_terms \
  --contract-type services \
  --out report.html
```

For OCR over scanned PDFs, install Tesseract (`sudo apt-get install tesseract-ocr`, or `brew install tesseract`) plus `pip install pytesseract Pillow`, and keep `OCR_ENGINE=tesseract`.

---

## Switching to a cloud LLM

Cloud is a strictly **opt-in escape hatch** — never required. Set two variables and the same code routes every call to the cloud provider with no code change:

```ini
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_EXTRACTION_MODEL=claude-sonnet-4-6
EMBEDDING_MODEL=voyage-3
```

Then `pip install anthropic` and run as usual. (OpenAI / Azure OpenAI adapters are on the backlog and currently raise a clear `NotImplementedError`.)

---

## Deployment models

The same build runs three ways — chosen by configuration, never a code change. Declare the intent with `DEPLOYMENT_MODE`, then point each component at a local or cloud provider/store.

| Model | `DEPLOYMENT_MODE` | What runs where | When |
|---|---|---|---|
| **On-premises** | `on_prem` | Everything on a customer-controlled host (LLM, OCR, DB, blobs, audit). Air-gap capable. | Defense, healthcare, finance, legal; maximum data control |
| **Cloud** | `cloud` | Everything in a cloud tenant: cloud LLM, managed DB, object storage. | Customers standardized on a cloud, no on-prem hardware |
| **Hybrid** | `hybrid` | Sensitive data (documents, DB, audit) stays **on-prem**; compute or public-facing pieces (e.g. a cloud LLM, a public web app) run in the **cloud**. | Want cloud accuracy/scale but must keep documents on-prem |

Each component's placement is independent:

- **LLM** — `LLM_PROVIDER=ollama` (local) or `anthropic` (cloud).
- **OCR** — `OCR_ENGINE=tesseract`/`paddleocr` (local library) or a cloud vision API.
- **Database / audit** — a `sqlite://` URL or filesystem path is *local*; a remote `postgresql://` host or `s3://` URL is *cloud*.
- **Blobs (raw documents)** — a filesystem path (`BLOB_DIR=./var/blobs`) keeps uploads *local*; an `s3://bucket/prefix` URL ships them to an **S3-compatible object store** — MinIO on-prem or AWS S3 in the cloud.

### Blob storage on MinIO / S3 (the hybrid blob path)

A hybrid deployment can physically push raw documents to object storage while structured state (the SQLite/Postgres DB and the audit trail) stays on-prem. Set `BLOB_DIR` to an `s3://` URL and provide the connection:

```ini
DEPLOYMENT_MODE=hybrid
BLOB_DIR=s3://cv-bucket/blobs            # bucket + key prefix
S3_ENDPOINT_URL=http://localhost:9000   # MinIO; leave blank for AWS S3
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
DATABASE_URL=sqlite:///./contract_verify.db   # DB stays local
AUDIT_LOG_PATH=./var/audit.jsonl              # audit stays local
```

Then `pip install boto3` (only needed for the `s3://` path). Each ingested file is uploaded under `s3://<bucket>/<prefix>/<doc_id>/<filename>`, the bucket is auto-created if missing, and the resulting `s3://` URI is written to the audit trail. Spin up a local MinIO to try it:

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"
```

The selection is purely configuration — the same code path runs `LocalBlobStore` or `S3BlobStore` depending on `BLOB_DIR`, and `boto3` is imported lazily so the local/offline path never needs it.

**Check your deployment before processing real contracts.** The `doctor` command reports where each component actually runs and warns when that contradicts the declared mode (for example, a cloud LLM under `on_prem` would send document content off the host):

```bash
python -m cli.main doctor
# Deployment mode : hybrid
# Component residency:
#   - llm      : cloud
#   - ocr      : local
#   - database : local
#   - blobs    : local
#   - audit    : local
# No guardrail warnings: placement is consistent with the declared mode.
```

A hybrid profile (cloud LLM for accuracy, documents and audit local) is shown in `.env.example`. Every run also records its deployment mode and data residency to the audit trail.

---

## The CLI

Every stage is runnable on its own, so each function can be tested from the terminal (no frontend required).

```bash
# Check the deployment model + per-component data residency
python -m cli.main doctor

# Ingest one document to the canonical representation (prints JSON)
python -m cli.main ingest   --file samples/contract/contract.txt --role contract
# Extract Layer-1 requirements from a deal source
python -m cli.main extract  --file samples/deal/term_sheet.txt

# Seed the Layer-2 playbook / Layer-3 standard-terms (preview what loads)
python -m cli.main playbook seed --dir samples/playbook
python -m cli.main stdterms seed --dir samples/standard_terms --contract-type services

# Run the whole thing
python -m cli.main pipeline  --contract samples/contract/contract.txt \
                             --sources samples/deal \
                             --playbook samples/playbook \
                             --stdterms samples/standard_terms \
                             --contract-type services --out report.html

# Inspect the audit trail for a document
python -m cli.main audit    --doc-id <uuid> --format json
```

> All commands need `backend` on the path. Either prefix with `PYTHONPATH=backend`, or `pip install -e .` (from `pyproject.toml`) to get a `contract-verify` entry point.

---

## Configuration (.env)

Nothing operational is hardcoded — the OCR engine, LLM provider/model, thresholds, storage paths and logging are all read from `.env`, and all prompts live in `backend/prompts/en/PROMPTS.md`. Copy `.env.example` to `.env` and edit. The most important keys:

| Key | Default | Meaning |
|---|---|---|
| `DEPLOYMENT_MODE` | `on_prem` | `on_prem` · `cloud` · `hybrid` (drives the residency report + guardrail) |
| `LLM_PROVIDER` | `ollama` | `ollama` · `anthropic` · `fake` (offline) |
| `LLM_EXTRACTION_MODEL` | `qwen3:14b-instruct-q4_K_M` | extraction/verification model |
| `EMBEDDING_MODEL` | `bge-m3` | embedding model (multilingual) |
| `OCR_ENGINE` | `tesseract` | swappable OCR backend |
| `BLOB_DIR` | `./var/blobs` | local path, or `s3://bucket/prefix` for MinIO/S3 |
| `S3_ENDPOINT_URL` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | _(empty)_ | object-store connection (used only when `BLOB_DIR` is `s3://`) |
| `CS_HUMAN_REVIEW_THRESHOLD` | `0.70` | below this, a result is routed to a human |
| `CS_AUTO_CONFIRM_THRESHOLD` | `0.85` | at/above this, eligible for auto-confirm |
| `RISK_ATTORNEY_THRESHOLD` | `60` | risk at/above this routes to an attorney |
| `DEFAULT_LOCALE` | `en` | prompt + message catalog (3-month: `en,ja`) |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | structured logging |

---

## Running the tests

The suite is hermetic — it runs entirely on the `fake` provider (no GPU/network).

```bash
# Option 1 — bundled runner (no pytest needed):
python run_tests.py
#   ...or just the scoring tests:
python run_tests.py scoring

# Option 2 — pytest (if installed):
pip install pytest
PYTHONPATH=backend pytest -q
```

The tests cover the scoring formulas (coverage / confidence / risk / gate), ingestion and email-attachment folding, reconciliation (dedupe + supersession), the layer-aware matcher, report assembly, the audit trail, an end-to-end pipeline run, and the CLI entry points.

---

## How a run works

```
deal sources ─┐
 (emails,      │  1 ingest      → Canonical Internal Representation (text/tables/images + citations)
  PDFs, DOCX)  │  2 extract     → Layer-1 requirements  (id, text, type, priority, source)
              ─┤  2b entities   → parties/dates/amounts/governing-law pulled from the contract, cited
              ─┤  3 reconcile   → dedupe + recency-ordered supersession (net-30 → net-45)
 playbook  ────┤  4 verify      → match each item (L1/L2/L3) to clauses; value check tightens Covered→Partial
 std-terms ────┤  5 score       → Coverage · Compliance · Completeness · Confidence · Risk → gate
 contract  ────┘  6 report      → cited HTML/JSON  +  append-only audit trail
                                  └─ low-confidence / violations / missing core terms → attorney queue
```

A contract is **never auto-confirmed** while any of these is open: a Critical requirement Missing/Contradicted, a playbook Violation, a missing core standard protection, or any determination below the confidence threshold.

---

## Repository layout

```
contract_verify/
├─ backend/
│  ├─ app/            # the engine: ingestion, references, verify, scoring, report, audit, llm
│  ├─ cli/            # Click function-test harness (cli/main.py)
│  ├─ prompts/en/     # externalized prompt catalog (PROMPTS.md) — never hardcoded
│  ├─ tests/          # unit + end-to-end tests (run on the fake provider)
│  └─ requirements.txt
├─ samples/           # runnable demo: playbook, standard_terms, deal sources, contract
├─ docs/
│  ├─ PRD.md         # product requirements (users, problem, deployment models, roadmap)
│  └─ TDD.md         # technical design (architecture, scope tiers, rationale)
├─ run_tests.py       # dependency-free test runner (also works under pytest)
├─ pyproject.toml
├─ .env.example
└─ README.md
```

A more detailed tree (including the `[i18n]` seams reserved for the 3-month English+Japanese build and the service/UI packages) is in [`docs/TDD.md`](docs/TDD.md).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: app` | Run from the repo root with `PYTHONPATH=backend`, or `pip install -e .` |
| `Prompt catalog not found` | Run from the repo root so `backend/prompts/en/PROMPTS.md` resolves, or set `PROMPTS_DIR` |
| Coverage is 0 / no requirements found | `--sources` must point at a **directory** of deal files (it globs them) |
| Connection refused to `:11434` | Ollama isn't running, or use the offline path with `LLM_PROVIDER=fake` |
| Want a quick run without a GPU | Prefix any command with `LLM_PROVIDER=fake` |

---

*Not legal advice. `contract_verify` verifies coverage and surfaces risk; contradictions and high-risk gaps require supervising-attorney sign-off.*
