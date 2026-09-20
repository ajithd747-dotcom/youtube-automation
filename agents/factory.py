"""Agent factory: scaffolds new agents, tools and skills so the project can grow.

    python agents/cli.py create-agent <name> "<role>" [--kind hybrid] [--categories a,b,c]
    python agents/cli.py create-tool  <agent> <tool_name> "<what it does>"
    python agents/cli.py create-skill <agent> <skill-id> <category> "<when to use>" "<trigger1,trigger2,trigger3>"

A new agent gets the standard layout (spec, entry class, tools/, skills/ with a starter skill, tests/, README) and is added
to agents/registry.json; from then on `agents/cli.py list|count|verify` sees it and the skill engine can grow its library.
"""
import json
import re
import sys
from pathlib import Path

from core import AGENTS_DIR, DEFAULT_CATEGORIES, ROOT, SK, register

AGENT_PY = '''"""{title} - {role}"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Agent  # noqa: E402


class {cls}(Agent):
    """{role}"""

    def run(self, task: str = "", **kw):
        """Plan with the skill library, then call tools/. Replace this stub with the real logic."""
        hits = self.skills(task, k=3)
        return {{"task": task, "skills": [s.id for _, s in hits], "note": "stub: implement run() using tools/"}}
'''

TOOL_PY = '''"""Tool: {desc}"""


def run(**kwargs):
    """{desc}. Return a plain dict/path so the agent (and its tests) can inspect the result."""
    raise NotImplementedError("implement {name}")
'''

TEST_PY = '''"""Smoke test for the {name} agent: spec + skills are valid and run() answers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from core import load_agent  # noqa: E402

agent = load_agent("{name}")
report = agent.self_check()
assert report["ok"], report
print("ok", report)
'''

README = '''# {title}

{role}

- kind: `{kind}`
- spec: `agent.json` - tools in `tools/` - skills in `skills/` (grown with `python agents/cli.py create-skill ...`)
- health check: `python agents/cli.py verify {name}`
'''


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def create_agent(name, role, kind="hybrid", categories=None, tools=None, entry_cls=None):
    name = slug(name)
    d = AGENTS_DIR / name
    if d.exists():
        raise SystemExit(f"agent {name} already exists")
    cats = categories or DEFAULT_CATEGORIES
    cls = entry_cls or "".join(w.capitalize() for w in name.split("-")) + "Agent"
    title = name.replace("-", " ").title()
    (d / "tools").mkdir(parents=True)
    (d / "tests").mkdir()
    for c in cats:
        (d / "skills" / c).mkdir(parents=True, exist_ok=True)
    spec = {"name": name, "title": title, "role": role, "kind": kind, "inputs": ["task"], "outputs": ["result"],
            "tools": [], "skill_categories": cats, "quality_gates": ["python agents/cli.py verify " + name], "llm": kind in ("llm", "hybrid")}
    (d / "agent.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    (d / "agent.py").write_text(AGENT_PY.format(title=title, role=role, cls=cls), encoding="utf-8")
    (d / "tools" / "__init__.py").write_text("", encoding="utf-8")
    (d / "tests" / f"test_{name.replace('-', '_')}.py").write_text(TEST_PY.format(name=name), encoding="utf-8")
    (d / "README.md").write_text(README.format(title=title, role=role, kind=kind, name=name), encoding="utf-8")
    register({"name": name, "title": title, "kind": kind, "role": role, "path": f"agents/{name}", "entry": f"agent.py:{cls}",
              "skills_dir": f"agents/{name}/skills", "llm": spec["llm"], "created_by": "factory"})
    create_skill(name, f"{name}-getting-started", cats[0], f"Starting any task for the {title} agent.",
                 [name.split("-")[0], "start", "task", title.lower()], status="candidate",
                 body="## Procedure\n1. TODO: describe the first concrete step.\n\n## Pitfalls\n- TODO\n")
    for t in tools or []:
        create_tool(name, t, f"{t} tool")
    print(f"created agent {name} in {d.relative_to(ROOT)}")
    return d


def create_tool(agent, tool_name, desc):
    d = AGENTS_DIR / agent
    f = d / "tools" / f"{slug(tool_name).replace('-', '_')}.py"
    if f.exists():
        raise SystemExit(f"tool exists: {f}")
    f.write_text(TOOL_PY.format(desc=desc, name=tool_name), encoding="utf-8")
    spec = json.loads((d / "agent.json").read_text(encoding="utf-8"))
    spec["tools"].append({"name": tool_name, "file": f"tools/{f.name}", "description": desc})
    (d / "agent.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print("created tool", f.relative_to(ROOT))


def create_skill(agent, skill_id, category, when, triggers, status="candidate", body=None):
    d = AGENTS_DIR / agent / "skills"
    spec = json.loads((AGENTS_DIR / agent / "agent.json").read_text(encoding="utf-8"))
    cats = spec.get("skill_categories") or DEFAULT_CATEGORIES
    if category not in cats:
        raise SystemExit(f"category must be one of {cats}")
    triggers = [t.strip() for t in (triggers.split(",") if isinstance(triggers, str) else triggers) if t.strip()]
    meta = {"id": skill_id, "name": skill_id.replace("-", " ").title(), "category": category, "kind": "technique", "status": status,
            "applies_to": ["any"], "when_to_use": when, "triggers": triggers, "source": ["factory scaffold"], "version": 1}
    SK.write_skill(d / category / f"{skill_id}.md", meta, body or "## Procedure\n1. TODO\n\n## Pitfalls\n- TODO\n")
    print("created skill", (d / category / f"{skill_id}.md").relative_to(ROOT))
