"""Add lpips_holdout to recreation runs that were scored before it existed, without re-rendering.

    .venv/bin/python training/rescore_perceptual.py <slug> <run dir under training/runs/<slug>/> [...]

For each run dir holding rendered/ (shot run) or frames/ (whole video) frames and a scores.json (written by score_recreation.py), scores every rendered frame
against its reference frame with score_recreation.lpips_similarity (same masking), stores lpips_holdout per frame and in
scores.json "overall", and prints frame_score / grad_ssim_holdout / lpips_holdout side by side.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_recreation as SR  # noqa: E402


def rescore_run(D, run_dir, rect, sub_flags):
    scores_path = run_dir / "scores.json"
    sc = json.loads(scores_path.read_text(encoding="utf-8"))
    start = sc.get("reference_start", 0)
    # shot runs keep frames in rendered/, whole-video runs (recreate_video.py) in frames/
    rendered = sorted((run_dir / "rendered").glob("f_*.png")) or sorted((run_dir / "frames").glob("f_*.png"))
    if not rendered:
        sys.exit(f"{run_dir}: no f_*.png in rendered/ or frames/ -- nothing to score")
    for r in sc["frames"]:
        i = r["frame"] - start
        if r.get("missing") or i >= len(rendered):
            r["lpips_holdout"] = 0.0
            continue
        ref = SR.load_reference_frame(D, r["frame"], rect)
        rec = cv2.imread(str(rendered[i]))
        if rec.shape[:2] != ref.shape[:2]:
            rec = cv2.resize(rec, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
        r["lpips_holdout"] = round(SR.lpips_similarity(ref, rec, SR.build_mask(ref.shape[0], ref.shape[1], sub_flags[r["frame"]])), 4)
    sc["overall"]["lpips_holdout"] = round(float(np.mean([r["lpips_holdout"] for r in sc["frames"]])), 4)
    scores_path.write_text(json.dumps(sc, indent=1), encoding="utf-8")
    return sc["overall"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("runs", nargs="+")
    a = ap.parse_args()
    hits = [p for p in SR.REF.iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    rect = tuple(json.loads((D / "meta.json").read_text(encoding="utf-8"))["content_rect_640"])
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    sub_flags = [bool(r["text_on_screen"]["subtitle_present"]) for r in rows]
    for run in a.runs:
        o = rescore_run(D, SR.RUNS / D.name / run, rect, sub_flags)
        print(f"{run:45s} frame_score {o['frame_score']:.3f}  grad_ssim_holdout {o['grad_ssim_holdout']:.3f}  lpips_holdout {o['lpips_holdout']:.3f}", flush=True)


if __name__ == "__main__":
    main()
