"""What do known-bad recreations score? A number means nothing until this says what the range is.

    .venv/bin/python training/calibrate_scores.py <slug> [--n 120]

Scores degradations of REAL reference frames with the same function the training loop uses, and writes the table to
training/reference/<slug>/calibration.json. A real recreation has to climb through this table; the rungs are:

    identical (must be 1.0)  >  jpeg  >  mild blur  >  posterised  >  heavy blur  >  shifted  >  flat shot colour  >  another video
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_recreation as SR  # noqa: E402

REF = SR.REF


def degrade(kind, im, ctx):
    if kind == "identical":
        return im
    if kind == "jpeg_q15":
        return cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 15])[1], 1)
    if kind == "blur_sigma2":
        return cv2.GaussianBlur(im, (0, 0), 2)
    if kind == "posterise_8_levels":
        return (im // 32) * 32 + 16
    if kind == "blur_sigma10":
        return cv2.GaussianBlur(im, (0, 0), 10)
    if kind == "blur_sigma25":
        return cv2.GaussianBlur(im, (0, 0), 25)
    if kind == "brightness_plus_25pct":
        return np.clip(im.astype(np.float32) * 1.25, 0, 255).astype(np.uint8)
    if kind == "mirrored":
        return im[:, ::-1]
    if kind == "shifted_3_frames":
        return ctx["shifted"]
    if kind == "flat_shot_mean_colour":
        return np.full_like(im, ctx["shot_mean"])
    if kind == "flat_frame_mean_colour":
        return np.full_like(im, im.reshape(-1, 3).mean(axis=0).astype(np.uint8))
    if kind == "another_video_same_index":
        return ctx["other"]
    raise KeyError(kind)


KINDS = ["identical", "jpeg_q15", "blur_sigma2", "posterise_8_levels", "brightness_plus_25pct", "blur_sigma10", "blur_sigma25", "mirrored",
         "shifted_3_frames", "flat_frame_mean_colour", "flat_shot_mean_colour", "another_video_same_index"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--n", type=int, default=120)
    a = ap.parse_args()
    hits = [p for p in REF.iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    others = [p for p in REF.iterdir() if p.is_dir() and p != D and (p / "frames").exists()]
    if not others:
        sys.exit("need at least one other ingested video for the 'another video' rung")
    O = others[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = tuple(meta["content_rect_640"])
    orect = tuple(json.loads((O / "meta.json").read_text(encoding="utf-8"))["content_rect_640"])
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    n_frames = len(rows)
    sub = [bool(r["text_on_screen"]["subtitle_present"]) for r in rows]
    onframes = len(list((O / "frames").glob("f_*.jpg")))

    shot_mean = {}
    for r in rows:
        shot_mean.setdefault(r["shot"], []).append(r["lighting"]["luma_mean"])
    idx = np.linspace(3, n_frames - 4, a.n).astype(int)
    results = {k: [] for k in KINDS}
    for i in idx:
        ref = SR.load_reference_frame(D, int(i), rect)
        mask = SR.build_mask(ref.shape[0], ref.shape[1], sub[i])
        sh = rows[i]["shot"]
        members = [j for j in range(n_frames) if rows[j]["shot"] == sh][:: max(1, len([j for j in range(n_frames) if rows[j]["shot"] == sh]) // 6)][:6]
        shot_col = np.mean([SR.load_reference_frame(D, j, rect).reshape(-1, 3).mean(axis=0) for j in members], axis=0).astype(np.uint8)
        other = cv2.resize(SR.crop_to_content(cv2.imread(str(O / "frames" / f"f_{(int(i) % onframes) + 1:05d}.jpg")), orect), (ref.shape[1], ref.shape[0]))
        ctx = {"shifted": SR.load_reference_frame(D, int(i) + 3, rect), "shot_mean": shot_col, "other": other}
        for kind in KINDS:
            sc, _ = SR.score_frame_pair(ref, degrade(kind, ref, ctx), mask)
            results[kind].append(sc)

    table = {}
    print(f"{D.name}: {len(idx)} sample frames, other video for the unrelated rung: {O.name}\n")
    print(f"{'degradation':28s} {'frame_score':>11s} {'ssim':>7s} {'hist':>7s} {'edge_f1':>8s} {'dhue':>7s}")
    for kind in KINDS:
        v = results[kind]
        table[kind] = {k: round(float(np.mean([x[k] for x in v])), 4) for k in ("frame_score", "ssim", "hist", "edge_f1", "dhue")}
        t = table[kind]
        print(f"{kind:28s} {t['frame_score']:11.4f} {t['ssim']:7.3f} {t['hist']:7.3f} {t['edge_f1']:8.3f} {t['dhue']:7.2f}")
    (D / "calibration.json").write_text(json.dumps({"n_frames": int(len(idx)), "weights": SR.WEIGHTS, "table": table}, indent=1), encoding="utf-8")
    problems = []
    if table["identical"]["frame_score"] < 0.999:
        problems.append("identical input does not score 1.0")
    order = ["identical", "jpeg_q15", "blur_sigma2", "blur_sigma10", "blur_sigma25", "flat_frame_mean_colour"]
    for hi, lo in zip(order, order[1:]):
        if table[hi]["frame_score"] < table[lo]["frame_score"]:
            problems.append(f"{hi} scores below {lo}")
    if table["another_video_same_index"]["frame_score"] > table["blur_sigma10"]["frame_score"]:
        problems.append("an unrelated video scores above a heavy blur of the right frame")
    print("\nORDERING PROBLEMS: " + "; ".join(problems) if problems else "\nordering sensible; identical = 1.0")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
