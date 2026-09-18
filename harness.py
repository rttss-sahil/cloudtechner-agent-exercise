"""Evaluation harness (FR-6/FR-7).

Classifies each (question, expected) case into one of four outcome buckets:
    PASS_RIGHT       cited the right doc(s)
    FAIL_WRONG       cited the wrong doc(s)
    PASS_NO_MATCH    correctly returned no match (expected None)
    FAIL_NO_MATCH    incorrectly returned no match when a doc did apply
Reports an aggregate score. Loads cases from examples.json plus any CLI args.
"""
from __future__ import annotations


import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from cloudtech_rag import Agent

BASE = Path(__file__).resolve().parent
CASES_FILE = BASE / "examples.json"
OUTPUT_DIR = BASE / "output"


@dataclass
class CaseResult:
    question: str
    expected: list[str] | None
    actual_ids: list[str]
    confidence: str
    outcome: str
    notes: str = ""


OUTCOME_LABELS = {
    "correct": "PASS: cited right doc(s)",
    "wrong": "FAIL: cited wrong doc(s)",
    "correct_no_match": "PASS: correctly no-match",
    "incorrect_no_match": "FAIL: wrong no-match (doc applied)",
}


def classify(expected, actual_ids) -> str:
    if expected is None:
        return "correct_no_match" if not actual_ids else "wrong"
    if actual_ids and any(d in expected for d in actual_ids):
        return "correct"
    return "incorrect_no_match" if not actual_ids else "wrong"


def run_cases(agent: Agent, cases: list[dict]) -> list[CaseResult]:
    results = []
    for c in cases:
        resp = agent.answer_question(c["question"])
        results.append(CaseResult(
            question=c["question"],
            expected=c.get("expected"),
            actual_ids=resp["cited_doc_ids"],
            confidence=resp["confidence"],
            outcome=classify(c.get("expected"), resp["cited_doc_ids"]),
        ))
    return results


def render(results: list[CaseResult]) -> str:
    lines = []
    lines.append("=" * 74)
    lines.append("CLOUDTECHNER AGENT SETUP EXERCISE — HARNESS REPORT")
    lines.append("=" * 74)
    lines.append(f"{'#':>3}  {'question':<58}  {'outcome':<30}")
    lines.append("-" * 74)
    for i, r in enumerate(results, 1):
        q = r.question if len(r.question) <= 58 else r.question[:55] + "..."
        lines.append(f"{i:>3}  {q:<58}  {OUTCOME_LABELS[r.outcome]:<30}")
        flags = []
        if r.expected is not None:
            exp = ",".join(r.expected)
            flags.append(f"expected={exp}")
        flags.append(f"cited={','.join(r.actual_ids) or '-'}")
        flags.append(f"conf={r.confidence}")
        lines.append(f"      ({', '.join(flags)})")
        if r.notes:
            lines.append(f"       ! {r.notes}")
    counts = Counter(r.outcome for r in results)
    passed = counts["correct"] + counts["correct_no_match"]
    total = len(results)
    lines.append("-" * 74)
    lines.append("Bucket counts:")
    for bucket, label in OUTCOME_LABELS.items():
        lines.append(f"  {label:<30} {counts[bucket]:>3}")
    lines.append("")
    lines.append(f"SCORE: {passed}/{total} cases passed ({100.0 * passed / max(1, total):.1f}%)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run the eval harness")
    ap.add_argument("--cases", default=str(CASES_FILE), help="cases JSON file")
    ap.add_argument("--runbooks-dir", "-d", default=None)
    ap.add_argument("--ad-hoc", nargs="*", default=[], help="raw questions (no expected truth)")
    ap.add_argument("--out", default=str(OUTPUT_DIR / "harness_output.txt"))
    args = ap.parse_args(argv)

    cases = []
    with open(args.cases, encoding="utf-8") as f:
        cases = json.load(f)
    cases += [{"question": q} for q in args.ad_hoc]

    agent = Agent(args.runbooks_dir) if args.runbooks_dir else Agent()
    results = run_cases(agent, cases)
    report = render(results)
    print(report)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[written to {out}]")

    passed = sum(1 for r in results if r.outcome in ("correct", "correct_no_match"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())