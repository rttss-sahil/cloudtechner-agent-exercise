# CloudTechner — Agent Setup Exercise: Functional Requirements Document

- **Version:** 1.0
- **Language:** Python 3 (preferred)
- **Scope:** Q&A agent over the `runbooks/` corpus + evaluation harness + packaged deliverable

---

## 1. Purpose

Build an agent that answers operational questions about a fictional company's services by
grounding answers in the `runbooks/` corpus (12 docs across `checkout-api`,
`payments-api`, `inventory-api`, and general process docs). The corpus intentionally contains
**near-duplicate docs** — same structure, very similar wording, but for a *different service* or
*different failure mode*. The agent must not force a citation to a doc that does not actually
answer the question.

## 2. Stakeholders / Users

| Role | Need |
|---|---|
| Interviewer / evaluator | A runnable, measured prototype; evidence of grounded reasoning and honest "no match" behavior |
| On-call engineer (subject) | Fast, grounded answers with citations; explicit "no match" when unknown |

## 3. Functional Requirements

### FR-1 — Entry point
- Provide a function `answer_question(question: str) -> dict` in Python.
- Must be importable/callable with no setup beyond running the provided instructions.

### FR-2 — Return contract
The returned dict MUST contain exactly these keys:

| Key | Type | Example |
|---|---|---|
| `answer` | str | Natural-language answer, grounded in citations |
| `cited_doc_ids` | list[str] | `["RB-002", "RB-012"]` — may be `[]` |
| `confidence` | str | one of `"high"`, `"medium"`, `"low"`, `"no match"` |

### FR-3 — Citation discipline
- `cited_doc_ids` MUST only include docs the answer is genuinely grounded in.
- MUST NOT force a citation to the closest-sounding document if it does not actually answer the question.
- Near-duplicate docs (right structure, wrong service / wrong failure mode) MUST NOT be cited for a question they do not cover.

### FR-4 — "no match" semantics
- When no doc in the corpus actually answers the question:
  - `confidence` MUST be `"no match"`
  - `cited_doc_ids` SHOULD be `[]`
  - `answer` SHOULD state explicitly that no applicable doc was found.
- `"no match"` is a legitimate, expected return for some inputs.

### FR-5 — Confidence semantics
- `confidence` MUST be derived from the strength of the retrieval/grounding evidence:
  - `high` — clear, specific match (e.g., doc refers to the exact service + exact failure mode asked about).
  - `medium` — relevant doc but partial/indirect coverage.
  - `low` — weak or tangential signal.
  - `no match` — nothing applicable.
- The mapping logic MUST be documented in the write-up.

### FR-6 — Evaluation harness
- A runner that accepts a list of `(question, expected)` pairs where `expected` is a list of doc IDs or `None` (meaning "expect no match").
- For each case, MUST classify the outcome into at least these four buckets:
  1. **correct** — cited the right doc(s)
  2. **wrong** — cited the wrong doc(s)
  3. **correct no-match** — returned no match when expected
  4. **incorrect no-match** — returned no match when a doc did apply
- MUST report a score (e.g., pass rate), not just printed output.

### FR-7 — Example suite
- The harness MUST be preloaded with the 5 official example questions + expected doc IDs:
  1. "checkout-api is running hot on CPU — what should I check first?" → `["RB-001"]`
  2. "'too many connections' errors on checkout-api — likely cause?" → `["RB-002"]` (citing `RB-012` also good, not required)
  3. "How do I safely roll back checkout-api?" → `["RB-005"]`
  4. "checkout-api incident on 2026-08-10 — root cause and fix?" → `["RB-011"]`
  5. "What's our policy for communicating an incident to customers?" → `["RB-012"]`
- Note: OCR of the screenshot garbled rows 4–5; VERIFY the exact expected IDs against the original assignment PDF before running.
- Harness output against these 5 MUST be included in the deliverable.

### FR-8 — Retrieval approach (choice is open)
Any of: keyword (BM25 / TF-IDF), embeddings, hybrid, or LLM reading the full corpus per query.
- The chosen approach MUST be explained in the write-up: why it was chosen, what it handles well, what it does not (esp. near-duplicate discrimination, multi-doc grounding, no-match detection).

### FR-9 — Error / robustness
- Unknown questions must be handled gracefully (`"no match"`), never an exception.
- Confidence must not be inflated for weak matches.

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | Runs locally on the candidate's machine; no mandatory paid external services (open-source libs OK: `scikit-learn`, `fuzz`, `sentence-transformers`, `chromadb`, etc.) |
| NFR-2 | `answer_question` responds within a few seconds per question |
| NFR-3 | Code is runnable as-is with clear one-page instructions (deps, install, run harness) |
| NFR-4 | Deterministic enough to reproduce harness results across runs |
| NFR-5 | Deliverable packaged as a repo or zip: code + harness + harness output + README + write-up |

---

## 5. Acceptance Criteria

- [ ] `answer_question(question: str) -> dict` exists and honors the FR-2 contract.
- [ ] Harness scores all 5 official examples and reports the pass rate.
- [ ] At least one "no match" case is exercised and scored before submission (self-added).
- [ ] At least one near-duplicate trap case is exercised and scored (e.g., CPU-hot question about `payments-api` when the doc is about `checkout-api`).
- [ ] README: 5 minutes or fewer to run the prototype on a fresh machine.
- [ ] Write-up explains retrieval choice, confidence rule, and failure modes.

---

## 6. Out of Scope

- No UI/API server required.
- No multi-turn chat memory required.
- No production deployment or CI required.
- No need to preprocess/rewrite the runbooks beyond indexing.

---

## 7. Suggested Build Order

1. Inventory: read all 12 runbooks; note services, failure modes, near-duplicate clusters. (30 min)
2. Index + retrieval: choose approach (recommend hybrid: keyword recall + doc similarity for rerank/confidence). (1–1.5h)
3. Agent core: `answer_question` wiring retrieval → answer template → confidence mapping → no-match handling. (1h)
4. Harness: 4-bucket classifier + scoring + report. (45 min)
5. Run official 5 examples + adversarial self-tests; iterate. (45 min)
6. Write-up + README + package as repo/zip. (45 min)