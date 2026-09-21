"""Rung 5: learn a character proxy's silhouette from the frame-by-frame feedback signal (training/SPEC.md section 1).

    .venv/bin/python training/tune_character_shape.py <slug> <shot> [--rounds 8] [--probe 3]

Starts from the rung-4 run (training/runs/<slug>/level4_shotNN/report.json: its tuned lights stay fixed) and adjusts the
8 shape parameters of the character proxy (blender_level3.DEFAULT_SHAPE, units of the face box) by coordinate descent on the
mean frame_score of a few probe frames. grad_ssim_holdout is reported but never used to accept a step: if it falls while
frame_score rises, the shape is fitting the metric, not the picture.

Writes training/runs/<slug>/level5_shotNN/{before,after}/ (full-shot renders + scores.json) and report.json.
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
from score_recreation import build_mask, load_reference_frame, score_frame_pair  # noqa: E402

SHAPE_STEPS = {"hair_w": 0.15, "hair_h": 0.15, "hair_cy": 0.1, "head_w": 0.1, "head_h": 0.1, "head_cy": 0.08, "body_w": 0.3, "body_top": 0.15}
FEATURE_STEPS = {"eye_y": 0.06, "eye_dx": 0.05, "eye_w": 0.04, "eye_h": 0.05, "mouth_y": 0.05, "mouth_w": 0.04}
SILHOUETTE_STEPS = {"spike": 0.06, "side_len": 0.2, "bang_len": 0.12, "neck_w": 0.12, "shoulder_drop": 0.15}
DEFAULT_SHAPE = {"hair_w": 1.15, "hair_h": 1.05, "hair_cy": 0.35, "head_w": 0.75, "head_h": 0.8, "head_cy": 0.6, "body_w": 2.0, "body_top": 0.95,
                 "spike": 0.12, "side_len": 0.6, "bang_len": 0.35, "neck_w": 0.35, "shoulder_drop": 0.35,
                 "eye_y": 0.55, "eye_dx": 0.2, "eye_w": 0.16, "eye_h": 0.2, "mouth_y": 0.82, "mouth_w": 0.12}   # = blender_level3.DEFAULT_SHAPE


def probe_scores(D, spec, lo, rect, candidates, probe, work):
    paths = L3.render(spec, candidates, probe, rect[2] - rect[0], rect[3] - rect[1], work)
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    refs = {f: load_reference_frame(D, lo + f, rect) for f in probe}
    masks = {f: build_mask(*refs[f].shape[:2], bool(rows[lo + f]["text_on_screen"]["subtitle_present"])) for f in probe}
    out = []
    for c in range(len(candidates)):
        ms = []
        for f in probe:
            rec = cv2.imread(str(paths[(c, f)]))
            m, _ = score_frame_pair(refs[f], rec, masks[f])
            ms.append(m)
        out.append((float(np.mean([m["frame_score"] for m in ms])), float(np.mean([m["grad_ssim_holdout"] for m in ms]))))
    return out


def run(slug, shot, rounds=8, n_probe=3, style="ellipsoid", features=False, landmark_face=False):
    D = L3.find_reference(slug)
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = meta["content_rect_640"]
    script = json.loads((D / "shots" / f"shot_{shot:02d}.json").read_text(encoding="utf-8"))
    lo = script["frames"][0]
    spec = L3.build_scene_spec(script)
    spec["character_style"] = style
    spec["face_features"] = features
    if landmark_face:
        if not spec.get("landmarks"):
            sys.exit("no measured face landmarks for this shot (run training/measure_face_landmarks.py, then write_shot_scripts.py)")
        spec["face_from_landmarks"] = True
    steps = {**SHAPE_STEPS, **(SILHOUETTE_STEPS if style == "silhouette" else {})}
    if style == "outline":
        if not spec.get("outline"):
            sys.exit("no measured silhouette outline for this shot (run training/measure_character_outlines.py)")
        steps = {k: SHAPE_STEPS[k] for k in ("head_w", "head_h", "head_cy", "body_top")}   # the outline is measured; only head + hair/body split tune
    if not spec["character"]:
        sys.exit("no character proxy for this shot (needs semantic characters + a detected face box)")
    rung4 = json.loads((HERE / "runs" / D.name / f"level4_shot{shot:02d}" / "report.json").read_text(encoding="utf-8"))
    params = {**rung4["params_tuned"], "shape": dict(DEFAULT_SHAPE)}
    tag = f"level5_shot{shot:02d}" + ("" if style == "ellipsoid" else f"_{style}") + ("_features" if features else "") + ("_lmface" if landmark_face else "")
    if features:
        steps = {**steps, **FEATURE_STEPS}
    if landmark_face:                                          # the face is measured: only hair and body stay free
        steps = {k: v for k, v in steps.items() if not k.startswith(("head_", "eye_", "mouth_"))}
    work = HERE / "runs" / D.name / tag
    probe = sorted({int(v) for v in np.linspace(0, spec["frames"] - 1, n_probe)})
    t0 = time.time()
    (best, best_hold), = probe_scores(D, spec, lo, rect, [params], probe, work / "probe")
    log = [{"round": 0, "frame_score": round(best, 4), "holdout": round(best_hold, 4), "shape": params["shape"]}]
    print(f"{D.name[:30]} shot {shot}: probe frames {probe}, start frame_score {best:.4f} holdout {best_hold:.4f}", flush=True)
    scale = 1.0
    for rnd in range(1, rounds + 1):
        cands, labels = [], []
        for k, st in steps.items():
            for d in (+1, -1):
                sh = dict(params["shape"])
                sh[k] = max(0.05, sh[k] + d * st * scale)
                cands.append({**params, "shape": sh})
                labels.append(f"{k} {'+' if d > 0 else '-'}{st * scale:.3g}")
        res = probe_scores(D, spec, lo, rect, cands, probe, work / "probe")
        i = int(np.argmax([r[0] for r in res]))
        if res[i][0] > best + 1e-4:
            params, (best, best_hold), moved = cands[i], res[i], labels[i]
        else:
            scale *= 0.5
            moved = f"no improvement -> step x{scale:g}"
        log.append({"round": rnd, "frame_score": round(best, 4), "holdout": round(best_hold, 4), "moved": moved, "shape": params["shape"]})
        print(f"  round {rnd}: frame_score {best:.4f} holdout {best_hold:.4f} ({moved})", flush=True)
        if scale < 0.2:
            break
    before = L3.render_and_score(D, spec, {**rung4["params_tuned"], "shape": dict(DEFAULT_SHAPE)}, lo, f"{tag}/before", rect)
    after = L3.render_and_score(D, spec, params, lo, f"{tag}/after", rect)
    report = {"slug": D.name, "shot": shot, "style": style, "face_features": features, "landmark_face": landmark_face, "probe_frames": probe, "seconds_wall": round(time.time() - t0, 1),
              "objective": "mean frame_score on probe frames (holdout never used to accept a step)",
              "before": before, "after": after, "shape_before": DEFAULT_SHAPE, "shape_after": params["shape"], "log": log}
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
    ap.add_argument("--features", action="store_true", help="add parametric anime eyes and mouth (style defaults for colour)")
    ap.add_argument("--landmark-face", action="store_true", help="face shape, eyes, brows, mouth placed on the measured landmarks")
    ap.add_argument("--style", default="ellipsoid", choices=["ellipsoid", "silhouette", "outline"])
    a = ap.parse_args()
    run(a.slug, a.shot, a.rounds, a.probe, a.style, a.features, a.landmark_face)


if __name__ == "__main__":
    main()
