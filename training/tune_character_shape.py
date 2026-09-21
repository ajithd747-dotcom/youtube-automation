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
DEFAULT_SHAPE = {"hair_w": 1.15, "hair_h": 1.05, "hair_cy": 0.35, "head_w": 0.75, "head_h": 0.8, "head_cy": 0.6, "body_w": 2.0, "body_top": 0.95}


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


def run(slug, shot, rounds=8, n_probe=3):
    D = L3.find_reference(slug)
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = meta["content_rect_640"]
    script = json.loads((D / "shots" / f"shot_{shot:02d}.json").read_text(encoding="utf-8"))
    lo = script["frames"][0]
    spec = L3.build_scene_spec(script)
    if not spec["character"]:
        sys.exit("no character proxy for this shot (needs semantic characters + a detected face box)")
    rung4 = json.loads((HERE / "runs" / D.name / f"level4_shot{shot:02d}" / "report.json").read_text(encoding="utf-8"))
    params = {**rung4["params_tuned"], "shape": dict(DEFAULT_SHAPE)}
    work = HERE / "runs" / D.name / f"level5_shot{shot:02d}"
    probe = sorted({int(v) for v in np.linspace(0, spec["frames"] - 1, n_probe)})
    t0 = time.time()
    (best, best_hold), = probe_scores(D, spec, lo, rect, [params], probe, work / "probe")
    log = [{"round": 0, "frame_score": round(best, 4), "holdout": round(best_hold, 4), "shape": params["shape"]}]
    print(f"{D.name[:30]} shot {shot}: probe frames {probe}, start frame_score {best:.4f} holdout {best_hold:.4f}", flush=True)
    scale = 1.0
    for rnd in range(1, rounds + 1):
        cands, labels = [], []
        for k, st in SHAPE_STEPS.items():
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
    before = L3.render_and_score(D, spec, {**rung4["params_tuned"], "shape": dict(DEFAULT_SHAPE)}, lo, f"level5_shot{shot:02d}/before", rect)
    after = L3.render_and_score(D, spec, params, lo, f"level5_shot{shot:02d}/after", rect)
    report = {"slug": D.name, "shot": shot, "probe_frames": probe, "seconds_wall": round(time.time() - t0, 1),
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
    a = ap.parse_args()
    run(a.slug, a.shot, a.rounds, a.probe)


if __name__ == "__main__":
    main()
