// Agent — direct port of cloudtech_rag/agent.py. answerQuestion(question) -> Answer.

import { CONF_HIGH, CONF_MED, MATCH_FLOOR } from "./config.ts";
import { CorpusIndex } from "./retrieval.ts";
import type { Answer, Doc } from "./types.ts";
import { RUNBOOKS } from "./data/runbooks.ts";

export class Agent {
  private docs: Doc[];
  private index: CorpusIndex;

  constructor(docs: Doc[]) {
    this.docs = docs;
    this.index = new CorpusIndex(docs);
  }

  static fromBundled(): Agent {
    return new Agent(RUNBOOKS);
  }

  answerQuestion(question: string): Answer {
    if (typeof question !== "string" || question.trim().length === 0) {
      return {
        answer: "No question provided.",
        cited_doc_ids: [],
        confidence: "no match",
      };
    }

    const ranked = this.index.rank(question);
    const best = ranked[0];

    if (best.score < MATCH_FLOOR) {
      return {
        answer: "No runbook in the corpus answers this question. Nothing grounded enough was found.",
        cited_doc_ids: [],
        confidence: "no match",
      };
    }

    const confidence =
      best.score >= CONF_HIGH ? "high"
      : best.score >= CONF_MED ? "medium"
      : "low";

    const doc = this.docs.find((d) => d.id === best.id);
    const title = doc ? docTitle(doc.text) : best.id;
    const answer = best.best_paragraph
      ? `${title}: ${best.best_paragraph}`
      : `See runbook ${best.id}.`;

    return { answer, cited_doc_ids: [best.id], confidence };
  }

  diagnostics(question: string, top = 5) {
    return this.index.rank(question).slice(0, top);
  }
}

let globalAgent: Agent | null = null;

export function answerQuestion(question: string): Answer {
  if (globalAgent === null) globalAgent = Agent.fromBundled();
  return globalAgent.answerQuestion(question);
}

export function docTitle(text: string): string {
  for (const line of text.split("\n")) {
    const s = line.trim();
    if (s.startsWith("#")) return s.replace(/^#+\s*/, "");
  }
  return "";
}