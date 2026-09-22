"""Per-shot colour and tone comparison: a run's rendered frames against the reference frames they recreate.

Answers "is the render too colourful / too flat, and where", with both sides measured by the same code as
training/describe_frames.py (crop off the bars, resize to 320 wide, INTER_AREA). Reference frames are
re-measured rather than read from frames_table.jsonl so neither side gets a different code path.

    .venv/bin/python training/compare_render_to_reference.py <slug> <run> [--stride 5] [--shots 2,9,17] [--json out.json]

Reports, per shot and over the run: mean Lab a/b (signed, as the shot scripts record them), HSV saturation,
Hasler-Susstrunk colourfulness, luma mean/std/p5/p95 and the share of dark pixels. The last three are what
separates "the lights are the wrong colour" from "the render has no deep shadows": a render whose luma mean
matches but whose p5 is lifted has lost the reference's dark, cool-tinted line art and shadow, and that loss
alone raises the render's mean chroma.
"""
import argparse
import json
import math
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

MEASURE_WIDTH = 320
ROOT = Path(__file__).resolve().parent.parent


def measure_frame(path):
    """Colour and tone of one frame, or None if it could not be read."""
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    height = max(2, int(round(bgr.shape[0] * MEASURE_WIDTH / bgr.shape[1])))
    bgr = cv2.resize(bgr, (MEASURE_WIDTH, height), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    f = bgr.astype(np.float32)
    B, G, R = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    rg, yb = R - G, 0.5 * (R + G) - B
    colourfulness = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    saturation = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1].mean() / 255
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    return [float(lab[:, :, 1].mean() - 128), float(lab[:, :, 2].mean() - 128), float(saturation),
            float(colourfulness / 255), float(grey.mean()), float(grey.std()),
            float(np.percentile(grey, 5)), float(np.percentile(grey, 95)), float((grey < 0.15).mean())]


FIELDS = ["lab_a", "lab_b", "saturation", "colourfulness", "luma_mean", "luma_std", "luma_p5", "luma_p95", "dark_share"]


def measure_shot(job):
    idx, ref_paths, run_paths = job
    ref = [m for m in (measure_frame(p) for p in ref_paths) if m]
    run = [m for m in (measure_frame(p) for p in run_paths) if m]
    if not ref or not run:
        return None
    return idx, np.array(ref).mean(axis=0).tolist(), np.array(run).mean(axis=0).tolist(), len(ref), len(run)


def collect_shot_rows(slug, run_name, stride, only_shots, workers):
    ref_dir = ROOT / "training/reference" / slug / "frames"
    run_dir = ROOT / "training/runs" / slug / run_name / "frames"
    shots = json.load(open(ROOT / "training/reference" / slug / "shots.json"))["shots"]
    run_shots = json.load(open(ROOT / "training/runs" / slug / run_name / "shots.json"))

    jobs = []
    for shot in shots:
        if only_shots and shot["idx"] not in only_shots:
            continue
        frames = range(shot["start"], shot["end"] + 1, stride)
        ref_paths = [p for p in (ref_dir / f"f_{n + 1:05d}.jpg" for n in frames) if p.exists()]
        run_paths = [p for p in (run_dir / f"f_{n + 1:05d}.png" for n in frames) if p.exists()]
        if ref_paths and run_paths:
            jobs.append((shot["idx"], ref_paths, run_paths))

    with Pool(workers) as pool:
        results = [r for r in pool.map(measure_shot, jobs) if r]

    rows = []
    for idx, ref, run, n_ref, n_run in results:
        meta = run_shots.get(str(idx), {})
        row = {"shot": idx, "n_ref": n_ref, "n_run": n_run, "look": meta.get("look"),
               "character_proxy": meta.get("character_proxy"), "feature_error": meta.get("feature_error"),
               "params": meta.get("params", {})}
        for i, name in enumerate(FIELDS):
            row["ref_" + name] = round(ref[i], 4)
            row["run_" + name] = round(run[i], 4)
        rows.append(row)
    return rows


def report(rows):
    print(f"{len(rows)} shots\n")
    print(f"{'shot':>4} {'ref a':>7}{'run a':>7} {'ref b':>7}{'run b':>7}  {'sat':>12}  {'luma':>12}  {'p5':>12}  {'std':>12}")
    for row in sorted(rows, key=lambda r: r["shot"]):
        print(f"{row['shot']:>4} {row['ref_lab_a']:>7.1f}{row['run_lab_a']:>7.1f} {row['ref_lab_b']:>7.1f}{row['run_lab_b']:>7.1f}"
              f"  {row['ref_saturation']:.3f}->{row['run_saturation']:.3f}  {row['ref_luma_mean']:.3f}->{row['run_luma_mean']:.3f}"
              f"  {row['ref_luma_p5']:.3f}->{row['run_luma_p5']:.3f}  {row['ref_luma_std']:.3f}->{row['run_luma_std']:.3f}")

    def col(name):
        return np.array([r[name] for r in rows])

    ref_a, run_a, ref_b, run_b = col("ref_lab_a"), col("run_lab_a"), col("ref_lab_b"), col("run_lab_b")
    chroma_gain_a = (ref_a * run_a).sum() / max(1e-9, (ref_a * ref_a).sum())
    chroma_gain_b = (ref_b * run_b).sum() / max(1e-9, (ref_b * ref_b).sum())
    print(f"\nchroma gain through the origin: lab_a x{chroma_gain_a:.2f}, lab_b x{chroma_gain_b:.2f}"
          f"   (1.00 = the render carries the reference's colour)")
    for name in ["saturation", "colourfulness", "luma_mean", "luma_std", "luma_p5", "luma_p95", "dark_share"]:
        ref, run = col("ref_" + name), col("run_" + name)
        print(f"{name:>15}: ref {ref.mean():.3f}  run {run.mean():.3f}  diff {run.mean() - ref.mean():+.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("run")
    ap.add_argument("--stride", type=int, default=5, help="measure every Nth frame of each shot")
    ap.add_argument("--shots", help="comma-separated shot indices; default every shot with rendered frames")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--json", help="write the per-shot rows here")
    args = ap.parse_args()

    only = {int(s) for s in args.shots.split(",")} if args.shots else None
    rows = collect_shot_rows(args.slug, args.run, args.stride, only, args.workers)
    report(rows)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
