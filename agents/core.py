"""Agent framework for the YouTube-automation project.

Every agent is: a SPEC (agent.json: role, inputs/outputs, tools, quality gates), TOOLS (plain python it can call), and its
own SKILL LIBRARY (skills/*.md in the same format the Blender agent uses; retrieved by trigger words, grown by use).
`agents/registry.json` lists all agents so the project can be inventoried and new ones created with `agents/factory.py`.

Agent kinds:  llm          decisions come from an LLM (via llm_router.py) grounded by skills
              hybrid       LLM planning + algorithmic tools (synthesis, rendering, measurement)
              algorithmic  deterministic, but with a skill library that parameterises it
              external     runs outside this repo's Python (e.g. Claude Code + Playwright)
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
REGISTRY = AGENTS_DIR / "registry.json"
sys.path.insert(0, str(ROOT / "blender_agent"))
import skills as SK  # noqa: E402  (the shared skill-library engine)

DEFAULT_CATEGORIES = ["technique", "rule", "workflow", "quality"]


def load_registry() -> list:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_registry(entries: list):
    REGISTRY.write_text(json.dumps(sorted(entries, key=lambda e: e["name"]), indent=2), encoding="utf-8")


def register(entry: dict):
    reg = [e for e in load_registry() if e["name"] != entry["name"]]
    reg.append(entry)
    save_registry(reg)


class Agent:
    """Base class. Subclasses implement run(); skills/quality helpers come for free."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.spec = json.loads((self.root / "agent.json").read_text(encoding="utf-8"))
        self.name = self.spec["name"]
        self.skills_dir = self.root / "skills"
        self.categories = self.spec.get("skill_categories") or DEFAULT_CATEGORIES

    # ---- skills
    def skills(self, query: str, k=3, **kw):
        with SK.library(self.skills_dir, self.categories):
            return SK.match(query, k=k, **kw)

    def skill_context(self, query: str, k=3, budget=3000) -> str:
        with SK.library(self.skills_dir, self.categories):
            return SK.context_for(query, k=k, budget=budget)

    def record_use(self, skill_ids, run: str, outcome="rendered", note=""):
        with SK.library(self.skills_dir, self.categories):
            SK.record_use(skill_ids, run, outcome, note)

    def all_skills(self, include_candidates=False):
        with SK.library(self.skills_dir, self.categories):
            return SK.load_all(include_candidates)

    def validate_skills(self):
        with SK.library(self.skills_dir, self.categories):
            return {s.id: SK.validate(s) for s in SK.load_all(True)}

    # ---- to implement
    def run(self, **kw):
        raise NotImplementedError(f"{self.name}.run() not implemented")

    def self_check(self) -> dict:
        """Cheap health check: spec fields present, skills valid, tools importable. Subclasses may extend."""
        problems = []
        for f in ("name", "role", "kind", "inputs", "outputs"):
            if not self.spec.get(f):
                problems.append(f"spec missing {f}")
        for sid, errs in self.validate_skills().items():
            problems += [f"skill {sid}: {e}" for e in errs]
        return {"agent": self.name, "ok": not problems, "problems": problems, "skills": len(self.all_skills())}


def load_agent(name: str) -> Agent:
    """Instantiate a registered agent that has a python entry (`entry`: 'module.py:ClassName' relative to its path)."""
    e = next((x for x in load_registry() if x["name"] == name), None)
    if not e:
        raise KeyError(f"unknown agent {name}")
    path = ROOT / e["path"]
    entry = e.get("entry")
    if not entry:
        raise ValueError(f"{name} has no python entry (kind={e['kind']})")
    mod_file, cls = entry.split(":")
    spec = importlib.util.spec_from_file_location(f"agent_{name}", path / mod_file)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path))
    spec.loader.exec_module(mod)
    return getattr(mod, cls)(path)
