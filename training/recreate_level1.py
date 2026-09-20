"""One full pass of the recreation loop at rung 1 (colour layout): measured grid -> Blender frames -> frame-by-frame score.

    .venv/bin/python training/recreate_level1.py <slug> <shot> [--grids 6x4,16x9,32x18]

For each grid resolution: area-average the measured 32x18 colour grid of the shot's frames, render them in Blender
(training/blender_level1.py, Workbench, one vertex per cell), then score with training/score_recreation.py. Prints the
score per resolution so the effect of each change is a measured delta. Runs land in training/runs/<slug>/level1_shotNN_<grid>/.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "blender_agent"))
from blender_runner import find_blender  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("shot", type=int)
    ap.add_argument("--grids", default="6x4,16x9,32x18")
    a = ap.parse_args()
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = meta["content_rect_640"]
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    lo, hi = next((s["start"], s["end"]) for s in json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"] if s["idx"] == a.shot)
    grid32 = np.load(D / "colour_grid32x18.npy")[lo:hi]
    results = {}
    for spec in a.grids.split(","):
        gw, gh = (int(v) for v in spec.split("x"))
        run = f"level1_shot{a.shot:02d}_{spec}"
        run_dir = HERE / "runs" / D.name / run
        run_dir.mkdir(parents=True, exist_ok=True)
        g = np.stack([cv2.resize(f, (gw, gh), interpolation=cv2.INTER_AREA) for f in grid32]) if (gw, gh) != (32, 18) else grid32
        np.save(run_dir / "grid.npy", g)
        (run_dir / "job.json").write_text(json.dumps({"grid": str(run_dir / "grid.npy"), "out_dir": str(run_dir / "rendered"), "width": W, "height": H}), encoding="utf-8")
        r = subprocess.run([find_blender(), "-b", "--python", str(HERE / "blender_level1.py"), "--", str(run_dir / "job.json")], capture_output=True, text=True)
        if "LEVEL1_DONE" not in r.stdout:
            sys.exit("Blender did not finish:\n" + (r.stdout + r.stderr)[-1500:])
        s = subprocess.run([sys.executable, str(HERE / "score_recreation.py"), D.name, str(run_dir / "rendered"), "--start", str(lo), "--run", run],
                           capture_output=True, text=True)
        sc = json.loads((HERE / "runs" / D.name / run / "scores.json").read_text(encoding="utf-8"))
        results[spec] = sc["overall"]
        print(f"shot {a.shot} frames {lo}-{hi} ({hi - lo}f)  grid {spec:>5s}: frame_score={sc['overall']['frame_score']:.4f} ssim={sc['overall']['ssim']:.3f} "
              f"hist={sc['overall']['hist']:.3f} edge_f1={sc['overall']['edge_f1']:.3f} dhue={sc['overall']['dhue']}  coverage={sc['coverage']:.0%}")
    return results


if __name__ == "__main__":
    main()
