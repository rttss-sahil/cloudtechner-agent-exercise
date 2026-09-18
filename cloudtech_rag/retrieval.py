"""Hybrid retrieval: TF-IDF cosine + token Jaccard + character 3-gram Jaccard.

Design rationale (see WRITEUP.md for full detail):
- The corpus is small (12 docs) and intentionally contains near-duplicates that
  differ by *service* and *failure mode*. Pure embeddings over-smooth those
  differences and tend to match the closest-sounding (wrong) doc.
- A hybrid lexical score is precise: it rewards literal keyword overlap while a
  character-trigram Jaccard stays robust to small wording differences.
- An explicit *service-grounding gate* enforces "you asked about checkout-api, the
  answer must actually be about checkout-api" — the core defense against the
  wrong-service near-duplicate traps. It needs no fixed list of services: it just
  compares hyphenated service-like tokens in the question vs. each doc.
Everything here is pure stdlib — no ML/vector DB install friction.
"""
from __future__ import annotations


import math
import re
from collections import Counter

from .config import (ANSWER_MAX_PARAGRAPHS, EXTRA_SERVICES, SERVICE_ALIASES,
                     SERVICE_MINUS_PENALTY, SERVICE_PENALTY, SERVICE_TOKEN_RE, WEIGHTS)

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "have", "has", "had", "to", "of", "in", "on", "for",
    "and", "or", "but", "not", "no", "we", "our", "i", "you", "it", "that",
    "this", "what", "how", "why", "when", "which", "who", "whom", "with",
    "at", "by", "from", "as", "about", "if", "then", "than", "so", "vs", "should",
    "can", "could", "would", "will", "their", "they", "them", "there", "here",
}
TOKEN_RE = re.compile(r"[a-z0-9]+")
NG3 = "abcdefghijklmnopqrstuvwxyz0123456789"


def tokenize(text: str) -> list[str]:
    words = TOKEN_RE.findall(text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def ngrams3(text: str) -> set[str]:
    chunks = [c for c in (TOKEN_RE.findall(text.lower()))]
    joined = "".join(chunks)
    if len(joined) < 3:
        return {joined} if joined else set()
    return {joined[i:i + 3] for i in range(len(joined) - 2)}


def service_tokens(text: str) -> set[str]:
    found: set[str] = set()
    for tok in re.findall(SERVICE_TOKEN_RE, text.lower()):
        found.add(SERVICE_ALIASES.get(tok, tok))
    found |= {t.lower() for t in EXTRA_SERVICES if t.lower() in text.lower()}
    return found


class CorpusIndex:
    def __init__(self, docs):
        self.docs = docs
        self._token_counts: list[Counter] = []
        self._doc_tokens: list[set[str]] = []
        self._doc_ngrams: list[set[str]] = []
        self._doc_svc: list[set[str]] = []
        self._idf: dict[str, float] = {}
        self._build()

    def _build(self) -> None:
        for doc in self.docs:
            doc["_tokens"] = tokenize(doc["text"])
            self._token_counts.append(Counter(doc["_tokens"]))
            self._doc_tokens.append(set(doc["_tokens"]))
            self._doc_ngrams.append(ngrams3(doc["text"]))
            self._doc_svc.append(service_tokens(doc["text"]))
        n = len(self.docs)
        df: Counter = Counter()
        for c in self._token_counts:
            df.update(c.keys())
        for term, count in df.items():
            self._idf[term] = math.log((1 + n) / (1 + count)) + 1.0

    def _tfidf_vec(self, tokens: list[str]) -> Counter:
        c = Counter(tokens)
        vec: Counter = Counter()
        for term, count in c.items():
            vec[term] = (1.0 + math.log(count)) * self._idf.get(term, 1.0)
        return vec

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        if not a or not b:
            return 0.0
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        dot = 0.0
        small, big = (a, b) if len(a) <= len(b) else (b, a)
        for term, v in small.items():
            dot += v * big.get(term, 0.0)
        return dot / (na * nb)

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 0.0
        return len(a & b) / len(a | b)

    def rank(self, question: str) -> list[dict]:
        """Return docs sorted by grounded hybrid score, each annotated with diagnostics."""
        q_tokens = tokenize(question)
        q_svc = service_tokens(question)
        q_vec = self._tfidf_vec(q_tokens)
        q_ngrams = ngrams3(question)

        scored = []
        for i, doc in enumerate(self.docs):
            doc_vec = self._tfidf_vec(doc["_tokens"])
            tfidf = self._cosine(q_vec, doc_vec)
            jac_tok = self._jaccard(set(q_tokens), self._doc_tokens[i])
            jac_ng = self._jaccard(q_ngrams, self._doc_ngrams[i])
            hybrid = (WEIGHTS["tfidf"] * tfidf
                      + WEIGHTS["token_jaccard"] * jac_tok
                      + WEIGHTS["ngram_jaccard"] * jac_ng)

            doc_svc = self._doc_svc[i]
            matched_svc = q_svc & doc_svc if q_svc else True
            reasons = []
            if q_svc and not matched_svc:
                hybrid *= SERVICE_PENALTY
                reasons.append(f"doc never mentions service(s) {sorted(q_svc)[:2]}...")
            else:
                missing = q_svc - doc_svc
                extra = doc_svc - q_svc
                if q_svc and missing and extra:
                    hybrid *= SERVICE_MINUS_PENALTY

            scored.append({
                "id": doc["id"],
                "name": doc["name"],
                "score": round(hybrid, 4),
                "tfidf": round(tfidf, 4),
                "token_jaccard": round(jac_tok, 4),
                "ngram_jaccard": round(jac_ng, 4),
                "service_match": bool(matched_svc) or not q_svc,
                "reasons": reasons,
                "best_paragraph": self._best_paragraph(doc["text"], q_tokens),
            })

        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored

    def _best_paragraph(self, text: str, q_tokens: list[str]) -> str:
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        if not paragraphs:
            return text.strip()
        qset = set(q_tokens)
        def score(p: str) -> float:
            ptoks = tokenize(p)
            return self._jaccard(qset, set(ptoks)) + 0.5 * len(set(ptoks) & qset) / max(1, len(qset))
        top = sorted(paragraphs, key=score, reverse=True)[:ANSWER_MAX_PARAGRAPHS]
        return " ".join(top)[:400]