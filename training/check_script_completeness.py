"""Audit a reference's per-frame script against the standard (training/SPEC.md section 4, CLAUDE.md rule 2).

    .venv/bin/python training/check_script_completeness.py <slug-or-fragment>

HARD errors (exit 1): a required group missing from a frame row or a shot script; a placeholder word standing in for a
measurement; a Blender directive without source_metric / confidence; a directive with a value but confidence 0.
PENDING (reported, not an error): `semantic` fields still NOT MEASURED because no vision pass has filled them yet.
Also prints how much of each section is NOT MEASURED, so a sparse script is visible rather than looking complete.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "reference"
ROW_GROUPS = ["lighting", "colour", "camera", "motion", "physics", "depth", "composition", "transition", "characters", "audio", "text_on_screen", "shot"]
SHOT_GROUPS = ["timing", "camera", "lighting", "motion", "physics", "composition", "colour", "transitions", "audio", "characters", "text_on_screen",
               "semantic", "blender_directives"]
PLACEHOLDER = re.compile(r"\b(tbd|todo|typical|assumed|guess(?:ed)?|probably|default value|placeholder|lorem)\b", re.I)


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, node


def main():
    frag = sys.argv[1] if len(sys.argv) > 1 else ""
    dirs = [p for p in OUT.iterdir() if p.is_dir() and frag in p.name]
    if len(dirs) != 1:
        sys.exit(f"'{frag}' matches {[d.name for d in dirs]}")
    D = dirs[0]
    hard, pending = [], Counter()
    nm_by_section, leaves_by_section = Counter(), Counter()

    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    missing = Counter(g for r in rows for g in ROW_GROUPS if g not in r)
    for g, n in missing.items():
        hard.append(f"frames_table: group '{g}' missing from {n} rows")
    if [r["frame"] for r in rows] != list(range(len(rows))):
        hard.append("frames_table: frame indices are not 0..N-1 in order")

    shot_files = sorted((D / "shots").glob("shot_*.json"))
    if not shot_files:
        hard.append("no shot scripts: run training/write_shot_scripts.py first")
    for f in shot_files:
        s = json.loads(f.read_text(encoding="utf-8"))
        for g in SHOT_GROUPS:
            if g not in s:
                hard.append(f"{f.name}: group '{g}' missing")
        for path, v in walk(s):
            top = path.split(".")[0].split("[")[0]
            leaves_by_section[top] += 1
            if isinstance(v, str) and v.startswith("NOT MEASURED"):
                nm_by_section[top] += 1
                if top == "semantic":
                    pending[path] += 1
            elif isinstance(v, str) and PLACEHOLDER.search(v) and "caveat" not in path and "note" not in path and "evidence" not in path:
                hard.append(f"{f.name}: placeholder wording at {path}: {v[:60]!r}")
            elif v is None:
                nm_by_section[top] += 1
        for i, d in enumerate(s.get("blender_directives", [])):
            for k in ("setting", "value", "source_metric", "confidence"):
                if k not in d:
                    hard.append(f"{f.name}: directive {i} lacks '{k}'")
            c = d.get("confidence")
            if not isinstance(c, (int, float)) or not 0 <= c <= 1:
                hard.append(f"{f.name}: directive {i} confidence {c!r} not in 0..1")
            elif isinstance(d.get("value"), str) and d["value"].startswith("NOT MEASURED") and c != 0:
                hard.append(f"{f.name}: directive {i} is NOT MEASURED but claims confidence {c}")
            elif d.get("value") in (None, [], {}) and c > 0:
                hard.append(f"{f.name}: directive {i} ({d.get('setting')}) has an empty value but confidence {c}")

    print(f"{D.name}: {len(rows)} frame rows, {len(shot_files)} shot scripts")
    print("NOT MEASURED share by section (a sparse-but-honest script is fine; an invisible one is not):")
    for sec in SHOT_GROUPS:
        if leaves_by_section[sec]:
            print(f"  {sec:20s} {100 * nm_by_section[sec] / leaves_by_section[sec]:5.1f}%  of {leaves_by_section[sec]} values")
    if pending:
        print(f"PENDING vision pass: {len(shot_files)} shots x {len(pending)} semantic fields still NOT MEASURED (fill via the frame-script-writer agent)")
    if hard:
        print(f"\n{len(hard)} HARD ERRORS:")
        for h in hard[:25]:
            print("  -", h)
        sys.exit(1)
    print("\nno hard errors: every group present, no placeholders, every directive sourced")


if __name__ == "__main__":
    main()
