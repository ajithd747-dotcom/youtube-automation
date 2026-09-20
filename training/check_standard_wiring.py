"""Fail loudly if the per-frame script standard has been unwired from any place that is supposed to enforce it.

    .venv/bin/python training/check_standard_wiring.py

The standard has to survive a change of VPS, so it lives in the repo in five places. This checks all five still agree.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "blender_agent"))
GROUPS = ["lighting", "motion", "physics", "composition", "colour", "transitions", "audio", "characters"]
PIPELINE_FILES = ["ingest_reference.py", "describe_frames.py", "describe_audio.py", "detect_anime_faces.py", "write_shot_scripts.py",
                  "check_script_completeness.py", "score_recreation.py", "calibrate_scores.py", "measure_colour_grid.py", "measure_lines.py",
                  "blender_layout_common.py", "blender_level1.py", "blender_level2.py", "recreate_level1.py", "recreate_level2.py"]
problems = []


def need(cond, msg):
    if not cond:
        problems.append(msg)


claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8") if (ROOT / "CLAUDE.md").exists() else ""
need("per-frame script standard" in claude_md.lower() and "NOT MEASURED" in claude_md, "CLAUDE.md lacks the per-frame script standard rule")
for g in GROUPS:
    need(g in claude_md.lower(), f"CLAUDE.md rule does not name '{g}'")

spec = (ROOT / "training" / "SPEC.md").read_text(encoding="utf-8")
need("## 4. The per-frame script" in spec, "training/SPEC.md lost section 4")

skill = ROOT / ".claude" / "skills" / "frame-script-standard" / "SKILL.md"
need(skill.exists() and skill.read_text(encoding="utf-8").startswith("---\nname: frame-script-standard"), "project skill missing or malformed")

agent = ROOT / ".claude" / "agents" / "frame-script-writer.md"
text = agent.read_text(encoding="utf-8") if agent.exists() else ""
need(re.search(r"^model: sonnet$", text, re.M) is not None and re.search(r"^effort: high$", text, re.M) is not None, "frame-script-writer agent missing or model/effort not pinned")

for f in PIPELINE_FILES:
    need((ROOT / "training" / f).exists(), f"the skill points at training/{f} but it does not exist")

try:
    import director
    import skills as SK
    ids = [s.id for s in SK.standing_rules()]
    need("per-frame-script-standard" in ids, "Blender agent skill is not an always-on standing rule")
    guidance, used = director.skill_guidance("completely unrelated words", "cinematic")
    need(used and used[0] == "per-frame-script-standard", "director does not put the standard first for an unrelated query")
except Exception as e:  # noqa: BLE001
    problems.append(f"could not load the Blender agent skill library: {e}")

if problems:
    print("STANDARD IS NOT FULLY WIRED:")
    [print("  -", p) for p in problems]
    sys.exit(1)
print("per-frame script standard: wired in CLAUDE.md, SPEC.md, project skill, project agent, Blender agent always-on skill")
