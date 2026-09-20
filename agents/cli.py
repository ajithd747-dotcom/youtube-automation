"""Agent registry CLI.

    python agents/cli.py list                 every agent: kind, skills, tools
    python agents/cli.py count                total number of AI agents in the project (+ breakdown)
    python agents/cli.py show <name>
    python agents/cli.py verify [name]        spec + skill validation (+ the agent's own tests)
    python agents/cli.py create-agent|create-tool|create-skill ...   (see factory.py)
    python agents/cli.py sync                 (re)register the built-in agents of this project
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import ROOT, SK, Agent, load_agent, load_registry, register  # noqa: E402
import factory  # noqa: E402

# Agents that exist as code elsewhere in the repo (their skills live where their code lives).
BUILTIN = [
    dict(name="research", title="Research agent", kind="external", role="Gathers topic data with a browser (Playwright MCP) and web search, saves notes to research/<topic>.md",
         path="research", skills_dir=None, llm=True, note="run by Claude Code, no python entry"),
    dict(name="script-writer", title="Script writer agent", kind="llm", role="Turns research notes into a category-specific video script (draft -> critique -> revise) via the multi-provider LLM router",
         path="scripts", entry=None, skills_dir=None, llm=True),
    dict(name="blender-director", title="Blender director agent", kind="llm", role="Reads each script segment and plans the shot (2D DSL or cinematic recipe + mood + title), grounded by the skill library",
         path="blender_agent", entry=None, skills_dir="blender_agent/skills", llm=True),
    dict(name="blender-coder", title="Blender coder agent", kind="llm", role="Writes extra bpy code for effects the shot DSL cannot express, using docs+skills RAG, static safety check and a headless self-repair loop",
         path="blender_agent", entry=None, skills_dir="blender_agent/skills", llm=True),
    dict(name="blender-render", title="Blender render agent", kind="algorithmic", role="Builds and renders shots headless (physics pre-step, quality ladder, draft fallback, per-shot cache) and muxes audio/captions",
         path="blender_agent", entry=None, skills_dir="blender_agent/skills", llm=False),
    dict(name="benchmark", title="Recreation & benchmark agent", kind="algorithmic", role="Recreates a reference video from its analysis (shot spec, Blender presets, music/voice agents, GUI screen recording) and scores it against the original (SSIM, colour, cuts, motion, WER, pitch, loudness), then guides fixes round by round",
         path="blender_agent/benchmark", entry=None, skills_dir="blender_agent/skills", llm=False),
    dict(name="skill-learner", title="Skill learning agent", kind="hybrid", role="Extracts evidence from videos/books (transcribe, cuts, frames, metrics), distils candidate skills, verifies them headless and promotes them; retrospective after every run",
         path="blender_agent", entry=None, skills_dir="blender_agent/skills", llm=True),
]


def sync():
    for e in BUILTIN:
        register(e)
    print("registered", len(BUILTIN), "built-in agents")


def agent_row(e):
    n_skills = "-"
    if e.get("skills_dir"):
        d = ROOT / e["skills_dir"]
        n_skills = str(len([f for f in d.rglob("*.md") if f.name.lower() != "readme.md" and "candidates" not in f.parts and "sources" not in f.parts])) if d.exists() else "0"
    return f"{e['name']:18s} {e['kind']:11s} llm={'y' if e.get('llm') else 'n'}  skills={n_skills:>3s}  {e['role'][:88]}"


def main(a):
    if not a:
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "sync":
        sync()
    elif cmd == "list":
        for e in load_registry():
            print(agent_row(e))
    elif cmd == "count":
        reg = load_registry()
        kinds = Counter(e["kind"] for e in reg)
        print(f"TOTAL AI AGENTS IN THE PROJECT: {len(reg)}")
        print("  by kind:", dict(kinds))
        print("  LLM-driven or hybrid:", sum(1 for e in reg if e.get("llm")))
        print("  with their own skill library:", sum(1 for e in reg if e.get("skills_dir")))
        for e in reg:
            print("  -", e["name"], f"({e['kind']})")
    elif cmd == "show":
        e = next(x for x in load_registry() if x["name"] == a[1])
        print(json.dumps(e, indent=2))
        p = ROOT / e["path"] / "agent.json"
        if p.exists():
            print(p.read_text(encoding="utf-8"))
    elif cmd == "verify":
        names = a[1:] or [e["name"] for e in load_registry() if e.get("entry")]
        bad = 0
        for n in names:
            ag = load_agent(n)
            rep = ag.self_check()
            bad += not rep["ok"]
            print(("ok   " if rep["ok"] else "FAIL ") + n, f"skills={rep['skills']}", "; ".join(rep["problems"]))
            for t in sorted((ag.root / "tests").glob("test_*.py")):
                r = subprocess.run([sys.executable, str(t)], capture_output=True, text=True)
                bad += r.returncode != 0
                print(("  test ok   " if r.returncode == 0 else "  test FAIL ") + t.name, (r.stderr or r.stdout)[-300:] if r.returncode else "")
        sys.exit(1 if bad else 0)
    elif cmd == "create-agent":
        kind = a[a.index("--kind") + 1] if "--kind" in a else "hybrid"
        cats = a[a.index("--categories") + 1].split(",") if "--categories" in a else None
        factory.create_agent(a[1], a[2], kind, cats)
    elif cmd == "create-tool":
        factory.create_tool(a[1], a[2], a[3])
    elif cmd == "create-skill":
        factory.create_skill(a[1], a[2], a[3], a[4], a[5])
    else:
        print(__doc__)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main(sys.argv[1:])
