"""Category: world_news. Funny and romantic/heartwarming real news stories
from around the world -- search queries rotate across regions so the topic
pool draws from global news, not one country's cycle.
"""
import random
import sys

REGIONS = [
    "United States", "United Kingdom", "India", "Australia", "Japan",
    "Brazil", "Italy", "Spain", "South Korea", "Mexico", "Kenya",
    "Philippines", "Canada", "France", "Thailand",
]

ANGLES = [
    "funny viral news story", "heartwarming romantic news story",
    "unbelievable but true news story", "feel-good news story",
    "quirky local news story",
]


def suggest_search_queries(n: int = 6) -> list:
    queries = []
    for _ in range(n):
        region = random.choice(REGIONS)
        angle = random.choice(ANGLES)
        queries.append(f"{region} {angle} this week")
    return queries


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    for q in suggest_search_queries(n):
        print(q)
