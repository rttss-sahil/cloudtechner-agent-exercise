// Hybrid retrieval — direct port of cloudtech_rag/retrieval.py (Python).
// Same math: TF-IDF cosine + token Jaccard + char 3-gram Jaccard, then a
// service-grounding gate. Kept deterministic so Worker results == local Python
// results for the same corpus and thresholds.

import {
  ANSWER_MAX_PARAGRAPHS,
  ANSWER_SNIPPET_LENGTH,
  EXTRA_SERVICES,
  SERVICE_ALIASES,
  SERVICE_MINUS_PENALTY,
  SERVICE_PENALTY,
  SERVICE_TOKEN_RE,
  WEIGHTS,
} from "./config.ts";
import type { Doc, RankedDoc } from "./types.ts";

const STOPWORDS = new Set([
  "the","a","an","is","are","was","were","be","been","being","am",
  "do","does","did","have","has","had","to","of","in","on","for",
  "and","or","but","not","no","we","our","i","you","it","that",
  "this","what","how","why","when","which","who","whom","with",
  "at","by","from","as","about","if","then","than","so","vs","should",
  "can","could","would","will","their","they","them","there","here",
]);

const ALNUM_RE = /[a-z0-9]+/g;

export function tokenize(text: string): string[] {
  const out: string[] = [];
  const lower = text.toLowerCase();
  for (const m of lower.matchAll(ALNUM_RE)) {
    const w = m[0];
    if (!STOPWORDS.has(w) && w.length > 1) out.push(w);
  }
  return out;
}

export function ngrams3(text: string): Set<string> {
  const joined = text.toLowerCase().match(ALNUM_RE)?.join("") ?? "";
  if (joined.length < 3) return joined ? new Set([joined]) : new Set();
  const out = new Set<string>();
  for (let i = 0; i + 2 < joined.length; i++) out.add(joined.slice(i, i + 3));
  return out;
}

export function serviceTokens(text: string): Set<string> {
  const out = new Set<string>();
  const lower = text.toLowerCase();
  for (const m of lower.matchAll(new RegExp(SERVICE_TOKEN_RE.source, "g"))) {
    out.add(SERVICE_ALIASES[m[0]] ?? m[0]);
  }
  for (const extra of EXTRA_SERVICES) {
    if (lower.includes(extra.toLowerCase())) out.add(extra.toLowerCase());
  }
  return out;
}

interface DocVector {
  tokens: string[];
  tokenSet: Set<string>;
  ngrams: Set<string>;
  services: Set<string>;
  tfidf: Map<string, number>;
}

export class CorpusIndex {
  private docs: Doc[];
  private vectors: DocVector[];
  private idf: Map<string, number>;

  constructor(docs: Doc[]) {
    this.docs = docs;
    this.vectors = [];
    this.idf = new Map();
    this.build();
  }

  private build(): void {
    const df = new Map<string, number>();
    for (const doc of this.docs) {
      const tokens = tokenize(doc.text);
      const vec: DocVector = {
        tokens,
        tokenSet: new Set(tokens),
        ngrams: ngrams3(doc.text),
        services: serviceTokens(doc.text),
        tfidf: new Map(),
      };
      this.vectors.push(vec);
      for (const term of new Set(tokens)) df.set(term, (df.get(term) ?? 0) + 1);
    }
    const n = this.docs.length;
    for (const [term, count] of df) {
      this.idf.set(term, Math.log((1 + n) / (1 + count)) + 1);
    }
    for (let i = 0; i < n; i++) {
      this.vectors[i].tfidf = this.tfidfVec(this.vectors[i].tokens);
    }
  }

  private tfidfVec(tokens: string[]): Map<string, number> {
    const counts = new Map<string, number>();
    for (const t of tokens) counts.set(t, (counts.get(t) ?? 0) + 1);
    const vec = new Map<string, number>();
    for (const [term, c] of counts) {
      vec.set(term, (1 + Math.log(c)) * (this.idf.get(term) ?? 1));
    }
    return vec;
  }

  private static cosine(a: Map<string, number>, b: Map<string, number>): number {
    if (a.size === 0 || b.size === 0) return 0;
    let na = 0;
    for (const v of a.values()) na += v * v;
    let nb = 0;
    for (const v of b.values()) nb += v * v;
    if (na === 0 || nb === 0) return 0;
    const [small, big] = a.size <= b.size ? [a, b] : [b, a];
    let dot = 0;
    for (const [term, v] of small) dot += v * (big.get(term) ?? 0);
    return dot / (Math.sqrt(na) * Math.sqrt(nb));
  }

  private static jaccard(a: Set<string>, b: Set<string>): number {
    if (a.size === 0 && b.size === 0) return 0;
    let inter = 0;
    for (const x of a) if (b.has(x)) inter++;
    const union = a.size + b.size - inter;
    return union === 0 ? 0 : inter / union;
  }

  rank(question: string): RankedDoc[] {
    const qTokens = tokenize(question);
    const qServices = serviceTokens(question);
    const qVec = this.tfidfVec(qTokens);
    const qNgrams = ngrams3(question);

    const scored: RankedDoc[] = [];
    for (let i = 0; i < this.docs.length; i++) {
      const doc = this.docs[i];
      const v = this.vectors[i];

      const tfidf = CorpusIndex.cosine(qVec, v.tfidf);
      const jacTok = CorpusIndex.jaccard(new Set(qTokens), v.tokenSet);
      const jacNg = CorpusIndex.jaccard(qNgrams, v.ngrams);
      let hybrid =
        WEIGHTS.tfidf * tfidf +
        WEIGHTS.token_jaccard * jacTok +
        WEIGHTS.ngram_jaccard * jacNg;

      const docSvc = v.services;
      let serviceMatch = true;
      const reasons: string[] = [];
      if (qServices.size > 0) {
        let matched = false;
        for (const s of qServices) if (docSvc.has(s)) matched = true;
        if (!matched) {
          hybrid *= SERVICE_PENALTY;
          serviceMatch = false;
          reasons.push(`doc never mentions service(s) ${[...qServices].slice(0, 2).join(",")}...`);
        } else {
          const missing = [...qServices].filter((s) => !docSvc.has(s));
          const extra = [...docSvc].filter((s) => !qServices.has(s));
          if (missing.length > 0 && extra.length > 0) hybrid *= SERVICE_MINUS_PENALTY;
        }
      }

      scored.push({
        id: doc.id,
        name: doc.name,
        score: Math.round(hybrid * 10000) / 10000,
        tfidf: Math.round(tfidf * 10000) / 10000,
        token_jaccard: Math.round(jacTok * 10000) / 10000,
        ngram_jaccard: Math.round(jacNg * 10000) / 10000,
        service_match: serviceMatch,
        reasons,
        best_paragraph: this.bestParagraph(doc.text, new Set(qTokens)),
      });
    }

    scored.sort((a, b) => b.score - a.score);
    return scored;
  }

  private bestParagraph(text: string, qSet: Set<string>): string {
    const paragraphs = text
      .split("\n")
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
    if (paragraphs.length === 0) return text.trim();
    const scored = paragraphs.map((p) => {
      const ptoks = new Set(tokenize(p));
      const inter = [...ptoks].filter((t) => qSet.has(t)).length;
      return { p, s: CorpusIndex.jaccard(qSet, ptoks) + (0.5 * inter) / Math.max(1, qSet.size) };
    });
    scored.sort((a, b) => b.s - a.s);
    return scored.slice(0, ANSWER_MAX_PARAGRAPHS).map((x) => x.p).join(" ").slice(0, ANSWER_SNIPPET_LENGTH);
  }
}