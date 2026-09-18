// Thresholds mirror cloudtech_rag/config.py (Python implementation).
// Tune here after swapping in the real runbooks corpus, then re-run `npm run parity`.

export const MATCH_FLOOR = 0.12; // below this -> "no match"
export const CONF_HIGH = 0.2;    // >= this  -> "high"
export const CONF_MED = 0.155;   // >= this  -> "medium", else "low" (if above floor)

export const SERVICE_PENALTY = 0.35;         // doc never mentions the asked service
export const SERVICE_MINUS_PENALTY = 0.85;   // doc about extra services but still covers

export const WEIGHTS = { tfidf: 0.45, token_jaccard: 0.25, ngram_jaccard: 0.3 };

export const SERVICE_TOKEN_RE = /[a-z][a-z0-9]*-api\b/g;

// Explicit aliases -> canonical service token (extend when the real corpus lands)
export const SERVICE_ALIASES: Record<string, string> = {
  "billing-api": "payments-api",
  "billing": "payments-api",
  "orders-api": "checkout-api",
  "stock-api": "inventory-api",
};

export const EXTRA_SERVICES: string[] = []; // e.g. ["auth-service"] if the real corpus has them

export const ANSWER_MAX_PARAGRAPHS = 2;
export const ANSWER_SNIPPET_LENGTH = 400;