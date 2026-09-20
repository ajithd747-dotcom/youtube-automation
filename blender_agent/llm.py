"""Thin wrapper over the project's multi-provider router (llm_router.py) with JSON/code extraction."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def ask(prompt: str, system: str = None) -> str:
    from llm_router import generate  # imported lazily so offline/heuristic runs never need API keys
    return generate(prompt, system=system)


def extract_json(raw: str):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, flags=re.S)  # first { ... last }
        if not m:
            raise
        return json.loads(m.group(0))


def ask_json(prompt: str, system: str = None, retries: int = 2):
    last = None
    for _ in range(retries):
        try:
            return extract_json(ask(prompt, system))
        except (json.JSONDecodeError, ValueError) as e:
            last = e
            prompt += "\n\nYour previous reply was not valid JSON. Reply with ONLY one JSON object, no prose."
    raise ValueError(f"LLM did not return valid JSON: {last}")


def extract_code(raw: str) -> str:
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", raw, flags=re.S)
    return (m.group(1) if m else raw).strip()
