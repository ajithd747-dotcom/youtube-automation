"""Category: explainer. Finds a real trending/most-searched question and
gathers source material for it via WebSearch results the agent already has
access to -- this script prepares the SEARCH PLAN; the agent runs the actual
WebSearch calls and saves the result (see research/README.md workflow).
"""
import random
import sys
from pathlib import Path

TOPIC_BUCKETS = {
    "health": ["what is bone marrow", "why do we dream", "what causes migraines", "is intermittent fasting healthy"],
    "tech": ["how to fix a null pointer exception", "why is my wifi slow", "how to fix 'undefined is not a function'", "what is a memory leak"],
    "science": ["why is the sky blue", "how do vaccines work", "what happens in a black hole", "why do cats purr"],
    "howto": ["how to negotiate a raise", "how to remove a stripped screw", "how to get a passport fast", "how to fix a running toilet"],
    "finance": ["what is a credit score", "how does compound interest work", "what is an index fund", "why is inflation bad"],
}


def suggest_search_queries(n: int = 5) -> list:
    """Returns n real search queries to run via WebSearch to find current
    trending versions of these evergreen high-search-volume question types."""
    buckets = random.sample(list(TOPIC_BUCKETS.keys()), min(n, len(TOPIC_BUCKETS)))
    queries = []
    for bucket in buckets:
        queries.append(f"most googled {bucket} questions 2026 trending")
    return queries


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for q in suggest_search_queries(n):
        print(q)
