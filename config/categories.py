"""Content category registry. Each category maps to a research method and a
video visual style. This is the single source of truth for what kinds of
videos the pipeline produces -- add new categories here as they're built out.
"""

CATEGORIES = {
    "explainer": {
        "label": "Trending Q&A explainers",
        "description": "Most-searched real-world questions across topics (health, tech/coding errors, science, how-to) turned into short explainer videos.",
        "visual_style": "stock",
        "research_module": "research.trending_topics",
        "status": "active",
    },
    "comedy_stickman": {
        "label": "Stickman jokes & flirting one-liners",
        "description": "Short comedic stickman videos: jokes/punchlines and flirting/pickup-line content.",
        "visual_style": "stickman",
        "research_module": "research.joke_topics",
        "status": "active",
    },
    "crime_news": {
        "label": "Crime & scam case studies",
        "description": "Real crime/scam news stories with case background, police findings, culprit, and sentence. Images limited to official mugshots and Wikimedia Commons only (copyright-safe) -- generic imagery used when no rights-cleared photo exists.",
        "visual_style": "stock",
        "research_module": "research.crime_news",
        "status": "active",
    },
    "world_news": {
        "label": "Funny & romantic world news",
        "description": "Lighthearted, funny, or heartwarming/romantic real news stories from around the world.",
        "visual_style": "stock",
        "research_module": "research.world_news",
        "status": "active",
    },
}


def list_categories():
    for key, cat in CATEGORIES.items():
        print(f"{key:18} [{cat['status']:6}] {cat['label']} -> style={cat['visual_style']}")


if __name__ == "__main__":
    list_categories()
