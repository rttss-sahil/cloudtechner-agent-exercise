"""CloudTechner Agent Setup Exercise — hybrid RAG over runbooks.

External entry points:
    from cloudtech_rag import answer_question
    answer_question("checkout-api is running hot on CPU - where do I start?")

CLI:
    python3 -m cloudtech_rag -q "..."
"""

from .agent import Agent, answer_question

__all__ = ["Agent", "answer_question"]