"""Agent entry point: answer_question(question) -> dict.

Contract (from FRD): returns
    {"answer": str, "cited_doc_ids": list[str], "confidence": "high"|"medium"|"low"|"no match"}
"no match" is a legitimate answer when nothing in the corpus actually applies.
"""
from __future__ import annotations


from .config import CONF_HIGH, CONF_MED, MATCH_FLOOR
from .loader import read_runbooks
from .retrieval import CorpusIndex, tokenize

DEFAULT_DIR = None  # resolved lazily to the runbooks/ folder next to this package


class Agent:
    def __init__(self, runbooks_dir=DEFAULT_DIR):
        import cloudtech_rag.config as cfg
        from .config import BASE_DIR
        self.dir = runbooks_dir or (cfg.DEFAULT_RUNBOOKS_DIR if hasattr(cfg, "DEFAULT_RUNBOOKS_DIR") else BASE_DIR / "runbooks")
        self.docs = read_runbooks(self.dir)
        self.index = CorpusIndex(self.docs)

    def answer_question(self, question: str) -> dict:
        if not isinstance(question, str) or not question.strip():
            return {
                "answer": "No question provided.",
                "cited_doc_ids": [],
                "confidence": "no match",
            }

        ranked = self.index.rank(question)
        best = ranked[0]

        if best["score"] < MATCH_FLOOR:
            return {
                "answer": ("No runbook in the corpus answers this question. "
                           "Nothing grounded enough was found."),
                "cited_doc_ids": [],
                "confidence": "no match",
            }

        if best["score"] >= CONF_HIGH:
            confidence = "high"
        elif best["score"] >= CONF_MED:
            confidence = "medium"
        else:
            confidence = "low"

        doc = next((d for d in self.docs if d["id"] == best["id"]), None)
        title = _doc_title(doc["text"]) if doc else best["id"]
        answer = (f"{title}: {best['best_paragraph']}"
                  if best["best_paragraph"] else f"See runbook {best['id']}.")

        return {
            "answer": answer,
            "cited_doc_ids": [best["id"]],
            "confidence": confidence,
        }


def _doc_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


globa_agent: Agent | None = None


def answer_question(question: str) -> dict:
    """Top-level entry point (FR-1). Lazily builds the index on first call."""
    global globa_agent
    if globa_agent is None:
        globa_agent = Agent()
    return globa_agent.answer_question(question)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "checkout-api is running hot on CPU - what should I check first?"
    print(answer_question(q))