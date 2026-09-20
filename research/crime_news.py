"""Category: crime_news. Worldwide crime/scam case studies with real outcomes
(investigation, culprit, sentence). Search queries deliberately rotate across
regions/countries so the topic pool isn't limited to one country's news cycle.

Images: only official police mugshots and Wikimedia Commons are safe to reuse
(copyright-cleared). This module includes a Wikimedia Commons lookup helper;
if no rights-cleared photo exists for a case, the video should fall back to
generic crime-themed stock imagery instead of a real (possibly copyrighted)
news photo.
"""
import sys
import urllib.parse
import urllib.request
import json

REGIONS = [
    "United States", "United Kingdom", "India", "Australia", "Canada",
    "Germany", "France", "Japan", "South Korea", "Brazil", "South Africa",
    "Philippines", "Nigeria", "UAE", "Singapore",
]

CASE_TYPES = [
    "fraud scam case sentenced", "cybercrime arrest convicted",
    "major heist case solved", "corporate embezzlement scandal sentenced",
    "serial scammer caught", "money laundering case verdict",
]


def suggest_search_queries(n: int = 6) -> list:
    """Real WebSearch queries spread across regions/case types for variety."""
    import random
    queries = []
    for _ in range(n):
        region = random.choice(REGIONS)
        case_type = random.choice(CASE_TYPES)
        queries.append(f"{region} {case_type} 2026 news")
    return queries


WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"


def find_wikimedia_image(person_name: str) -> str | None:
    """Search Wikimedia Commons for a rights-cleared image of a named person.
    Returns a direct image URL, or None if nothing found."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": person_name,
        "gsrnamespace": 6,  # File namespace only
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url",
    }
    url = f"{WIKIMEDIA_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "youtube-automation-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo")
            if imageinfo:
                return imageinfo[0]["url"]
    except Exception as e:
        print(f"Wikimedia lookup failed for '{person_name}': {e}")
    return None


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    for q in suggest_search_queries(n):
        print(q)
