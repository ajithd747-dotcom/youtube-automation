"""Rung 7: hair as measured masses -- the character's measured outline above the chin, in the measured hair tones, split into
locks from a crown point (blender_level3.place_hair_masses, training/face_geometry.hair_locks) -- on top of the landmark face.

    .venv/bin/python training/tune_hair_masses.py <slug> <shot> [--locks 4,6,8,10,12,14,16] [--probe 3]

The one free parameter, the number of locks, is chosen by the script's measured line art: for each candidate the render is
measured with measure_line_art (same function as the reference) and the lock count whose 8x8 edge-density grid is closest
to characters.line_art.edge_density_grid wins. frame_score and grad_ssim_holdout are computed afterwards and never used to
choose. Before = the same scene (landmark face, default proxy shape, lights from level4_shotNN) with the hair ellipsoid.
Writes training/runs/<slug>/level7_shotNN_hair/{before,after}/ and report.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recreate_level3 as L3  # noqa: E402
from tune_character_shape import DEFAULT_SHAPE  # noqa: E402
from tune_line_art import probe_errors  # noqa: E402


def run(slug, shot, locks=(4, 6, 8, 10, 12, 14, 16), n_probe=3):
    D = L3.find_reference(slug)
    rect = json.loads((D / "meta.json").read_text(encoding="utf-8"))["content_rect_640"]
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    script = json.loads((D / "shots" / f"shot_{shot:02d}.json").read_text(encoding="utf-8"))
    lo = script["frames"][0]
    spec = {**L3.build_scene_spec(script), "face_from_landmarks": True}
    target = spec.get("line_art")
    if not (spec["character"] and spec.get("outline") and spec.get("landmark_keys") and target and isinstance(target.get("edge_density_grid"), list)):
        sys.exit("needs a character proxy, a measured outline, face landmarks with hair_tones, and characters.line_art")
    if not any(isinstance((k.get("hair_tones") or {}).get("dark_share"), (int, float)) for k in spec["landmark_keys"]):
        sys.exit("no measured hair_tones (re-run training/measure_face_landmarks.py, then write_shot_scripts.py)")
    params = {**json.loads((HERE / "runs" / D.name / f"level4_shot{shot:02d}" / "report.json").read_text(encoding="utf-8"))["params_tuned"],
              "shape": dict(DEFAULT_SHAPE)}
    hair = {**spec, "hair_masses": True}
    tag = f"level7_shot{shot:02d}_hair"
    work = HERE / "runs" / D.name / tag
    probe = sorted({int(v) for v in np.linspace(0, spec["frames"] - 1, n_probe)})
    t0 = time.time()
    cands = [{**params, "hair_locks": n} for n in locks]
    res = probe_errors(hair, target, spec["outline"], cands, probe, work / "probe", W, H)
    for n, (err, dens, vert) in zip(locks, res):
        print(f"  locks {n:2d}: line-art error {err:.3f} (density {dens:.4f}, vertical {vert})", flush=True)
    i = int(np.argmin([r[0] for r in res]))
    chosen = cands[i]
    print(f"{D.name[:30]} shot {shot}: chose {locks[i]} locks (target density {target['edge_density_inside']})", flush=True)
    before = L3.render_and_score(D, spec, params, lo, f"{tag}/before", rect)
    after = L3.render_and_score(D, hair, chosen, lo, f"{tag}/after", rect)
    report = {"slug": D.name, "shot": shot, "probe_frames": probe, "seconds_wall": round(time.time() - t0, 1),
              "objective": "lock count closest to characters.line_art edge_density_grid; frame_score and holdout never used to choose",
              "candidates": [{"locks": n, "line_art_error": round(r[0], 4), "density": r[1], "vertical": r[2]} for n, r in zip(locks, res)],
              "chosen_locks": locks[i], "before": before, "after": after}
    (work / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for k, v in (("before", before), ("after", after)):
        print(f"  {k:6s} full shot: frame_score={v['frame_score']:.4f} ssim={v['ssim']:.3f} hist={v['hist']:.3f} edge_f1={v['edge_f1']:.3f} "
              f"holdout={v['grad_ssim_holdout']:.3f}", flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("shot", type=int)
    ap.add_argument("--locks", default="4,6,8,10,12,14,16")
    ap.add_argument("--probe", type=int, default=3)
    a = ap.parse_args()
    run(a.slug, a.shot, tuple(int(x) for x in a.locks.split(",")), a.probe)


if __name__ == "__main__":
    main()
