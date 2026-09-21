"""Rung 3 of the recreation ladder: build the shot from its SCRIPT alone as a parametric Blender scene, then tune the scene's
lights, exposure and compositor until the render's measured features match the script's measured targets.

    .venv/bin/python training/recreate_level3.py <slug> <shot> [--rounds 10] [--tag NAME] [--no-character]

No reference pixels are read here or in Blender: the only input is training/reference/<slug>/shots/shot_NN.json. The tuning
loop measures its own renders with the same functions that measured the reference (training/describe_frames.py) and compares
them with the numbers in the script -- that is the feature error it minimises. frame_score and grad_ssim_holdout
(training/score_recreation.py) are computed afterwards against the reference frames and are never tuned against.

Writes training/runs/<slug>/<tag>/{untuned,tuned}/ (rendered frames + scores.json) and report.json.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "blender_agent"))
sys.path.insert(0, str(HERE))
from blender_runner import find_blender  # noqa: E402
from describe_frames import measure_colour, measure_lighting, prepare_frame  # noqa: E402

NM = "NOT MEASURED"
TUNE_W, TUNE_H = 320, 180
# feature -> (script path, error scale). Error = |render - target| / scale, averaged over the features that were measured.
FEATURES = {
    "luma_std": ("lighting.contrast_luma_std", 0.04),
    "luma_p5": ("lighting.ambient_luma_p5", 0.04),
    "luma_p95": ("lighting.highlight_luma_p95", 0.04),
    "top_minus_bottom": ("lighting.top_minus_bottom", 0.04),
    "left_minus_right": ("lighting.left_minus_right", 0.04),
    "vignette_corner_over_centre": ("lighting.vignette_corner_over_centre", 0.08),
    "bloom": ("lighting.bloom", 0.04),
    "lab_a": ("lighting.lab_a", 3.0),
    "lab_b": ("lighting.lab_b", 3.0),
}
# parameter -> (kind, step, lo, hi). "mul" steps multiply, "add" steps add.
PARAMS = {
    "key_energy": ("mul", 1.6, 0.05, 50.0),
    "fill_strength": ("mul", 1.6, 0.01, 10.0),
    "key_screen_angle_deg": ("add", 40.0, -720.0, 720.0),
    "key_elevation_deg": ("add", 20.0, 5.0, 85.0),
    "exposure": ("add", 0.6, -6.0, 6.0),
    "bloom_strength": ("add", 0.3, 0.0, 2.0),
    "vignette": ("add", 0.15, 0.0, 0.9),
}


def dig(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d if isinstance(d, (int, float)) else None


def find_reference(fragment):
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and fragment in p.name]
    if len(hits) != 1:
        sys.exit(f"'{fragment}' matches {[h.name for h in hits]}")
    return hits[0]


def build_scene_spec(script):
    """Everything Blender gets, taken from the shot script. Refuses a script without the measured colour regions."""
    reg = script["colour"].get("regions")
    if not isinstance(reg, dict):
        sys.exit("shot script has no colour.regions -- rebuild it with training/write_shot_scripts.py")
    li, cam = script["lighting"], script["camera"]
    n = script["frames"][1] - script["frames"][0]
    keys = cam["path_keyframes"] if isinstance(cam.get("path_keyframes"), list) else [{"frame": 0, "dx": 0.0, "dy": 0.0, "zoom": 0.0, "roll_deg": 0.0}]
    keys = [{k: (v if v is not None else 0.0) for k, v in key.items()} for key in keys]
    exp = li["exposure_luma"]["keyframes"] if isinstance(li["exposure_luma"], dict) else []
    exp = [e for e in exp if isinstance(e.get("luma"), (int, float))]
    return {
        "frames": n,
        "regions": reg,
        "subject_bbox_xywh": reg["subject_bbox_xywh"] if isinstance(reg["subject_bbox_xywh"], list) else None,
        "subject_rgb": reg["subject_rgb"] if isinstance(reg["subject_rgb"], list) else None,
        "world_rgb": reg["middle_third_rgb"],
        # rung 4: the vision pass says who is on screen; only then does the face box become a character (colours measured)
        "character": reg.get("character") if isinstance(reg.get("character"), dict) and isinstance(script.get("semantic", {}).get("characters"), list)
                     and script["semantic"]["characters"] else None,
        # measured silhouette (middle keyframe) when the segmentation found a character
        "outline": next((k["polygon"] for k in sorted(script["characters"].get("silhouette_outline", {}).get("keyframes", []), key=lambda k: abs(k["frame"] - n // 2))
                         if isinstance(k["polygon"], list)), None),
        # measured line art (ink colour, stroke width, edge density inside the outline): drives the stroke layer when enabled
        "line_art": script["characters"].get("line_art") if isinstance(script["characters"].get("line_art"), dict) else None,
        # measured facial landmarks per keyframe (28 points, frame fractions, + face tones): place and animate the face when
        # face_from_landmarks; "landmarks" = the keyframe nearest the middle, for the static uses
        "landmark_keys": sorted(({"frame": k["frame"], "points": k["points"], "tones": k.get("tones"), "hair_tones": k.get("hair_tones")} for k in script["characters"]["face_landmarks"]["keyframes"]),
                                key=lambda k: k["frame"]) if isinstance(script["characters"].get("face_landmarks"), dict) else None,
        "landmarks": next((k["points"] for k in sorted(script["characters"]["face_landmarks"]["keyframes"], key=lambda k: abs(k["frame"] - n // 2))),
                          None) if isinstance(script["characters"].get("face_landmarks"), dict) else None,
        "camera_keys": keys,
        "exposure_keys": [{"frame": int(e["frame"]), "luma": float(e["luma"])} for e in exp] or [{"frame": 0, "luma": float(li["exposure_luma"]["median"])}],
        "targets": {name: dig(script, path) for name, (path, _) in FEATURES.items()},
        "provenance": f"training/reference/{script['slug']}/shots/shot_{script['shot']:02d}.json",
    }


def initial_params(script):
    li = script["lighting"]
    ang = li["key_direction_screen_deg"]["angle"]
    vig = li["vignette_corner_over_centre"]
    return {"key_energy": 1.0, "fill_strength": 0.5,
            "key_screen_angle_deg": float(ang) if ang is not None else 270.0,
            "key_elevation_deg": 30.0,
            "exposure": 0.0, "bloom_strength": 0.0,
            "vignette": float(np.clip(1.0 - vig, 0.0, 0.9)) if isinstance(vig, (int, float)) else 0.0,
            "exposure_offsets": {}}


def render(spec, candidates, frames, width, height, out_dir, samples=16):
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    job = out_dir / "job.json"
    job.write_text(json.dumps({"spec": spec, "candidates": candidates, "frames": frames, "width": width, "height": height,
                               "samples": samples, "out_dir": str(out_dir)}), encoding="utf-8")
    r = subprocess.run([find_blender(), "-b", "--python", str(HERE / "blender_level3.py"), "--", str(job)], capture_output=True, text=True)
    if "LEVEL3_DONE" not in r.stdout:
        sys.exit("Blender did not finish:\n" + (r.stdout + r.stderr)[-2000:])
    return {(c, f): out_dir / f"c{c:02d}_f{f:05d}.png" for c in range(len(candidates)) for f in frames}


def measure_render(path):
    bgr = cv2.imread(str(path))
    im, gray = prepare_frame(bgr, (0, 0, bgr.shape[1], bgr.shape[0]))
    light, _ = measure_lighting(im, gray, None)
    return light, measure_colour(im)


def feature_error(spec, measured_by_frame):
    """measured_by_frame: {frame: lighting dict}. Returns (error, per-feature errors)."""
    per = {}
    tgt = spec["targets"]
    lights = list(measured_by_frame.values())
    for name, (_, scale) in FEATURES.items():
        if tgt[name] is None:
            continue
        vals = [l[name] for l in lights if l[name] is not None]
        if vals:
            per[name] = abs(float(np.median(vals)) - tgt[name]) / scale      # script targets are shot medians
    exp = {k["frame"]: k["luma"] for k in spec["exposure_keys"]}
    ex = [abs(measured_by_frame[f]["luma_mean"] - exp[f]) / 0.03 for f in measured_by_frame if f in exp]
    if ex:
        per["exposure_curve"] = float(np.mean(ex)) * 2.0          # the exposure curve counts double: it is the shot's main lighting fact
    return float(np.mean(list(per.values()))), per


def step(params, name, direction):
    kind, s, lo, hi = PARAMS[name]
    p = dict(params)
    p[name] = float(np.clip(p[name] * s ** direction if kind == "mul" else p[name] + s * direction, lo, hi))
    return p


def evaluate(spec, candidates, frames, work):
    paths = render(spec, candidates, frames, TUNE_W, TUNE_H, work)
    out = []
    for c in range(len(candidates)):
        lights = {f: measure_render(paths[(c, f)])[0] for f in frames}
        out.append((feature_error(spec, lights), lights))
    return out


def solve_exposure_offsets(spec, params, lights):
    """Per-keyframe exposure correction: display luma ~ linear^(1/2.2), so a luma ratio r is about 2.2*log2(r) stops. Damped."""
    offs = dict(params.get("exposure_offsets") or {})
    for k in spec["exposure_keys"]:
        f = k["frame"]
        if f in lights and lights[f]["luma_mean"] > 1e-3 and k["luma"] > 1e-3:
            offs[str(f)] = float(np.clip(offs.get(str(f), 0.0) + 0.7 * 2.2 * math.log2(k["luma"] / lights[f]["luma_mean"]), -4, 4))
    mean_off = float(np.mean(list(offs.values()))) if offs else 0.0      # keep the offsets zero-mean; the base exposure carries the level
    return {**params, "exposure": float(np.clip(params["exposure"] + mean_off, -6, 6)), "exposure_offsets": {k: v - mean_off for k, v in offs.items()}}


def tune(spec, params, rounds, work, log):
    keys = [k["frame"] for k in spec["exposure_keys"]]
    probe = sorted({keys[0], keys[len(keys) // 2], keys[-1]})
    (best_err, best_per), best_lights = evaluate(spec, [params], probe, work / "probe")[0]
    log.append({"round": 0, "error": round(best_err, 4), "per": {k: round(v, 3) for k, v in best_per.items()}, "params": params})
    scale = 1.0
    for rnd in range(1, rounds + 1):
        cands = []
        for name in PARAMS:
            for d in (+scale, -scale):
                cands.append(step(params, name, d))
        cands.append(solve_exposure_offsets(spec, params, best_lights))
        results = evaluate(spec, cands, probe, work / "probe")
        i = int(np.argmin([r[0][0] for r in results]))
        (err, per), lights = results[i]
        if err < best_err - 1e-4:
            params, best_err, best_per, best_lights = cands[i], err, per, lights
            moved = "exposure_offsets" if i == len(cands) - 1 else f"{list(PARAMS)[i // 2]} {'+' if i % 2 == 0 else '-'}{scale:g}"
        else:
            scale *= 0.5
            moved = f"no improvement -> step x{scale:g}"
        log.append({"round": rnd, "error": round(best_err, 4), "moved": moved, "per": {k: round(v, 3) for k, v in best_per.items()}, "params": params})
        print(f"  round {rnd}: feature error {best_err:.3f} ({moved})", flush=True)
        if scale < 0.1:
            break
    # final: all exposure keyframes, two correction passes
    for _ in range(2):
        (err, per), lights = evaluate(spec, [params], keys, work / "probe")[0]
        cand = solve_exposure_offsets(spec, params, lights)
        (err2, per2), _ = evaluate(spec, [cand], keys, work / "probe")[0]
        if err2 < err:
            params = cand
        log.append({"round": "exposure_pass", "error": round(min(err, err2), 4), "per": {k: round(v, 3) for k, v in (per2 if err2 < err else per).items()}})
    return params


def render_and_score(D, spec, params, lo, run_name, rect):
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    run_dir = HERE / "runs" / D.name / run_name
    frames = list(range(spec["frames"]))
    paths = render(spec, [params], frames, W, H, run_dir / "blender")
    rendered = run_dir / "rendered"
    if rendered.exists():
        shutil.rmtree(rendered)
    rendered.mkdir(parents=True)
    for f in frames:
        shutil.move(str(paths[(0, f)]), rendered / f"f_{f + 1:05d}.png")
    subprocess.run([sys.executable, str(HERE / "score_recreation.py"), D.name, str(rendered), "--start", str(lo), "--run", run_name], capture_output=True, text=True)
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))["overall"]
    lights = {f: measure_render(rendered / f"f_{f + 1:05d}.png")[0] for f in frames}
    err, per = feature_error(spec, {f: lights[f] for f in frames})
    exp_keys = {k["frame"]: k["luma"] for k in spec["exposure_keys"]}
    tgt_curve = np.interp(frames, sorted(exp_keys), [exp_keys[k] for k in sorted(exp_keys)])
    got_curve = np.array([lights[f]["luma_mean"] for f in frames])
    return {"frame_score": scores["frame_score"], "ssim": scores["ssim"], "hist": scores["hist"], "edge_f1": scores["edge_f1"],
            "grad_ssim_holdout": scores["grad_ssim_holdout"], "lpips_holdout": scores.get("lpips_holdout"), "dhue": scores["dhue"],
            "feature_error": round(err, 4), "feature_errors": {k: round(v, 3) for k, v in per.items()},
            "exposure_curve_mae": round(float(np.abs(got_curve - tgt_curve).mean()), 4)}


def run(slug, shot, rounds=10, tag=None, character=True):
    D = find_reference(slug)
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    script = json.loads((D / "shots" / f"shot_{shot:02d}.json").read_text(encoding="utf-8"))
    lo = script["frames"][0]
    spec = build_scene_spec(script)
    if not character:
        spec["character"] = None
    name = tag or f"level3_shot{shot:02d}"
    work = HERE / "runs" / D.name / name
    work.mkdir(parents=True, exist_ok=True)
    (work / "spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    t0 = time.time()
    p0 = initial_params(script)
    print(f"{D.name[:30]} shot {shot} ({spec['frames']}f): tuning {len(PARAMS)} parameters against {sum(v is not None for v in spec['targets'].values())} script features + exposure curve", flush=True)
    log = []
    p1 = tune(spec, p0, rounds, work, log)
    untuned = render_and_score(D, spec, p0, lo, f"{name}/untuned", meta["content_rect_640"])
    tuned = render_and_score(D, spec, p1, lo, f"{name}/tuned", meta["content_rect_640"])
    report = {"slug": D.name, "shot": shot, "frames": spec["frames"], "seconds_wall": round(time.time() - t0, 1),
              "inputs": spec["provenance"] + " only (no reference pixels)", "character_proxy": spec["character"] is not None, "untuned": untuned, "tuned": tuned,
              "params_untuned": p0, "params_tuned": p1, "tuning_log": log}
    (work / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for k, v in (("untuned", untuned), ("tuned", tuned)):
        print(f"  {k:8s} frame_score={v['frame_score']:.4f} ssim={v['ssim']:.3f} hist={v['hist']:.3f} edge_f1={v['edge_f1']:.3f} "
              f"holdout={v['grad_ssim_holdout']:.3f} feature_error={v['feature_error']:.3f} exposure_mae={v['exposure_curve_mae']:.4f}", flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("shot", type=int)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--no-character", action="store_true", help="rung-3 ablation: ignore the semantic character proxy")
    a = ap.parse_args()
    run(a.slug, a.shot, a.rounds, a.tag, not a.no_character)


if __name__ == "__main__":
    main()
