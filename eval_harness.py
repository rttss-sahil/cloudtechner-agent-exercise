"""Standalone evaluation runner — the 4-category score breakdown (Rubric #5).

Thin entry point over harness.py so the deliverable ships with an explicitly
named test runner. Prints the per-case classification (right doc / wrong doc /
right no-match / wrong no-match) and the aggregate score; exits non-zero only on
a full pass.

Usage:
    python3 eval_harness.py            # evaluate all cases in examples.json
    python3 eval_harness.py -q "..."   # append an ad-hoc question (no truth)
"""

from harness import main

if __name__ == "__main__":
    raise SystemExit(main())