"""Root entry point — mirrors the FR-1 contract and a tiny CLI.

Usage:
    python3 main.py -q "checkout-api is running hot on CPU"
    python3 main.py                              # prints usage
"""

from cloudtech_rag import Agent, answer_question

__all__ = ["Agent", "answer_question"]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Runbooks Q&A agent (CloudTechner exercise)")
    ap.add_argument("--question", "-q", default=None)
    ap.add_argument("--runbooks-dir", "-d", default=None)
    args = ap.parse_args()
    if not args.question:
        print("Usage:\n  python3 main.py -q \"<question>\"\n  python3 harness.py")
        return
    agent = Agent(args.runbooks_dir) if args.runbooks_dir else Agent()
    print(agent.answer_question(args.question))


if __name__ == "__main__":
    main()