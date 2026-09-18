"""python3 -m cloudtech_rag -q "..." — CLI entry."""

from .agent import Agent


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Runbooks Q&A agent")
    ap.add_argument("--question", "-q", default=None, help="Ask a question")
    ap.add_argument("--runbooks-dir", "-d", default=None, help="Override runbooks directory")
    args = ap.parse_args()
    if not args.question:
        print("Contact: answer_question(question) -> dict\n"
              "   python3 -m cloudtech_rag -q \"<question>\"")
        return
    agent = Agent(args.runbooks_dir) if args.runbooks_dir else Agent()
    print(agent.answer_question(args.question))


if __name__ == "__main__":
    main()