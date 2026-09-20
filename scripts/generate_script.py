"""Turn research notes into a YouTube video script.

Backends:
  router  - rotates across free-tier cloud LLM providers, falls back to paid
            Kimi only as a last resort. Runs a generate -> critique -> revise
            pipeline for quality, using a category-specific prompt. [default]
            outputs strict JSON, saved as <name>_script.json
  ollama  - local llama3.2:1b (fast, free, always available, lower quality,
            single-pass, no critique loop) outputs markdown
  manual  - pauses and asks you to run the prompt through Claude Code yourself,
            then paste the reply back in (best quality, human-in-the-loop)
            outputs freeform markdown, saved as <name>_script.md

Categories (see config/categories.py): explainer, comedy_stickman, crime_news,
world_news. Each has its own prompt/structure -- pass one with --category or
it defaults to "explainer".
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ollama_client import generate as ollama_generate
from manual_llm import ask as manual_ask
from llm_router import generate as router_generate
from scripts.prompts import PROMPTS, CRITIQUE_PROMPT, REVISE_PROMPT

MARKDOWN_PROMPT = """You are a YouTube scriptwriter. Using the research notes below, write a complete video script.

Research notes:
---
{notes}
---

Output format:
1. Title (one catchy line)
2. Hook (first 10 seconds, must grab attention)
3. Full script broken into short spoken segments
4. Call to action / outro
"""


def extract_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    return json.loads(raw)


def write_script_router(research_notes: str, category: str = "explainer") -> tuple:
    """Generate -> critique -> revise pipeline. Returns (json_str, format)."""
    prompt_template = PROMPTS.get(category, PROMPTS["explainer"])
    draft_prompt = prompt_template.format(notes=research_notes)

    print(f"[script] generating draft ({category})...")
    draft_raw = router_generate(draft_prompt)

    print("[script] critiquing draft...")
    critique = router_generate(CRITIQUE_PROMPT.format(category=category, notes=research_notes, draft=draft_raw))

    print("[script] revising based on critique...")
    revised_raw = router_generate(REVISE_PROMPT.format(notes=research_notes, draft=draft_raw, critique=critique))

    try:
        data = extract_json(revised_raw)
        return json.dumps(data, indent=2), "json"
    except (json.JSONDecodeError, ValueError):
        print("[script] revision wasn't valid JSON, falling back to draft...")
        try:
            data = extract_json(draft_raw)
            return json.dumps(data, indent=2), "json"
        except (json.JSONDecodeError, ValueError):
            print("[script] draft wasn't valid JSON either, saving raw text.")
            return revised_raw, "markdown"


def write_script(research_notes: str, backend: str = "router", category: str = "explainer"):
    """Returns (content_str, format) where format is 'json' or 'markdown'."""
    if backend == "manual":
        return manual_ask(MARKDOWN_PROMPT.format(notes=research_notes)), "markdown"
    if backend == "ollama":
        return ollama_generate(MARKDOWN_PROMPT.format(notes=research_notes)), "markdown"
    return write_script_router(research_notes, category)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_script.py <path-to-research-notes.md> [router|ollama|manual] [category]")
        raise SystemExit(1)

    notes_path = Path(sys.argv[1])
    backend_arg = sys.argv[2] if len(sys.argv) > 2 else "router"
    category_arg = sys.argv[3] if len(sys.argv) > 3 else "explainer"
    notes = notes_path.read_text(encoding="utf-8")
    content, fmt = write_script(notes, backend_arg, category_arg)

    ext = "json" if fmt == "json" else "md"
    out_path = Path(__file__).parent / f"{notes_path.stem}_script.{ext}"
    out_path.write_text(content, encoding="utf-8")
    print(f"Script written to {out_path}")
