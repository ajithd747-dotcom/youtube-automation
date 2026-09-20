"""Skill library for the Blender video agent.

A *skill* is one verified, reusable piece of animation know-how stored as a Markdown file with YAML front matter in
blender_agent/skills/<category>/<id>.md. It says WHAT it achieves, WHEN to use it (the trigger words/situations that
identify it in a script or shot), HOW (procedure + measured parameters + code) and what goes wrong (pitfalls). The agent
retrieves matching skills for every script segment and feeds them to its director / coder.

Skills come from three places; `verified` and `reference` ones are used by the agent, `candidate`s never are:
  * authored from finished videos I made (each links an exemplar clip in skills/exemplars/ and a headless test snippet)
  * distilled from reference videos / books (skill_extract.py builds the evidence, humans/LLM distill, tests verify)
  * proposed automatically after each render (learn_from_run) as `candidate`s, promoted only once their test passes

CLI:  python blender_agent/skills.py list [--all] | show <id> | match "<text>" | validate | verify [id] | stats
                                       | learn <run-name> | promote <id> | new <id> <category>
"""
import ast
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE / "skills"
CAND_DIR = SKILLS_DIR / "candidates"
STATS = SKILLS_DIR / "stats.json"
EXEMPLARS = SKILLS_DIR / "exemplars"

CATEGORIES = ["physics", "motion", "character", "camera", "lighting", "materials", "effects", "composition", "pacing",
              "style-2d", "audio", "workflow", "performance"]
KINDS = ["recipe", "technique", "rule", "pitfall"]
STATUSES = ["verified", "reference", "candidate", "deprecated"]  # verified = tested/used in a finished video; reference = distilled from a trusted source, advisory only; candidate = auto-proposed, never used
STOP = set("a an the of to in is it and or for on with as at by be this that from are was if not you can your".split())


from contextlib import contextmanager


@contextmanager
def library(root, categories=None):
    """Point every function in this module at another skill library (each agent keeps its own skills/ folder)."""
    global SKILLS_DIR, CAND_DIR, STATS, EXEMPLARS, CATEGORIES
    old = (SKILLS_DIR, CAND_DIR, STATS, EXEMPLARS, CATEGORIES)
    SKILLS_DIR = Path(root)
    CAND_DIR, STATS, EXEMPLARS = SKILLS_DIR / "candidates", SKILLS_DIR / "stats.json", SKILLS_DIR / "exemplars"
    CATEGORIES = list(categories) if categories else old[4]
    try:
        yield
    finally:
        SKILLS_DIR, CAND_DIR, STATS, EXEMPLARS, CATEGORIES = old


class Skill:
    def __init__(self, meta: dict, body: str, path: Path):
        self.meta, self.body, self.path = meta, body, path
        self.id = meta["id"]
        self.name = meta.get("name", self.id)
        self.category = meta.get("category", "workflow")
        self.kind = meta.get("kind", "technique")
        self.status = meta.get("status", "candidate")
        self.applies_to = meta.get("applies_to") or ["any"]
        self.triggers = [str(t).lower() for t in (meta.get("triggers") or [])]
        self.when = " ".join(str(meta.get("when_to_use", "")).split())
        self.recipe = meta.get("uses_recipe")

    def section(self, title: str) -> str:
        m = re.search(rf"^##\s+{re.escape(title)}[^\n]*\n(.*?)(?=^##\s|\Z)", self.body, flags=re.S | re.M | re.I)
        return m.group(1).strip() if m else ""

    def procedure(self) -> str:
        """The how-to part: '## Procedure', or '## Rules' / '## Parameters...' / '## Evidence' for rule-type skills."""
        for title in ("Procedure", "Rules", "Parameters", "Evidence"):
            t = self.section(title)
            if t:
                return t
        return ""

    def code_blocks(self):
        return re.findall(r"```python\s*\n(.*?)```", self.body, flags=re.S)

    def brief(self, chars=900) -> str:
        """Compact form for LLM prompts: when to use + procedure + pitfalls."""
        tag = "" if self.status == "verified" else " [advisory: from a reference source, not yet tested]"
        parts = [f"SKILL {self.id} ({self.category}/{self.kind}){tag}: {self.name}", f"  use when: {self.when}"]
        proc = self.procedure()
        if proc:
            parts.append("  procedure: " + " ".join(proc.split())[:chars // 2])
        for title in ("Parameters that worked", "Pitfalls"):
            s = self.section(title)
            if s:
                parts.append(f"  {title.lower()}: " + " ".join(s.split())[:chars // 2])
        return "\n".join(parts)[: chars * 2]


# ----------------------------------------------------------------------------- loading
def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.S)
    if not m:
        raise ValueError(f"{path.name}: missing front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    if "id" not in meta:
        raise ValueError(f"{path.name}: front matter has no id")
    return Skill(meta, m.group(2), path)


def load_all(include_candidates=False):
    out = []
    dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir() and p.name not in ("sources", "exemplars", "candidates", "tests", "runs")]
    files = [f for d in dirs for f in sorted(d.glob("*.md"))]
    if include_candidates and CAND_DIR.exists():
        files += sorted(CAND_DIR.glob("*.md"))
    for f in files:
        if f.name.lower() == "readme.md":
            continue
        try:
            s = parse_file(f)
        except Exception as e:
            print(f"[skills] skipped {f.name}: {e}")
            continue
        if include_candidates or s.status in ("verified", "reference"):
            out.append(s)
    return out


def load_stats() -> dict:
    try:
        return json.loads(STATS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_stats(st: dict):
    STATS.write_text(json.dumps(st, indent=1), encoding="utf-8")


# ----------------------------------------------------------------------------- matching (BM25 + trigger boost)
def tokens(text: str):
    toks = []
    for w in re.findall(r"[a-z][a-z0-9'\-]+", text.lower()):
        toks.append(w)
        if "-" in w:
            toks.extend(w.split("-"))
    return [t for t in toks if t not in STOP and len(t) > 2]


def _stem(w: str) -> str:
    for suf in ("ing", "ers", "er", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def standing_rules():
    """Skills marked `always: true` in their front matter: rules that apply to every request, so they are added to the
    agent's context without waiting for a trigger match (the per-frame script standard is one)."""
    return [s for s in load_all() if s.meta.get("always") and s.status in ("verified", "reference")]


def match(query: str, k=4, style=None, kinds=None, categories=None, include_candidates=False, min_score=0.5):
    """Rank skills for a script segment / shot description. Returns [(score, Skill)]."""
    skills = [s for s in load_all(include_candidates)
              if (not kinds or s.kind in kinds) and (not categories or s.category in categories)
              and (not style or "any" in s.applies_to or style in s.applies_to)]
    if not skills:
        return []
    q = [_stem(t) for t in tokens(query)]
    qtext = query.lower()
    docs = []
    for s in skills:
        toks = [_stem(t) for t in tokens(f"{s.name} {s.when} " + " ".join(s.triggers) * 3 + " " + " ".join(map(str, s.meta.get("tags", []))))]
        docs.append(toks)
    n = len(docs)
    df = Counter(t for d in docs for t in set(d))
    avg = sum(len(d) for d in docs) / n
    scored = []
    for s, d in zip(skills, docs):
        tf = Counter(d)
        sc = 0.0
        for t in set(q):
            f = tf.get(t)
            if f:
                sc += math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(d) / avg))
        # explicit trigger phrases found verbatim in the text are the strongest signal
        sc += sum(2.0 for t in s.triggers if len(t) > 3 and t in qtext)
        if sc >= min_score:
            scored.append((round(sc, 2), s))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def context_for(query: str, k=3, style=None, kinds=None, budget=3500) -> str:
    out, used = [], 0
    for _, s in match(query, k=k, style=style, kinds=kinds):
        b = s.brief()
        if used + len(b) > budget:
            break
        out.append(b)
        used += len(b)
    return "\n\n".join(out)


def recipe_skills(style="cinematic"):
    return {s.recipe: s for s in load_all() if s.recipe and (style in s.applies_to or "any" in s.applies_to)}


# ----------------------------------------------------------------------------- usage statistics ("skills grow")
def record_use(skill_ids, run: str, outcome="rendered", note=""):
    st = load_stats()
    now = time.strftime("%Y-%m-%d %H:%M")
    for sid in dict.fromkeys(skill_ids):
        e = st.setdefault(sid, {"uses": 0, "ok": 0, "failed": 0, "runs": []})
        e["uses"] += 1
        e["ok" if outcome == "rendered" else "failed"] += 1
        e["last_used"] = now
        if run not in e["runs"]:
            e["runs"].append(run)
        if note:
            e["last_note"] = note
    save_stats(st)


def mark_verified(sid: str, ok: bool, detail=""):
    st = load_stats()
    e = st.setdefault(sid, {"uses": 0, "ok": 0, "failed": 0, "runs": []})
    e["verified_at" if ok else "verify_failed_at"] = time.strftime("%Y-%m-%d %H:%M")
    e["verify_detail"] = detail[:300]
    save_stats(st)


# ----------------------------------------------------------------------------- validation / verification
def validate(s: Skill):
    errs = []
    m = s.meta
    for f in ("id", "name", "category", "kind", "when_to_use"):
        if not m.get(f):
            errs.append(f"missing {f}")
    if s.category not in CATEGORIES:
        errs.append(f"unknown category {s.category}")
    if s.kind not in KINDS:
        errs.append(f"unknown kind {s.kind}")
    if s.status in ("verified", "reference") and len(s.triggers) < 3:
        errs.append("verified skills need >=3 triggers (how else would the agent identify them?)")
    if s.status in ("verified", "reference") and not s.procedure():
        errs.append("missing '## Procedure' (or Rules/Parameters/Evidence) section")
    for i, code in enumerate(s.code_blocks()):
        try:
            ast.parse(code)
        except SyntaxError as e:
            errs.append(f"code block {i + 1}: {e}")
    if m.get("exemplar") and not (SKILLS_DIR / m["exemplar"]).exists():
        errs.append(f"exemplar missing: {m['exemplar']}")
    if m.get("test") and not (SKILLS_DIR / m["test"]).exists():
        errs.append(f"test missing: {m['test']}")
    if m.get("uses_recipe"):
        try:
            sys.path.insert(0, str(HERE / "blender_side"))
            import dsl
            if m["uses_recipe"] not in dsl.RECIPES:
                errs.append(f"uses_recipe {m['uses_recipe']} not in dsl.RECIPES")
        except Exception:
            pass
    return errs


def verify(s: Skill, timeout=300):
    """Run the skill's headless test (a bpy snippet executed after a small scene is built). Returns (ok, detail)."""
    tp = s.meta.get("test")
    if not tp:
        return None, "no test snippet"
    sys.path.insert(0, str(HERE))
    import blender_runner
    code = (SKILLS_DIR / tp).read_text(encoding="utf-8")
    shot = {"style": "cinematic", "recipe": "robot_intro", "mood": "studio", "title": "", "params": {}}
    if s.meta.get("test_shot"):
        shot = s.meta["test_shot"]
    res = blender_runner.run_job({"shot": shot, "width": 320, "height": 180, "fps": 12, "duration": 2.0, "quality": "draft",
                                  "mode": "check", "custom_code": code}, timeout=timeout)
    ok = bool(res.get("ok"))
    detail = "ok" if ok else f"{res.get('error')} {res.get('traceback', '')[-300:]}"
    mark_verified(s.id, ok, detail)
    return ok, detail


# ----------------------------------------------------------------------------- candidates + learning loop
def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60]


def write_skill(path: Path, meta: dict, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=110) + "---\n" + body.strip() + "\n", encoding="utf-8")


def save_candidates(items, origin="auto"):
    """items: dicts with id/name/category/when_to_use/triggers/steps/pitfalls/evidence. Written as unverified candidates."""
    known = {s.id for s in load_all(include_candidates=True)}
    n = 0
    for it in items:
        sid = _slug(it.get("id") or it.get("name"))
        if not sid or sid in known:
            continue
        cat = it.get("category") if it.get("category") in CATEGORIES else "workflow"
        meta = {"id": sid, "name": it.get("name", sid), "category": cat, "kind": it.get("kind", "technique"), "status": "candidate",
                "applies_to": ["any"], "when_to_use": it.get("when_to_use", ""), "triggers": [str(t) for t in it.get("triggers", [])],
                "source": [it.get("source", origin)], "version": 1}
        steps = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(it.get("steps", [])))
        pit = "\n".join(f"- {p}" for p in it.get("pitfalls", []))
        body = f"## Procedure\n{steps}\n\n## Pitfalls\n{pit}\n\n## Evidence\n{it.get('evidence', '')}\n"
        if it.get("code"):
            body += f"\n## Code\n```python\n{it['code']}\n```\n"
        write_skill(CAND_DIR / f"{sid}.md", meta, body)
        known.add(sid)
        n += 1
    return n


def promote(sid: str, force=False):
    src = CAND_DIR / f"{sid}.md"
    if not src.exists():
        raise SystemExit(f"no candidate {sid}")
    s = parse_file(src)
    errs = [e for e in validate(s) if "verified skills need" not in e and "Procedure" not in e]
    if errs and not force:
        raise SystemExit("cannot promote: " + "; ".join(errs))
    ok, detail = verify(s) if s.meta.get("test") else (None, "no test")
    if s.meta.get("test") and not ok and not force:
        raise SystemExit(f"test failed, not promoted: {detail}")
    s.meta["status"] = "verified"
    dest = SKILLS_DIR / s.category / f"{sid}.md"
    write_skill(dest, s.meta, s.body)
    src.unlink()
    print(f"promoted {sid} -> {dest.relative_to(HERE)}")


def learn_from_run(work_dir: Path, run_name: str, log=print):
    """Retrospective after a finished video: update usage stats and turn concrete signals into candidate skills.

    Signals: (1) which recipe skills were used, (2) shots the human re-planned in plan.json (director preference),
    (3) shots that needed the draft-quality fallback (pitfall), (4) coder fixes stored in learned.jsonl (technique)."""
    plan_f, auto_f = work_dir / "plan.json", work_dir / "plan.auto.json"
    if not plan_f.exists():
        return 0
    plan = json.loads(plan_f.read_text(encoding="utf-8"))
    rs = {r: s.id for r, s in recipe_skills("cinematic").items()}
    used = [rs[x["recipe"]] for x in plan.get("shots", []) if x.get("recipe") in rs]
    if used:
        record_use(used, run_name)
    cands = []
    if auto_f.exists():  # human edits to the plan = preferences worth remembering
        auto = json.loads(auto_f.read_text(encoding="utf-8"))
        for i, (a, b) in enumerate(zip(auto.get("shots", []), plan.get("shots", []))):
            if a.get("recipe") != b.get("recipe") or a.get("mood") != b.get("mood"):
                text = plan["segments"][i][2] if i < len(plan.get("segments", [])) else ""
                cands.append({"id": f"pref-{_slug(run_name)}-shot{i + 1}", "name": f"Preference: {b.get('recipe')} ({b.get('mood')}) fits '{text[:50]}'",
                              "category": "composition", "kind": "rule", "when_to_use": f"A segment like: {text[:160]}",
                              "triggers": [w for w in tokens(text)][:8], "steps": [f"Use recipe {b.get('recipe')} in mood {b.get('mood')} (a human changed the automatic choice {a.get('recipe')}/{a.get('mood')})."],
                              "evidence": f"plan edit in run {run_name}"})
    if not cands:
        return 0
    n = save_candidates(cands, origin=f"run {run_name}")
    log(f"[skills] {n} new candidate skill(s) proposed from this run (skills/candidates/, unverified)")
    return n


# ----------------------------------------------------------------------------- CLI
def _row(s: Skill, st):
    e = st.get(s.id, {})
    return f"{s.id:38s} {s.category:12s} {s.kind:9s} {s.status:9s} uses={e.get('uses', 0):2d}  {s.name[:60]}"


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd, st = argv[0], load_stats()
    if cmd == "list":
        allskills = load_all(include_candidates="--all" in argv)
        by = Counter(s.category for s in allskills)
        for s in sorted(allskills, key=lambda x: (x.category, x.id)):
            print(_row(s, st))
        print(f"\n{len(allskills)} skills: " + ", ".join(f"{c}={n}" for c, n in sorted(by.items())))
    elif cmd == "show":
        s = next((x for x in load_all(True) if x.id == argv[1]), None)
        print(s.path.read_text(encoding="utf-8") if s else "not found")
    elif cmd == "match":
        q = " ".join(a for a in argv[1:] if not a.startswith("--"))
        for sc, s in match(q, k=6):
            print(f"{sc:6.2f}  {s.id:36s} {s.when[:100]}")
    elif cmd == "validate":
        bad = 0
        for s in load_all(True):
            errs = validate(s)
            bad += bool(errs)
            print(("FAIL " if errs else "ok   ") + s.id, "; ".join(errs))
        sys.exit(1 if bad else 0)
    elif cmd == "verify":
        ids = argv[1:] or [s.id for s in load_all() if s.meta.get("test")]
        for s in [x for x in load_all(True) if x.id in ids]:
            ok, d = verify(s)
            print(("PASS " if ok else "FAIL " if ok is False else "SKIP ") + s.id, "" if ok else d)
    elif cmd == "stats":
        for sid, e in sorted(st.items(), key=lambda kv: -kv[1].get("uses", 0)):
            print(f"{sid:38s} uses={e['uses']:3d} ok={e['ok']:3d} failed={e['failed']:2d} last={e.get('last_used', '-')} verified={e.get('verified_at', '-')}")
    elif cmd == "learn":
        learn_from_run(HERE / "work" / argv[1], argv[1])
    elif cmd == "promote":
        promote(argv[1], force="--force" in argv)
    elif cmd == "new":
        sid, cat = argv[1], argv[2]
        write_skill(SKILLS_DIR / cat / f"{sid}.md",
                    {"id": sid, "name": sid.replace("-", " ").title(), "category": cat, "kind": "technique", "status": "candidate",
                     "applies_to": ["any"], "when_to_use": "TODO", "triggers": [], "source": ["own-experience"], "version": 1},
                    "## Procedure\n1. TODO\n\n## Pitfalls\n- TODO\n")
        print("created", SKILLS_DIR / cat / f"{sid}.md")
    else:
        print(__doc__)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main(sys.argv[1:])
