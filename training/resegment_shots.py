"""Re-detect shot boundaries of already-ingested references and carry every per-shot file over to the new numbering.

    .venv/bin/python training/resegment_shots.py [slug fragment ...]            # print the plan, write nothing
    .venv/bin/python training/resegment_shots.py [slug fragment ...] --apply    # back up, then write

Shot detection only ever gains cuts here (ingest_reference.detect_isolated_cuts), so each new shot lies inside one old
shot. A new shot equal to an old one keeps that shot's entries under its new index; a shot that was split loses them --
its measurements (outlines, landmarks, line art) must be re-measured and its semantic layer re-filled by a vision pass,
since a description of the whole old shot is not a description of either half. Per-shot files handled: semantic.json,
face_landmarks.json, character_outlines.json, line_art.json. shots/, sheets/ and script.json are rebuilt afterwards by
write_shot_scripts.py. Before writing, the old files are copied to <reference>/backup_pre_resegment_<date>/.
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest_reference as IR  # noqa: E402

PER_SHOT_FILES = ("semantic.json", "face_landmarks.json", "character_outlines.json", "line_art.json")


def map_new_to_old(old, new):
    """{new idx: old idx} for new shots identical to an old one, and {old idx: [new idx]} for old shots that were split."""
    same, split = {}, {}
    for n in new:
        parent = next(o for o in old if o["start"] <= n["start"] < o["end"])
        assert n["end"] <= parent["end"], f"new shot {n} crosses old boundary {parent} -- resegmenting only adds cuts"
        if (n["start"], n["end"]) == (parent["start"], parent["end"]):
            same[n["idx"]] = parent["idx"]
        else:
            split.setdefault(parent["idx"], []).append(n["idx"])
    return same, split


def remap_per_shot_file(path, same):
    data = json.loads(path.read_text(encoding="utf-8"))
    data["shots"] = {str(n): data["shots"][str(o)] for n, o in sorted(same.items()) if str(o) in data["shots"]}
    return data


def resegment(D, apply):
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    old_doc = json.loads((D / "shots.json").read_text(encoding="utf-8"))
    old = old_doc["shots"]
    new = IR.detect_shots(sorted((D / "frames").glob("f_*.jpg")), meta["fps"])
    same, split = map_new_to_old(old, new)
    print(f"{D.name}: {len(old)} -> {len(new)} shots")
    for o, ns in split.items():
        print(f"  old shot {o} [{old[o]['start']}, {old[o]['end']}) -> " + ", ".join(f"new {n} [{new[n]['start']}, {new[n]['end']})" for n in ns))
    present = [f for f in PER_SHOT_FILES if (D / f).exists()]
    split_new = sorted(n for ns in split.values() for n in ns)
    print(f"  per-shot files: {present}; to re-measure / re-describe: new shots {split_new}")
    if not split or not apply:
        return split_new
    backup = D / f"backup_pre_resegment_{datetime.date.today():%Y%m%d}"
    if backup.exists():
        sys.exit(f"{backup} exists -- refusing to overwrite a backup")
    backup.mkdir()
    for f in present + ["shots.json", "script.json"]:
        if (D / f).exists():
            shutil.copy2(D / f, backup / f)
    for f in present:
        (D / f).write_text(json.dumps(remap_per_shot_file(D / f, same), indent=1 if f in ("semantic.json", "line_art.json") else None),
                           encoding="utf-8")
    (D / "shots.json").write_text(json.dumps({**old_doc, "shots": new}, indent=1), encoding="utf-8")
    for p in list((D / "shots").glob("shot_*.json")) + list((D / "sheets").glob("shot_*.jpg")):
        p.unlink()                                  # rebuilt by write_shot_scripts.py under the new numbering
    print(f"  written; old files in {backup}")
    return split_new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    refs = sorted(p for p in IR.OUT.iterdir() if p.is_dir() and (p / "shots.json").exists()
                  and (not a.slugs or any(s in p.name for s in a.slugs)))
    plan = {D.name: resegment(D, a.apply) for D in refs}
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
