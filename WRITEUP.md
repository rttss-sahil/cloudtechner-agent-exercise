# Write-up — Design Rationale

## The problem

The agent must answer operational questions about a fictional company's services,
grounded in 12 runbooks. Two constraints make this hard rather than trivial:

1. The corpus is **small** (12 docs) but densely similar — the assignment warns
   of near-duplicate runbooks that share *structure and wording* across *different
   services and failure modes*.
2. `confidence == "no match"` must be a first-class answer. Forcing a citation to
   the closest-sounding doc when it doesn't apply is scored as a failure.

This is fundamentally a **retrieval precision** problem, not a generation problem.

## What I chose and why

**Pure-stdlib hybrid lexical retrieval** (no embeddings, no vector DB, no LLM):

- **TF-IDF cosine** (`retrieval.py`) — semantic-ish recall for keywords; robust
  against stopword noise; cheap and explainable on a 12-doc corpus.
- **Token Jaccard** — rewards verbatim shared vocabulary (important for matching
  the exact failure-mode phrasing like `too many connections`).
- **Character 3-gram Jaccard** — tolerates inflection/wording variance
  (`running hot` vs `hot on CPU`) where exact tokens diverge.
- **Service-grounding gate** — the core defense against the traps. Service names
  are extracted from the question (`*-api` tokens + optional aliases) and any
  candidate doc that never mentions the asked-about service is heavily demoted
  (~0.35x). A near-duplicate of RB-001 about `payments-api` therefore cannot win
  a `checkout-api` CPU question even though its wording beats unrelated docs.

### Why not embeddings?
Word (or sentence) embeddings are great when the *semantics* differ but the
words don't — but here the traps are the opposite: **the words are nearly
identical, and the difference is an entity** (service name or failure mode).
Under cosine-in-embedding-space those near-duplicates collapse together, which is
precisely what tends to make a naive RAG answer cite the wrong-service doc. A
lexical scorer + entity gate decisively separates them, and does so with zero
dependencies and full transparency about *why* a doc was chosen or rejected
(diagnostics are attached to every ranked doc).

### Why not an LLM reading the whole corpus per query?
It's a legitimate option, but it makes "no match" and near-duplicate distinction
depend on a prompt and a model's judgment call, which is hard to evaluate
deterministically and hard to defend in an interview write-up. The lexical core
is deterministic: same question → same result, reproducible harness.

## What it handles well

- Exact failure-mode lookups (`too many connections`, `high CPU`, `roll back`).
- Wrong-service traps: the grounding gate demotes the other service's near-dupe.
- Clear no-match cases: threshold-gated, out-of-corpus questions return
  `no match` with empty citations (verified with 5 adversarial questions).
- Explainability: every answer traces to a doc id + the best matching paragraph.

## What it does NOT handle well (honest limits)

- **Synonym shift.** Ask *"the cart page is slow"* and it won't reliably find a
  doc that only says `checkout-api high CPU`. A small fallback: `SERVICE_ALIASES`
  in config covers a few synonyms; the general fix would be an embedding reranker
  layered on top of this lexical core.
- **Threshold sensitivity.** `MATCH_FLOOR`/`CONF_*` are absolute cutoffs tuned on
  the mock corpus. On a very different corpus (longer/shorter docs, more or
  fewer junk docs) they need re-calibration — the harness makes this visible per
  case.
- **Single citation.** The agent cites one top doc. The prompt allows citing
  `RB-012` *in addition* to `RB-002` for the connections question; my single-doc
  contract satisfies the letter of the spec but a multi-doc variant (top-k with a
  margin threshold) is a natural extension.
- **Cross-document answers.** Questions whose answer genuinely spans two docs
  (e.g., policy in one, severity in another) would need multi-doc answer
  synthesis, not just top-1 grounding.
- **No conversational memory / no structured query parsing.** If the corpus gains
  YAML/JSON parameter sections, entity extraction could be sharpened to
  parse those fields explicitly.

## Confidence mapping

`score` is the grounded hybrid score after service penalties.

| score | confidence |
|---|---|
| `< MATCH_FLOOR` | `no match` |
| `[MATCH_FLOOR, CONF_MED)` | `low` |
| `[CONF_MED, CONF_HIGH)` | `medium` |
| `>= CONF_HIGH` | `high` |

`no match` never coexists with a citation. Current values: floor `0.12`,
medium `0.155`, high `0.20` (config.py).

**Spec-compliant string:** the confidence value for out-of-coverage queries is
`"no match"` exactly as written in the assignment (`"high" | "medium" | "low" |
"no match"`, with a space) — deliberately not coerced to `no_match`.

## Rubric alignment notes

- **RB-011 / RB-012:** the mock corpus IDs the incident postmortem as RB-012 and
  the customer-communication policy as RB-011, matching the assessment table's
  benchmark (Q4 → RB-012, Q5 → RB-011).
- **Evaluation runner:** `eval_harness.py` is the standalone, reproducible
  Python test runner that prints the 4-category score breakdown (right doc /
  wrong doc / right no-match / wrong no-match) — see `output/harness_output.txt`.

## Evaluation design

The harness (FR-6) classifies each case into four buckets — right/wrong citation,
right/wrong no-match — because "cited the right doc" alone can't distinguish "did
the right thing by staying silent" from "missed an answer". Score aggregates the
two pass buckets and the exit code fails the build on any miss. The suite pairs
the 5 official examples with adversarial cases the agent has never tuned against
(wrong-service near-dupes, out-of-corpus trivia), so the "no match" behavior is
actually exercised, not just assumed.

## Running

```bash
python3 scripts/make_sample_corpus.py   # generate the mock runbooks/ corpus
python3 eval_harness.py                 # evaluate 11 cases -> output/harness_output.txt
python3 main.py -q "<question>"         # single query
```