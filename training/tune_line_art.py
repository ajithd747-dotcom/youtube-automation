"""Rung 6: parametric line art on the character proxy, tuned to the script's measured line art (characters.line_art).

    .venv/bin/python training/tune_line_art.py <slug> <shot> [--rounds 8] [--probe 3] [--features]

Starts from the rung-5 run (lights from level4_shotNN, proxy shape from level5_shotNN) and turns on the stroke layer
(blender_level3.stroke_paths: bangs strands over a hair fringe, crown strands, side locks, neck and collar; ink colour and
stroke width straight from the script). Its 6 count/length parameters are tuned by coordinate descent so the render's line
art measures like the script says -- edge density inside the outline and the vertical share of hair strokes, measured on the
render by the same function that measured the reference (measure_line_art.measure_line_art_of_frame).

frame_score and grad_ssim_holdout are computed afterwards and never used to accept a step. Before = the same scene with
the stroke layer off, so the delta is the line art alone.
Objective "grid" (default) matches the 8x8 edge_density_grid over the outline's bounding box; "density" the single number.
Writes training/runs/<slug>/level6_shotNN_lines[_features][_grid]/{before,after}/ and report.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recreate_level3 as L3  # noqa: E402
from measure_line_art import measure_line_art_of_frame  # noqa: E402

LINE_STEPS = {"n_bangs": 2, "bang_len": 0.1, "n_crown": 2, "n_locks": 1, "lock_len": 0.2, "collar": 1}
LINE_START = {"n_bangs": 7, "bang_len": 0.45, "n_crown": 4, "n_locks": 2, "lock_len": 0.9, "collar": 1}   # = blender_level3.LINE_STROKES
LINE_LIMITS = {"n_bangs": (0, 20), "bang_len": (0.1, 0.9), "n_crown": (0, 12), "n_locks": (0, 5), "lock_len": (0.2, 2.0), "collar": (0, 1)}


def grid_error(target_grid, measured):
    """Mean absolute per-cell edge-density difference over the cells the script measured, relative to the mean target density:
    WHERE the ink goes, not just how much."""
    cells = [c for c, t in enumerate(target_grid) if isinstance(t, (int, float))]
    got = np.array([[m["edge_density_grid"][c] if isinstance(m["edge_density_grid"][c], float) else 0.0 for c in cells] for m in measured])
    tgt = np.array([target_grid[c] for c in cells])
    return float(np.abs(np.median(got, axis=0) - tgt).mean() / max(tgt.mean(), 1e-4))


def line_art_error(target, measured):
    """Per-cell density error when the script has the grid (edge_density_grid), else the relative error of the overall density
    inside the outline; plus the vertical-stroke share difference (half weight)."""
    d = [m["edge_density_inside"] for m in measured if isinstance(m["edge_density_inside"], float)]
    v = [m["vertical_stroke_share"] for m in measured if isinstance(m["vertical_stroke_share"], float)]
    if isinstance(target.get("edge_density_grid"), list):
        err = grid_error(target["edge_density_grid"], measured)
    else:
        err = abs(float(np.median(d)) - target["edge_density_inside"]) / target["edge_density_inside"] if d else 1.0
    if v and isinstance(target.get("vertical_stroke_share"), (int, float)):
        err += 0.5 * abs(float(np.median(v)) - target["vertical_stroke_share"])
    return err, (float(np.median(d)) if d else None), (float(np.median(v)) if v else None)


def probe_errors(spec, target, outline, candidates, probe, work, width, height):
    paths = L3.render(spec, candidates, probe, width, height, work)
    keep = np.ones((height, width), bool)                  # a render has no subtitles or logos to mask
    out = []
    for c in range(len(candidates)):
        out.append(line_art_error(target, [measure_line_art_of_frame(cv2.imread(str(paths[(c, f)])), outline, keep) for f in probe]))
    return out


def run(slug, shot, rounds=8, n_probe=3, features=False, objective="grid"):
    D = L3.find_reference(slug)
    rect = json.loads((D / "meta.json").read_text(encoding="utf-8"))["content_rect_640"]
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    script = json.loads((D / "shots" / f"shot_{shot:02d}.json").read_text(encoding="utf-8"))
    lo = script["frames"][0]
    spec = L3.build_scene_spec(script)
    target = spec.get("line_art")
    if not spec["character"] or not target or not isinstance(target.get("edge_density_inside"), (int, float)) or not spec.get("outline"):
        sys.exit("needs a character proxy, a measured outline and characters.line_art (training/measure_line_art.py, then write_shot_scripts.py)")
    if objective == "density":
        target = {k: v for k, v in target.items() if k != "edge_density_grid"}
    spec["face_features"] = features
    runs = HERE / "runs" / D.name
    params = {**json.loads((runs / f"level4_shot{shot:02d}" / "report.json").read_text(encoding="utf-8"))["params_tuned"],
              "shape": json.loads((runs / (f"level5_shot{shot:02d}" + ("_features" if features else "")) / "report.json").read_text(encoding="utf-8"))["shape_after"],
              "lines": dict(LINE_START)}
    tag = f"level6_shot{shot:02d}_lines" + ("_features" if features else "") + ("_grid" if objective == "grid" else "")
    work = runs / tag
    probe = sorted({int(v) for v in np.linspace(0, spec["frames"] - 1, n_probe)})
    lined = {**spec, "line_strokes": True}
    t0 = time.time()
    (best, dens, vert), = probe_errors(lined, target, spec["outline"], [params], probe, work / "probe", W, H)
    log = [{"round": 0, "error": round(best, 4), "density": dens, "vertical": vert, "lines": params["lines"]}]
    print(f"{D.name[:30]} shot {shot}: target density {target['edge_density_inside']} vertical {target['vertical_stroke_share']}; "
          f"start error {best:.3f} (density {dens:.4f}, vertical {vert})", flush=True)
    scale = 1.0
    for rnd in range(1, rounds + 1):
        cands, labels = [], []
        for k, st in LINE_STEPS.items():
            for d in (+1, -1):
                ln = dict(params["lines"])
                lo_k, hi_k = LINE_LIMITS[k]
                step_k = max(round(st * scale), 1) if isinstance(LINE_START[k], int) else st * scale
                ln[k] = min(max(ln[k] + d * step_k, lo_k), hi_k)
                if ln[k] != params["lines"][k]:
                    cands.append({**params, "lines": ln})
                    labels.append(f"{k} {'+' if d > 0 else '-'}{step_k:g}")
        res = probe_errors(lined, target, spec["outline"], cands, probe, work / "probe", W, H)
        i = int(np.argmin([r[0] for r in res]))
        if res[i][0] < best - 1e-4:
            params, (best, dens, vert), moved = cands[i], res[i], labels[i]
        else:
            scale *= 0.5
            moved = f"no improvement -> step x{scale:g}"
        log.append({"round": rnd, "error": round(best, 4), "density": dens, "vertical": vert, "moved": moved, "lines": params["lines"]})
        print(f"  round {rnd}: error {best:.3f} density {dens:.4f} vertical {vert} ({moved})", flush=True)
        if scale < 0.2:
            break
    before = L3.render_and_score(D, spec, params, lo, f"{tag}/before", rect)
    after = L3.render_and_score(D, lined, params, lo, f"{tag}/after", rect)
    report = {"slug": D.name, "shot": shot, "face_features": features, "probe_frames": probe, "seconds_wall": round(time.time() - t0, 1),
              "objective": f"match characters.line_art ({objective}: {'per-cell edge density grid' if objective == 'grid' else 'edge density inside the outline'}, vertical stroke share); frame_score and holdout never used to accept a step",
              "target": {k: target[k] for k in ("edge_density_inside", "vertical_stroke_share", "ink_rgb", "stroke_width_frac")},
              "before": before, "after": after, "lines_start": LINE_START, "lines_after": params["lines"], "log": log}
    (work / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for k, v in (("before", before), ("after", after)):
        print(f"  {k:6s} full shot: frame_score={v['frame_score']:.4f} ssim={v['ssim']:.3f} hist={v['hist']:.3f} edge_f1={v['edge_f1']:.3f} "
              f"holdout={v['grad_ssim_holdout']:.3f}", flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("shot", type=int)
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--probe", type=int, default=3)
    ap.add_argument("--objective", default="grid", choices=["grid", "density"], help="grid = per-cell density (where the ink is); density = one number")
    ap.add_argument("--features", action="store_true", help="also draw the parametric eyes and mouth (tune_character_shape.py --features)")
    a = ap.parse_args()
    run(a.slug, a.shot, a.rounds, a.probe, a.features, a.objective)


if __name__ == "__main__":
    main()
