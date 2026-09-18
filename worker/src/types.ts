export type Confidence = "high" | "medium" | "low" | "no match";

export interface Answer {
  answer: string;
  cited_doc_ids: string[];
  confidence: Confidence;
}

export interface Doc {
  id: string;
  name: string;
  text: string;
}

export interface RankedDoc {
  id: string;
  name: string;
  score: number;
  tfidf: number;
  token_jaccard: number;
  ngram_jaccard: number;
  service_match: boolean;
  reasons: string[];
  best_paragraph: string;
}