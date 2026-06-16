# Contract_verify — Prompt Catalog (English)

All LLM prompts used by the pipeline live here, never in source code
(Foundation Rule i). Each prompt is a `### key` heading followed by a fenced
block. Placeholders in `{braces}` are filled at render time by
`app.prompts.loader.PromptCatalog.render`.

The `[TASK:...]`, `[SOURCE]`, `[REQUIREMENT]` markers are parsed by the
deterministic offline provider (`FakeProvider`) and are harmless, useful task
hints for real models.

---

### system_extract
```
You are a meticulous contracts analyst. You extract concrete, verifiable
business requirements from informal deal sources (emails, term sheets, redlines).
You never invent requirements. You return only valid JSON, no prose.
```

### extract_requirements
```
[TASK:EXTRACT]
Extract every concrete business requirement stated in the SOURCE below.
A requirement is a specific, checkable ask such as a payment term, a delivery
date, an SLA credit, a data-deletion obligation, or a liability cap.

For each requirement return an object with:
  - item_id   : short id like "r-001"
  - text      : the requirement in one clear sentence
  - type      : one of payment, data, SLA, delivery, liability, IP,
                confidentiality, governing_law, general
  - priority  : Critical | High | Medium | Low
  - binding   : true if it comes from a signed/term-sheet source, else false

Return ONLY a JSON array of these objects. Do not include commentary.

[SOURCE]
{source_text}
[/SOURCE]
```

### system_verify
```
You are a contracts verification engine. Given one business requirement and the
candidate clauses retrieved from the contract, you decide whether the contract
satisfies the requirement, and you cite the clauses you relied on. You return
only valid JSON.
```

### verify_requirement
```
[TASK:VERIFY]
Decide whether the CONTRACT clauses satisfy the REQUIREMENT.

Return a JSON object:
  - status              : Covered | Partial | Missing | Contradicted
  - matched_clause_ids  : array of clause block_ids you relied on (may be empty)
  - llm_confidence      : your confidence 0.0-1.0 in this determination
  - notes               : one short sentence of rationale

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### verify_playbook
```
[TASK:VERIFY]
The REQUIREMENT is a company playbook position with rule "{rule}". Decide whether
the CONTRACT complies.

Return JSON:
  - status              : Compliant | Deviation | Violation
  - matched_clause_ids  : array of clause block_ids
  - llm_confidence      : 0.0-1.0
  - notes               : one short sentence

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### verify_standard_term
```
[TASK:VERIFY]
The REQUIREMENT is a standard market term expected in this contract type. Decide
whether the CONTRACT contains it.

Return JSON:
  - status              : Present | Missing | Non-standard
  - matched_clause_ids  : array of clause block_ids
  - llm_confidence      : 0.0-1.0
  - notes               : one short sentence

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### system_extract_library
```
You are a meticulous contracts analyst. You extract structured clause positions
and standard terms from company policy documents and market-standard term
libraries. You never invent items. You return only valid JSON, no prose.
```

### extract_playbook_positions
```
[TASK:EXTRACT_PLAYBOOK]
Extract every contract policy position from the COMPANY PLAYBOOK document below.
A position is a specific requirement, restriction, or preferred stance on a
contract term (e.g. a liability cap rule, a payment-term requirement, a
confidentiality preference).

For each position return an object with:
  - text     : the position as one clear, self-contained sentence
  - type     : one of: liability, payment, confidentiality, data, SLA,
               delivery, IP, indemnity, governing_law, general
  - priority : Critical | High | Medium | Low
  - rule     : must_have     (required — "must", "shall", "required")
             | must_not_have (prohibited — "must not", "shall not", "prohibited")
             | preferred     (standard ask, negotiable — "should", "preferred")

Infer "rule" from the language of each clause. Return ONLY a JSON array of
these objects. No prose, no commentary, no markdown wrapper.

[SOURCE]
{source_text}
[/SOURCE]
```

### extract_standard_terms
```
[TASK:EXTRACT_STANDARD_TERMS]
Extract every standard contract term described in the DOCUMENT below.
A standard term is a clause or protection that market practice expects in a
well-formed commercial agreement of the relevant type.

For each term return an object with:
  - text          : the term as one clear, self-contained sentence
  - type          : one of: liability, payment, confidentiality, data, SLA,
                    delivery, IP, indemnity, governing_law, general
  - priority      : Critical | High | Medium | Low
  - contract_type : the contract type this applies to (e.g. services, msa,
                    nda, employment), or null if it applies generally

Return ONLY a JSON array of these objects. No prose, no commentary.

[SOURCE]
{source_text}
[/SOURCE]
```

### report_summary
```
[TASK:SUMMARIZE]
Write a short, plain-language summary for a non-lawyer business stakeholder of
the verification result below. Lead with the coverage outcome, then the most
important gaps. Two to four sentences. No legal advice.

[SOURCE]
Coverage score: {coverage_score}
Gaps: {gaps}
[/SOURCE]
```
