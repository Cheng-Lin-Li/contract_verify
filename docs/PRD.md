# contract_verify — Product Requirements Document

**Requirements Coverage for Business Contracts**

| | |
|---|---|
| **Version** | 0.9.0 (MVP) |
| **Status** | Design guideline |
| **Positioning** | Coverage-first · three-layer verification |
| **Deployment** | On-premises, cloud, or hybrid · data-residency configurable · air-gap capable |
| **Classification** | Confidential |

> **One-line positioning.** contract_verify verifies every contract against three reference layers at once — the business stakeholder's deal requirements (scattered across emails, PDFs, Word documents, and attachments), the company's internal playbook, and standard market terms — confirming what was captured and flagging every gap, with each result cited back to its source.

---

## 1. Problem & Opportunity

When a business stakeholder negotiates a contract, the things they actually need — net-60 payment, a data-deletion clause, an SLA credit, a delivery date, a liability cap — are stated incrementally and informally across many channels: email threads, PDF term sheets, Word redlines, and meeting attachments. By the time a final contract arrives, no one systematically checks whether all of those requirements survived into the signed document.

This is a coverage gap that no existing tool closes:

- **Requirements live in scattered, unstructured sources.** Negotiation happens over long email trails and marked-up drafts; teams reconcile feedback across multiple email threads with no single source of truth.
- **Business stakeholders are not lawyers.** They own the requirements but cannot reliably verify, clause-by-clause, that the legal language captures them.
- **Verification today is manual or skipped.** Confirming coverage means re-reading the contract against a dozen threads by hand — so it is done badly, or not at all, and gaps surface only later as disputes.
- **The cost is measurable.** Poor contract management costs companies a meaningful share of annual revenue, much of it from terms that were agreed but never properly captured.

**The core gap.** Existing tools answer *"is this contract risky?"* against a generic playbook. Almost no tool answers the question the business stakeholder actually has: *"did the contract include everything I asked for?"* That question can only be answered by reconciling the final contract against the specific, scattered requirement sources for *this* deal.

---

## 2. Product Vision

contract_verify is a contract-verification engine that checks every contract against **three reference layers** at once:

1. The deal's **business requirements**, scattered across emails, PDFs, DOCX, and attachments.
2. The company's **internal playbook** of approved positions.
3. **Standard, market-expected contract terms.**

It ingests these sources, extracts each reference set into structured items, and verifies line-by-line whether the draft or executed contract satisfies them — producing a unified verification report with citations to both the reference item and the matching (or missing) contract clause.

Requirements coverage is the lead and the differentiator; playbook compliance and standard-terms completeness run in the same pass so nothing falls through the cracks.

> **Core belief.** A business stakeholder should never have to wonder whether the contract captured what they asked for — or whether it quietly violated company policy or dropped a standard protection. All three checks should be automatic, grounded, and explainable: every *covered*, *compliant*, and *missing* cites its evidence.

---

## 3. Users & Personas

The primary user is the **business stakeholder** — not a lawyer — who owns the deal's requirements and must confirm they were met. The supervising attorney is the escalation path for contradictions and high-risk gaps.

### Operator — the Business Stakeholder (primary)

- Role: Operations / Procurement / Finance / Sales lead who owns the deal.
- Not a lawyer; owns the business requirements, not the legal language.
- Pain: *"I asked for net-60, a data-deletion clause, and an SLA credit — did all of that actually make it into the final contract?"*
- Today: re-reads the contract against a dozen email threads and attachments by hand, or just signs and hopes.
- Success: a coverage report confirming every requirement is reflected, with the gaps flagged before signature.

### Supervising Attorney (secondary)

- Role: fractional or in-house supervising attorney; final sign-off.
- Engagement: reviews only flagged gaps, contradictions, and high-risk items.
- Pain: business teams bring contracts late and cannot articulate what they asked for.
- Goal: trust that routine coverage is verified automatically; spend judgment on real conflicts.
- Success: contradictions and missing high-priority terms surface with citations, not buried in email.

**Secondary stakeholders** supply requirements that must be covered: Finance (payment terms), Security/IT (data processing, deletion, DPA), HR (employment terms), Procurement (delivery, SLAs, pricing).

---

## 4. Why an AI-Native Coverage Engine Fits the Gap

### 4.1 The unserved question

SMBs rarely have in-house counsel before roughly $5–10 M ARR, and outside review is slow and expensive. But even when a lawyer reviews for risk, no one confirms the business requirements were captured — that is a business question, not a legal one, and it falls between the cracks.

### 4.2 Economic fit

A full-time GC at a high-growth private company runs roughly $300K–$415K+ in total compensation; a fractional GC retainer runs roughly $60K–$120K/year. contract_verify targets a low monthly subscription, giving the business stakeholder self-service coverage confirmation and reserving scarce attorney time for genuine contradictions and risk.

### 4.3 Competitive landscape — and the open gap

Re-checked against the coverage framing, the direct competition thins out sharply. The mechanic (requirement extraction + coverage matrix) is proven, and obligation-from-email extraction exists — but no one aims this at the SMB business stakeholder verifying a commercial contract.

| Category | Example players | Fit vs. our wedge |
|---|---|---|
| **Requirements coverage for business contracts** | — open gap — | **THIS PRODUCT** |
| Enterprise AI-native CLM | Sirion | Closest — extracts email obligations, links to terms; enterprise tier, post-signature focus |
| Proposal / RFP traceability | VisibleThread, Reqchecker | Same mechanic, wrong direction (proposal → RFP), GovCon buyers |
| Generic AI contract review | LegalOn, Spellbook, Ivo, ContractKen | Adjacent — flags risk / "missing clauses" vs. a playbook, not your deal asks |
| AI law firms for SMBs | Superlegal, Paralex | Adjacent — provide the lawyer; risk redline, not coverage |
| Horizontal AI | Claude, ChatGPT, Copilot | Substitute — general-purpose, manual, ungrounded |

**Strategic verdict.** A generic "AI contract reviewer" is **not** needed — that market is saturated. A requirements-coverage engine for the SMB business stakeholder **is** an open gap. Pairing coverage verification with **flexible, data-residency-aware deployment — on-premises, cloud, or hybrid** — is the moat: the email threads and attachments that hold the requirements are exactly the sensitive material many customers will not send to a third-party cloud, yet others want the convenience and scale of a managed cloud or a hybrid split. The same product serves all three without a fork: sensitive data can stay on-premises while compute or public-facing applications run in the cloud.

---

## 5. Core Capability: The Three-Layer Verification Engine

The engine verifies each contract against three reference layers in a single pass.

| Layer | Reference set | Question answered | Output |
|---|---|---|---|
| **1 · Business Requirements** | Deal sources: emails, PDFs, DOCX, attachments, conversation exports | *"Did the contract capture what I asked for in THIS deal?"* | Coverage Score + per-requirement status |
| **2 · Internal Playbook** | Company-approved clause library; preferred positions; must-have / must-not-have rules | *"Does the contract comply with OUR standard positions?"* | Playbook Compliance: Compliant / Deviation / Violation |
| **3 · Standard Contract Terms** | Market/legal baseline for the contract type (governing law, notices, severability, LoL, etc.) | *"Is the contract complete and well-formed by market standard?"* | Completeness: Present / Missing / Non-standard |

The engine runs in six grounded, auditable stages:

1. **Source & reference ingestion** — accept deal sources (emails inline + attachments, PDFs, DOCX, conversation exports) and load the company playbook and standard-terms library for the contract type.
2. **Reference extraction** — parse each layer into structured items (id, text, source reference, type, priority).
3. **Reconciliation** — within Layer 1, deduplicate and detect supersession/contradiction across sources (a later "net-60" overrides an earlier "net-30"); across layers, flag where a deal requirement conflicts with a playbook rule.
4. **Verification matching** — match every reference item to the contract clause(s) that satisfy it and assign a per-layer status.
5. **Unified report** — produce the Coverage Score plus Playbook-Compliance and Completeness summaries, as a single per-item table where each row cites the reference item *and* the matching (or missing) contract clause.
6. **Gap routing** — route high-priority Missing / Partial / Contradicted requirements, playbook Violations, and missing standard protections to the stakeholder and — above risk/contradiction thresholds — to the supervising attorney.

**Layer-1 coverage status taxonomy**

| Status | Meaning | Action |
|---|---|---|
| Covered | Requirement fully reflected in the contract | Pass; cite clause |
| Partial | Partially reflected; key detail differs or missing | Flag for stakeholder |
| Missing | Requirement absent from the contract | Flag + draft insert |
| Contradicted | Contract directly conflicts with the requirement | Escalate to attorney |
| Superseded | A later source overrode this requirement | Use latest; log trail |

---

## 6. Verification Scores

Each layer produces its own grounded result; together they drive the unified report and routing.

### 6.1 Coverage Score (Layer 1 — headline)

The priority-weighted share of the deal's business requirements the contract satisfies.

```
CVS = Σ(priority_weight × coverage_credit) / Σ priority_weight × 100

priority_weight : Critical = 4, High = 3, Medium = 2, Low = 1
coverage_credit : Covered = 1.0, Partial = 0.5, Superseded(latest covered) = 1.0,
                  Missing = 0, Contradicted = 0 (forces an attorney flag)
```

### 6.2 Playbook Compliance (Layer 2)

Per company-approved position: **Compliant**, **Deviation** (within tolerance, logged), or **Violation** (must-have absent or must-not-have present). Any Violation blocks auto-confirmation and is routed to the attorney.

### 6.3 Standard-Terms Completeness (Layer 3)

Per expected market term for the contract type: **Present**, **Missing**, or **Non-standard**. Missing core protections (e.g. limitation of liability, governing law) are surfaced even when the business stakeholder never thought to ask for them.

### 6.4 Confidence Score (gates all three)

Coverage matching is only useful if the system knows when it might be wrong.

```
CS = 0.30·extract + 0.30·match + 0.20·(1 − contradiction) + 0.15·llm + 0.05·source

CS < 0.70   → route to human confirmation (even if status reads positive)
CS ≥ 0.85   → eligible for auto-confirmation
```

### 6.5 Risk Score (supporting)

The risk layer answers *"is anything here against policy or missing a standard protection I did NOT think to ask about?"* A 0–100 Risk Score aggregates playbook Violations and missing/non-standard core terms and contributes to attorney-routing decisions alongside coverage gaps.

**Combined auto-confirmation gate.** A contract is never auto-confirmed while any of the following is open: a Critical requirement Missing/Contradicted (L1); a playbook Violation (L2); a core standard protection Missing (L3); or any determination with CS < 0.70.

---

## 7. Product Feature Scope (v0.9.0)

This is the full 0.9.0 product scope, delivered across the roadmap in §9. The 2-day MVP ships the core verification subset (CLI-only); the remaining capabilities land within the three-month build.

- Ingest PDF, DOCX, and email (inline + attachments) deal sources, the company playbook, the standard-terms library, and the contract; OCR engine switchable via `.env`.
- **Layer 1** — extract structured business requirements with source citations, type, priority, and binding status; reconcile (dedupe, supersession, contradiction).
- **Layer 2** — load the internal playbook (approved clauses, must-have / must-not-have positions) and check the contract for Compliant / Deviation / Violation.
- **Layer 3** — load the standard-terms library per contract type and check for Present / Missing / Non-standard core protections.
- Verify all three layers in one pass and produce a unified report: Coverage Score + Playbook Compliance + Completeness, each row citing the reference item and the matching contract clause, with confidence scores.
- Gap routing: stakeholder action list + attorney queue for contradictions, playbook Violations, missing standard protections, and high-risk gaps with full context.
- Privilege-aware access controls and a full immutable audit trail of every reference-to-clause link and model action.
- CLI for function-level testing of each stage; self-hosted local-LLM default with cloud switch via `.env`.
- **Deploys on-premises, in the cloud, or hybrid:** every component (LLM, OCR, database, blob storage, audit) can independently run on customer-controlled infrastructure or in a cloud tenant. In the on-premises configuration nothing leaves the host and the system is fully air-gap capable; in hybrid, sensitive data (documents, database, audit) stays on-premises while compute or public-facing applications run in the cloud. The choice is configuration (`DEPLOYMENT_MODE` plus per-component provider/store settings), not a code fork, and a built-in guardrail flags any placement that would move data off the host against the declared mode.

---

## 8. Success Metrics

| Metric | Current baseline | MVP target |
|---|---|---|
| Requirement coverage confirmation | Manual re-read of email threads, or skipped | Automated coverage report per contract |
| Playbook compliance check | Inconsistent; depends on reviewer memory | 100% of contracts checked vs. playbook |
| Standard-terms completeness | Often missed by non-lawyers | Core protections checked on every contract |
| Missed-requirement rate | Unmeasured; surfaces only in disputes | < 3% false-negative on high-priority items |
| Time to full verification | Hours of manual cross-checking | < 10 min from upload to unified report |
| Audit completeness | Incomplete / ad-hoc | 100% of reference-to-clause links logged |

---

## 9. Delivery & Expansion Roadmap

The thesis is proven in a **2-day MVP** and shipped as a production product **within three months**, built with AI coding assistance. The 2-day MVP is the thinnest slice that demonstrates three-layer verification end-to-end; the three months that follow productionize and harden it. Broader legal-operations expansion is deliberately pushed beyond the 3-month window so the core product ships on time.

| Milestone | Timeline | Deliverables |
|---|---|---|
| **MVP** | Days 1–2 | Three-layer verification core on the CLI: ingest PDF/DOCX/email, extract requirements, verify coverage + playbook + standard terms, cited coverage report, audit log; deployment-mode aware (on-prem/cloud/hybrid) configuration + residency guardrail |
| **Month 1** | Weeks 1–4 | Productionize foundations: API service, Postgres + vector retrieval, switchable OCR (Tesseract + PaddleOCR for tables/images), storage/provider interfaces (local or cloud); migrate CLI core into services; containerized for on-prem, cloud, or hybrid bring-up |
| **Month 2** | Weeks 5–8 | Verification depth + UI: reconciliation (supersession, contradiction), all five scores, grounded redline, minimal web UI (upload, report, queue); **English + Japanese localization** (UI switch, JA OCR, JA prompts) |
| **Month 3** | Weeks 9–12 | Workflow, trust & hardening: attorney queue + routing + SLA, RBAC + privilege tagging, immutable audit, supporting risk layer, tests + demo, stabilization; per-deployment-model install guides |
| **Post-launch** | Beyond 3 mo | Managed cloud offering + customer-VPC blueprints, additional languages beyond EN/JA, more OCR/LLM providers, async scale, post-signature obligation tracking, portfolio analytics, CLM/DocuSign, broader legal ops |

Each milestone builds on the prior one behind stable interfaces, so the work is additive rather than a rewrite.

---

## 10. Constraints & Assumptions

- **Deployment-flexible: on-premises, cloud, or hybrid.** The system is declarative about where it runs (`DEPLOYMENT_MODE = on_prem | cloud | hybrid`) and each component's placement is independent. In the default **on-premises** configuration the system runs entirely within the customer's premises and is air-gap capable, with no data leaving the host. In **cloud**, every component runs in a cloud tenant. In **hybrid**, sensitive data (documents, database, audit trail) stays on-premises while compute (e.g. a cloud LLM) or public-facing web applications run in the cloud. A built-in guardrail warns whenever the actual placement of a component contradicts the declared mode.
- **Local LLM default** optimized for an RTX 4070 Ti (16 GB VRAM); cloud LLM switchable via `.env`. The default remains local so the privacy-first promise holds out of the box; cloud is opt-in per deployment model.
- **Localization.** The 2-day MVP ships English (Japanese is an optional demo stretch, since the matching stack is already multilingual). **English + Japanese** — UI language switch, Japanese OCR, and Japanese prompts — is in the 3-month scope; further languages are backlog. The repo skeleton reserves i18n seams so each addition is additive, not a refactor.
- **Not legal advice.** contract_verify verifies coverage and surfaces risk; contradictions and high-risk gaps require supervising-attorney sign-off.
- **Probabilistic extraction.** Requirement extraction from casual sources is probabilistic; the confidence score and human-in-the-loop routing exist precisely because this is the hard part of the problem.
- **Privilege.** Privilege-tagged documents are access-controlled; AI is not run on them without explicit attorney consent.

---

## Appendix — Document Conventions

This PRD is a living document and the authoritative product design guideline. Coverage-credit values, priority weights, confidence thresholds, and SLA targets are baseline values configurable per customer deployment.

**Related documents:** `TDD.md` (technical design), `README.md` (install + demo), `PROMPTS.md` (externalized prompt templates), `AUDIT_SCHEMA.md` (audit trail schema).
