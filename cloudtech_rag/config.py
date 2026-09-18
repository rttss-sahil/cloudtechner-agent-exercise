"""Central configuration for the RAG agent.

Thresholds are calibrated against the SAMPLE corpus (scripts/make_sample_corpus.py)
so the pipeline provably works before the real runbooks/ land. Re-tune with the
real corpus: run harness.py, look at the per-case report, then adjust the cutoffs.
"""
from __future__ import annotations


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUNBOOKS_DIR = BASE_DIR / "runbooks"

MATCH_FLOOR = 0.12        # below this -> "no match" (nothing grounded enough)
CONF_HIGH = 0.20          # >= this  -> "high"
CONF_MED = 0.155          # >= this  -> "medium", else "low" (if above floor)

SERVICE_PENALTY = 0.35    # multiplier when a doc never mentions the service asked about
SERVICE_MINUS_PENALTY = 0.85  # mild penalty when doc is about extra services but still covers

WEIGHTS = {"tfidf": 0.45, "token_jaccard": 0.25, "ngram_jaccard": 0.30}

# Service-like tokens are only `*-api` names (the real corpus's services) plus
# any explicit extras below. This deliberately avoids false positives from other
# hyphenated words (severity-1, blue-green, status-page).
SERVICE_TOKEN_RE = r"[a-z][a-z0-9]*-api\b"
EXTRA_SERVICES: set[str] = set()  # e.g. {"auth-service"} if the real corpus has them

# Explicit aliases -> canonical service token (extend when the real corpus lands)
SERVICE_ALIASES = {
    "billing-api": "payments-api",
    "billing": "payments-api",
    "orders-api": "checkout-api",
    "stock-api": "inventory-api",
}

ANSWER_MAX_PARAGRAPHS = 2

DEFAULT_RUNBOOKS_DIR = RUNBOOKS_DIR