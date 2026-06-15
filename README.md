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

The repo ships the working **MVP** (a CLI-driven verification engine) plus the **3-month scope**: an implemented React frontend and a backend API/service skeleton with TDD specs (see [Frontend & the 3-month scope](#frontend--the-3-month-scope)).

| | |
|---|---|
| **Interfaces** | Click CLI (every pipeline stage runnable headless) · **React + TypeScript SPA** (`frontend/`) — upload, report, attorney queue, EN/JA |
| **API** | FastAPI service skeleton (`backend/app/api`) — auth, contracts, queue, playbook, audit, health — with the shared schema contract |
| **Pipeline** | ingest → extract (3 layers) → reconcile → verify → score → report, fully audited |
| **Grounding** | contract-entity pass (parties, dates, amounts, governing law) cited to blocks; value-aware matching downgrades *Covered* → *Partial* when a key number (cap, net-term, %) differs |
| **LLM** | `ollama` (local default) · `anthropic` (cloud opt-in) · `fake` (deterministic, offline) |
| **Ingestion** | PDF (`pdfminer.six`), DOCX (`python-docx`), email + attachments (stdlib), text/markdown |
| **OCR** | Tesseract (swappable via `OCR_ENGINE`); PaddleOCR/PP-Structure adapter scaffolded for tables & images |
| **Scores** | Coverage · Playbook Compliance · Standard-Terms Completeness · Confidence · Risk |
| **Outputs** | cited HTML + JSON report, append-only JSONL audit trail |
| **Workflow** | attorney queue + routing + SLA, RBAC, and immutable Postgres audit scaffolded for the 3-month build |
| **Localization** | English shipped; **English + Japanese** in the frontend (i18next) |
| **Storage** | SQLite + local filesystem; S3/MinIO blob adapter implemented; Postgres + Qdrant adapters scaffolded |
| **Deployment** | on-premises · cloud · hybrid (data-residency configurable, guardrailed) |

---

## Quickstart A — offline demo (no GPU, no network)

The fastest way to see a full three-layer verification. It uses the built-in **`fake`** LLM provider — a deterministic, rule-based stand-in — so it needs **no GPU, no Ollama, and no internet**. This is also exactly what the test suite runs on.

**Requirements:** Python 3.11+ and these light packages: `click`, `jinja2`, `python-dotenv`, `pyyaml` (and `pdfminer.six` / `python-docx` only if you feed it PDF/DOCX — the sample demo uses text + email).

> **Shell syntax differs between Windows and Unix.** The two things that break when copying commands across shells are **setting an environment variable** and **continuing a command across lines**. Use the column for your shell:
>
> | | bash / zsh (macOS, Linux, WSL, Git Bash) | cmd.exe (Windows) |
> |---|---|---|
> | Set an env var | `export VAR=value` (or inline `VAR=value cmd`) | `set VAR=value` |
> | Line continuation | `\` | `^` |
> | Copy a file | `cp a b` | `copy a b` |
> | Activate the venv | `source .venv/bin/activate` | `.venv\Scripts\activate.bat` |
>
> The instructions below avoid line continuations entirely (each run command is a **single line**), so the only per-shell difference is how you activate the venv and set the provider.

### Steps

**1. Clone and enter the repo**

```bash
git clone https://github.com/Cheng-Lin-Li/contract_verify.git
cd contract_verify
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate          # bash / zsh / WSL / Git Bash
```
```bat
python -m venv .venv
.venv\Scripts\activate.bat         REM cmd.exe (Windows)
```

**3. Install the dependencies** from `requirements.txt`:

```bash
pip install -r backend/requirements.txt
```

Optionally also run `pip install -e .` to get a `contract-verify` command (so you don't have to set `PYTHONPATH`). Both the `contract-verify` form and the `python -m cli.main` form are shown in step 5.

**4. Select the offline provider.** The simplest way is to put it in `.env` (no shell env var needed). Copy the template:

```bash
cp .env.example .env               # bash / zsh
```
```bat
copy .env.example .env             REM cmd.exe (Windows)
```
Open `.env` and change the `LLM_PROVIDER` line to:
```ini
LLM_PROVIDER=fake
```

**5. Run the full pipeline** from the repo root (single line).

If you ran `pip install -e .`, use the `contract-verify` command (identical in every shell):

```bash
contract-verify pipeline --contract samples/contract/contract.txt --sources samples/deal --playbook samples/playbook --stdterms samples/standard_terms --contract-type services --out report.html --json-out report.json
```

Otherwise use `python -m cli.main` with `backend` on `PYTHONPATH`:

```bash
PYTHONPATH=backend python -m cli.main pipeline --contract samples/contract/contract.txt --sources samples/deal --playbook samples/playbook --stdterms samples/standard_terms --contract-type services --out report.html --json-out report.json
```
```bat
set PYTHONPATH=backend
python -m cli.main pipeline --contract samples/contract/contract.txt --sources samples/deal --playbook samples/playbook --stdterms samples/standard_terms --contract-type services --out report.html --json-out report.json
```

You should see a summary like:

```
Coverage 90.0 · Risk 45 · Auto-confirm: False
Blocking reasons:
  - Low confidence (0.67) on r-003
  - ...
HTML report -> report.html
JSON report -> report.json
```

> Run from the **repo root** so the prompt catalog (`backend/prompts/en/PROMPTS.md`) and `.env` resolve. If you didn't set `LLM_PROVIDER=fake` in `.env`, set it for your shell first: bash `export LLM_PROVIDER=fake` (or inline `LLM_PROVIDER=fake ...`); cmd `set LLM_PROVIDER=fake`. If `python` isn't found on Windows, try the launcher `py` instead.

Open **`report.html`** in a browser: one row per reference item across all three layers, each citing its source and the matched/missing contract clause.

> **What the sample demonstrates:** the signed term sheet asks for *net-30* but a follow-up email revises it to *net-45* — the engine marks the older term **Superseded**. The contract omits a **data-deletion** clause and an **indemnity** clause (a core standard protection), so those surface as gaps and the run is **not** auto-confirmed — it routes to the attorney queue.
>
> *Note:* confidence values from the `fake` provider are illustrative (it has no real model uncertainty); with a real model they reflect genuine extraction/match strength.

---

## Quickstart B — local LLM with Ollama (RTX 4070 Ti)

For real extraction quality, point the same pipeline at a local model. This is the **default production configuration** and keeps every document on your host.

**1. Install [Ollama](https://ollama.com/download)** and pull the default models:

```bash
ollama pull qwen3:14b                   # extraction + verification (Q4_K_M, ~9.3 GB)
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
LLM_EXTRACTION_MODEL=qwen3:14b
LLM_VERIFY_MODEL=qwen3:14b
EMBEDDING_MODEL=bge-m3
```

**4. Run the same command without the `fake` override** (set `LLM_PROVIDER=ollama` in `.env`, or just leave the default). With the package installed (`pip install -e .`) it's one line:

```bash
contract-verify pipeline --contract samples/contract/contract.txt --sources samples/deal --playbook samples/playbook --stdterms samples/standard_terms --contract-type services --out report.html
```

For OCR over scanned PDFs, install Tesseract (`sudo apt-get install tesseract-ocr`, or `brew install tesseract`, or on Windows the UB-Mannheim installer) plus `pip install pytesseract Pillow`, and keep `OCR_ENGINE=tesseract`.

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
docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin quay.io/minio/minio server /data --console-address ":9001"
```

The selection is purely configuration — the same code path runs `LocalBlobStore` or `S3BlobStore` depending on `BLOB_DIR`, and `boto3` is imported lazily so the local/offline path never needs it.

**Check your deployment before processing real contracts.** The `doctor` command reports where each component actually runs and warns when that contradicts the declared mode (for example, a cloud LLM under `on_prem` would send document content off the host):

```bash
contract-verify doctor
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

Every stage is runnable on its own, so each function can be tested from the terminal (no frontend required). After `pip install -e .` these work as-is; without the install, replace `contract-verify` with `python -m cli.main` and put `backend` on `PYTHONPATH` (see the note below).

```bash
# Check the deployment model + per-component data residency
contract-verify doctor

# Ingest one document to the canonical representation (prints JSON)
contract-verify ingest   --file samples/contract/contract.txt --role contract
# Extract Layer-1 requirements from a deal source
contract-verify extract  --file samples/deal/term_sheet.txt

# Seed the Layer-2 playbook / Layer-3 standard-terms (preview what loads)
contract-verify playbook seed --dir samples/playbook
contract-verify stdterms seed --dir samples/standard_terms --contract-type services

# Run the whole thing (single line). The JSON report is written next to the HTML automatically.
contract-verify pipeline --contract samples/contract/contract.txt --sources samples/deal --playbook samples/playbook --stdterms samples/standard_terms --contract-type services --out report.html

# Inspect the audit trail for a document
contract-verify audit    --doc-id <uuid> --format json
```

> **Not installing?** Run `python -m cli.main <command>` instead, with `backend` on `PYTHONPATH`, set for your shell: bash `PYTHONPATH=backend python -m cli.main ...`; cmd `set PYTHONPATH=backend` then `python -m cli.main ...`. Run from the **repo root** so prompts and `.env` resolve.

---

## Configuration (.env)

Nothing operational is hardcoded — the OCR engine, LLM provider/model, thresholds, storage paths and logging are all read from `.env`, and all prompts live in `backend/prompts/en/PROMPTS.md`. Copy `.env.example` to `.env` and edit. The most important keys:

| Key | Default | Meaning |
|---|---|---|
| `DEPLOYMENT_MODE` | `on_prem` | `on_prem` · `cloud` · `hybrid` (drives the residency report + guardrail) |
| `LLM_PROVIDER` | `ollama` | `ollama` · `anthropic` · `fake` (offline) |
| `LLM_EXTRACTION_MODEL` | `qwen3:14b` | extraction/verification model |
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

The suite is hermetic — it runs entirely on the `fake` provider (no GPU/network). Run from the repo root.

```bash
# Option 1 — bundled runner (no pytest needed), works in any shell:
python run_tests.py
#   ...or just the scoring tests:
python run_tests.py scoring
```

Option 2 — pytest (if installed). pytest needs `backend` on `PYTHONPATH`; set it for your shell:

```bash
pip install pytest                                   # all shells
PYTHONPATH=backend pytest -q                          # bash / zsh
```
```bat
set PYTHONPATH=backend                                REM cmd.exe (Windows)
pytest -q
```

The tests cover the scoring formulas (coverage / confidence / risk / gate), ingestion and email-attachment folding, reconciliation (dedupe + supersession), the layer-aware matcher, report assembly, the audit trail, an end-to-end pipeline run, and the CLI entry points.

---

## Run the full app (API server + frontend)

The MVP CLI needs no server. To use the **web app**, start the API backend, seed the demo accounts, then start the frontend. Run all backend commands from the **repo root** in your activated venv.

**1. Install the demo API deps** (lightweight — FastAPI + auth, and it pulls in the MVP core; no Postgres/Qdrant/PaddleOCR):

```bash
pip install -r backend/requirements-api.txt
```

**2. Configure** (if you haven't already): `cp .env.example .env` (cmd: `copy .env.example .env`), and set a real `SECRET_KEY` — generate one with `openssl rand -hex 32`. For the offline demo set `LLM_PROVIDER=fake`.

**3. Seed the demo accounts** (creates `var/users.json` with bcrypt-hashed passwords):

```bash
PYTHONPATH=backend python backend/scripts/seed_demo.py
```
```bat
set PYTHONPATH=backend
python backend/scripts/seed_demo.py
```

This prints the demo logins:

| Username | Password | Role | Can see the attorney queue? |
|---|---|---|---|
| `operator` | `operator123` | operator | no — upload + own reports |
| `attorney` | `attorney123` | attorney | yes — queue + decisions |
| `admin` | `admin123` | admin | yes |

> These are **demo-only** credentials. Re-seed any time with `--reset` to wipe and recreate the store. Never use them in production — real deployments use the Postgres-backed user table.

**4. Start the API server** (http://localhost:8000):

```bash
PYTHONPATH=backend python backend/scripts/run_api.py
```
```bat
set PYTHONPATH=backend
python backend/scripts/run_api.py
```

Equivalent raw command: `uvicorn app.api.app:create_app --factory --host 0.0.0.0 --port 8000` (run with `backend` on `PYTHONPATH`). Health check: open `http://localhost:8000/api/health`. Interactive API docs: `http://localhost:8000/docs`.

**5. Start the frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 — proxies /api to :8000
```

Open `http://localhost:5173`, log in with one of the demo accounts above, upload a contract plus its deal sources (use the files in `samples/`), and you'll get the verification report; log in as `attorney` to work the queue.

> **What's wired for the demo:** login/JWT auth + RBAC, contract upload → synchronous verification → stored report, the report view, and the attorney queue. The pipeline runs in-process (fast on `LLM_PROVIDER=fake`). The heavier 3-month pieces (Postgres, Qdrant, Celery, PaddleOCR) remain skeletons behind their interfaces — see below.

---

## Frontend & the 3-month scope

The repo carries the **3-month scope** alongside the working MVP:

- **Frontend (`frontend/`) — implemented.** A React + TypeScript + Tailwind SPA: upload a contract + deal sources, view the unified report (scores, gate, entities, per-item table), and work the attorney queue, with **English + Japanese** localization. See [`frontend/README.md`](frontend/README.md).
- **Demo API server (`backend/app/api`, `core/security`, `auth_store`, `state_store`) — implemented.** A runnable FastAPI backend with JWT auth + RBAC and the upload → verify → report → queue flow (see [Run the full app](#run-the-full-app-api-server--frontend)).
- **Heavier services (`models/orm`, `knowledge/qdrant_store`, `queue/*`, `services/jobs`, `storage/postgres`, OCR `paddle_engine`) — skeleton.** Defined with signatures + docstrings, raising `NotImplementedError`, behind stable interfaces. 3-month deps are in [`backend/requirements-3month.txt`](backend/requirements-3month.txt).
- **TDD specs first (`backend/tests/three_month/`).** Unit-test specifications for the 3-month features (auth/RBAC, SLA, queue routing, Qdrant retrieval, Postgres store, the API endpoints) were written before implementation. They are **skipped by default** (so the MVP suite stays green) and run while implementing with:

  ```bash
  pip install -r backend/requirements-3month.txt
  RUN_3MONTH=1 PYTHONPATH=backend pytest backend/tests/three_month
  ```

  Each spec is the acceptance test for a stub — implement the function until its spec passes.

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
│  ├─ app/
│  │  ├─ (MVP engine) ingestion, references, verify, scoring, report, audit, llm, storage
│  │  └─ (3-month skeleton) api/, core/security.py, models/, knowledge/, queue/, services/, i18n/
│  ├─ cli/            # Click function-test harness (cli/main.py)
│  ├─ prompts/en/     # externalized prompt catalog (PROMPTS.md) — never hardcoded
│  ├─ tests/          # MVP unit + end-to-end tests (run on the fake provider)
│  │  └─ three_month/ # TDD specs for the 3-month features (skipped until implemented)
│  ├─ requirements.txt
│  └─ requirements-3month.txt   # FastAPI, Postgres, Qdrant, PaddleOCR, auth, …
├─ frontend/          # React + TypeScript + Tailwind SPA (upload, report, queue; EN/JA)
│  ├─ src/            # api/, auth/, components/, pages/, hooks/, i18n/, locales/, test/
│  └─ README.md
├─ samples/           # runnable demo: playbook, standard_terms, deal sources, contract
├─ docs/
│  ├─ PRD.md         # product requirements (users, problem, deployment models, roadmap)
│  └─ TDD.md         # technical design (architecture, scope tiers, rationale)
├─ run_tests.py       # dependency-free test runner (also works under pytest)
├─ pyproject.toml
├─ .env.example
└─ README.md
```

A more detailed tree (including the `[i18n]` seams and the service/UI packages) is in [`docs/TDD.md`](docs/TDD.md).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `LLM_PROVIDER=fake ... : command not found` / `not recognized` (Windows) | That inline-env syntax is bash-only. Set `LLM_PROVIDER=fake` in `.env`, or in cmd run `set LLM_PROVIDER=fake` on a separate line first |
| `\` at end of line errors (Windows) | `\` line continuation is bash-only. Use the **single-line** commands in this README (cmd continues with `^`) |
| `ModuleNotFoundError: app` | `pip install -e .` and use `contract-verify`, or run from the repo root with `backend` on `PYTHONPATH` (bash `PYTHONPATH=backend ...`; cmd `set PYTHONPATH=backend`) |
| `contract-verify` not found | Activate the venv, then `pip install -e .`; on Windows ensure the venv is active so its `Scripts\` is on `PATH` |
| `python` not found (Windows) | Use the launcher `py` (e.g. `py -m venv .venv`), or install Python from python.org and tick "Add to PATH" |
| `Prompt catalog not found` | Run from the repo root so `backend/prompts/en/PROMPTS.md` resolves, or set `PROMPTS_DIR` |
| Coverage is 0 / no requirements found | `--sources` must point at a **directory** of deal files (it globs them) |
| Connection refused to `:11434` | Ollama isn't running, or use the offline path with `LLM_PROVIDER=fake` |
| `404 ... /api/chat` from Ollama | Ollama is running but the model tag isn't pulled. Run `ollama list` and either `ollama pull qwen3:14b`, or set `LLM_EXTRACTION_MODEL` / `LLM_VERIFY_MODEL` in `.env` to a tag it shows. Tags must match exactly |
| Want a quick run without a GPU | Set `LLM_PROVIDER=fake` (in `.env` or your shell) |

---

*Not legal advice. `contract_verify` verifies coverage and surfaces risk; contradictions and high-risk gaps require supervising-attorney sign-off.*
