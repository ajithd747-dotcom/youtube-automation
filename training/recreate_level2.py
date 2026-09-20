"""One pass of the recreation loop at rung 2 (colour layout + measured line work), with line parameters to adjust.

    .venv/bin/python training/recreate_level2.py <slug> <shot> [--grid 32x18] [--canny 60,120] [--minlen 10] [--half-width 0.75] [--tag NAME]

Measures the shot's line contours from the reference frames (12 workers), renders them over the colour layout in Blender
(training/blender_level2.py) and scores with training/score_recreation.py.
"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "blender_agent"))
sys.path.insert(0, str(HERE))
from blender_runner import find_blender  # noqa: E402
from measure_lines import extract_line_segments  # noqa: E402
from score_recreation import build_mask  # noqa: E402


def lines_for_frame(args):
    path, rect, canny, minlen, subtitle_present = args
    x0, y0, x1, y1 = rect
    im = cv2.imread(str(path))[y0:y1, x0:x1]
    a, b, c, npoly = extract_line_segments(im, canny=canny, min_len=minlen, keep_mask=build_mask(im.shape[0], im.shape[1], subtitle_present))
    return a, b, c, npoly


def run(slug, shot, grid="32x18", canny=(60, 120), minlen=10, half_width=0.75, tag=None):
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = meta["content_rect_640"]
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    lo, hi = next((s["start"], s["end"]) for s in json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"] if s["idx"] == shot)
    gw, gh = (int(v) for v in grid.split("x"))
    g32 = np.load(D / "colour_grid32x18.npy")[lo:hi]
    g = np.stack([cv2.resize(f, (gw, gh), interpolation=cv2.INTER_AREA) for f in g32]) if (gw, gh) != (32, 18) else g32
    name = tag or f"level2_shot{shot:02d}_{grid}_c{canny[0]}-{canny[1]}_m{minlen}_w{half_width}"
    run_dir = HERE / "runs" / D.name / name
    run_dir.mkdir(parents=True, exist_ok=True)
    np.save(run_dir / "grid.npy", g)
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()[lo:hi]]
    tasks = [(D / "frames" / f"f_{i + 1:05d}.jpg", tuple(rect), canny, minlen, bool(rows[i - lo]["text_on_screen"]["subtitle_present"])) for i in range(lo, hi)]
    with mp.Pool(os.cpu_count() or 4) as pool:
        res = pool.map(lines_for_frame, tasks, chunksize=2)
    arrays = {}
    for f, (a, b, c, _) in enumerate(res):
        arrays[f"a_{f}"], arrays[f"b_{f}"], arrays[f"c_{f}"] = a, b, c
    np.savez(run_dir / "lines.npz", **arrays)
    (run_dir / "job.json").write_text(json.dumps({"grid": str(run_dir / "grid.npy"), "lines": str(run_dir / "lines.npz"), "out_dir": str(run_dir / "rendered"),
                                                  "width": W, "height": H, "half_width_px": half_width}), encoding="utf-8")
    r = subprocess.run([find_blender(), "-b", "--python", str(HERE / "blender_level2.py"), "--", str(run_dir / "job.json")], capture_output=True, text=True)
    if "LEVEL2_DONE" not in r.stdout:
        sys.exit("Blender did not finish:\n" + (r.stdout + r.stderr)[-1500:])
    subprocess.run([sys.executable, str(HERE / "score_recreation.py"), D.name, str(run_dir / "rendered"), "--start", str(lo), "--run", name], capture_output=True, text=True)
    sc = json.loads((HERE / "runs" / D.name / name / "scores.json").read_text(encoding="utf-8"))
    o = sc["overall"]
    segs = int(np.mean([len(res[f][0]) for f in range(len(res))]))
    print(f"shot {shot} ({hi - lo}f) grid {grid} canny {canny} minlen {minlen} halfwidth {half_width}: frame_score={o['frame_score']:.4f} ssim={o['ssim']:.3f} "
          f"hist={o['hist']:.3f} edge_f1={o['edge_f1']:.3f} holdout_grad_ssim={o['grad_ssim_holdout']:.3f} dhue={o['dhue']}  (~{segs} segments/frame)", flush=True)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("shot", type=int)
    ap.add_argument("--grid", default="32x18")
    ap.add_argument("--canny", default="60,120")
    ap.add_argument("--minlen", type=int, default=10)
    ap.add_argument("--half-width", type=float, default=0.75)
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    run(a.slug, a.shot, a.grid, tuple(int(v) for v in a.canny.split(",")), a.minlen, a.half_width, a.tag)


if __name__ == "__main__":
    main()
