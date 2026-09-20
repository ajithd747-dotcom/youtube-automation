"""Category: comedy_stickman. Generates original joke/flirting premises via the
LLM router (not web research -- jokes aren't "searched", they're written).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_router import generate

JOKE_PROMPT = """Generate {n} short, original joke/punchline premises suitable for a 15-30 second
stickman comedy video (visual gag + spoken punchline). Keep them clean, universally relatable
(work, relationships, everyday annoyances), and punchy. One line each, numbered."""

FLIRT_PROMPT = """Generate {n} short, playful, tasteful flirting one-liners / pickup lines suitable
for a 15-30 second stickman video (one character delivering the line, reaction shot). Keep them
clever and lighthearted, not crude. One line each, numbered."""


def generate_joke_premises(n: int = 10) -> str:
    return generate(JOKE_PROMPT.format(n=n))


def generate_flirt_lines(n: int = 10) -> str:
    return generate(FLIRT_PROMPT.format(n=n))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "jokes"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    out = generate_flirt_lines(count) if mode == "flirt" else generate_joke_premises(count)
    print(out)
