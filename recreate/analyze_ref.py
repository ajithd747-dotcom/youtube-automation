"""Analyse a reference 2D animation: shot cuts, drawing cadence (on 1s/2s/3s), palette, camera drift.

Usage: python recreate/analyze_ref.py <frames_dir> <out_json>
Frames are the PNGs dumped by ffmpeg (f_0001.png ...), already downscaled.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def load_gray(paths, w=160):
    out = []
    for p in paths:
        im = cv2.imread(str(p), cv2.IMREAD_COLOR)
        h = int(im.shape[0] * w / im.shape[1])
        out.append(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA))
    return out


def frame_diffs(small):
    """Mean abs diff and histogram distance between consecutive frames."""
    mad, hist = [], []
    for a, b in zip(small, small[1:]):
        mad.append(float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean()))
        ha = cv2.calcHist([a], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).flatten()
        hb = cv2.calcHist([b], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).flatten()
        ha /= ha.sum() + 1e-9
        hb /= hb.sum() + 1e-9
        hist.append(float(np.abs(ha - hb).sum()))
    return np.array(mad), np.array(hist)


def find_cuts(mad, hist, mad_th=18.0, hist_th=0.55):
    """A cut = big pixel change AND big colour-distribution change."""
    return [i + 1 for i in range(len(mad)) if mad[i] > mad_th and hist[i] > hist_th]


def cadence(mad, lo, hi, still_th=0.45):
    """Within [lo,hi), how many frames are near-duplicates of the previous one.

    Returns the run-lengths of held drawings, e.g. [2,2,2,3] => mostly on 2s.
    """
    runs, cur = [], 1
    for i in range(lo, min(hi - 1, len(mad))):
        if mad[i] < still_th:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    return runs


def palette(img, k=6):
    px = img.reshape(-1, 3).astype(np.float32)
    px = px[::7]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lbl, cen = cv2.kmeans(px, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lbl.flatten(), minlength=k)
    order = np.argsort(-counts)
    return [{"rgb": [int(cen[i][2]), int(cen[i][1]), int(cen[i][0])],
             "share": round(float(counts[i] / counts.sum()), 3)} for i in order]


def camera_drift(small, lo, hi):
    """Median translation between consecutive frames (px at analysis width)."""
    dx = dy = 0.0
    n = 0
    for i in range(lo, min(hi - 1, len(small) - 1)):
        a = cv2.cvtColor(small[i], cv2.COLOR_BGR2GRAY)
        b = cv2.cvtColor(small[i + 1], cv2.COLOR_BGR2GRAY)
        try:
            (sx, sy), _ = cv2.phaseCorrelate(a.astype(np.float64), b.astype(np.float64))
        except cv2.error:
            continue
        dx += sx
        dy += sy
        n += 1
    return [round(dx, 2), round(dy, 2), n]


def main(frames_dir, out_json):
    paths = sorted(Path(frames_dir).glob("f_*.png"))
    small = load_gray(paths)
    mad, hist = frame_diffs(small)
    cuts = find_cuts(mad, hist)
    bounds = [0] + cuts + [len(small)]
    # merge shots shorter than 4 frames into the previous one
    merged = [bounds[0]]
    for b in bounds[1:]:
        if b - merged[-1] < 4:
            merged[-1] = b if len(merged) == 1 else merged[-1]
            continue
        merged.append(b)
    if merged[-1] != len(small):
        merged[-1] = len(small)

    shots = []
    for i, (lo, hi) in enumerate(zip(merged, merged[1:])):
        mid = small[(lo + hi) // 2]
        runs = cadence(mad, lo, hi)
        held = [r for r in runs if r > 0]
        shots.append({
            "idx": i,
            "start": lo, "end": hi, "n": hi - lo,
            "t_start": round(lo / 30.0, 3), "dur": round((hi - lo) / 30.0, 3),
            "cadence_runs": held,
            "cadence_median": int(np.median(held)) if held else 1,
            "new_drawings": len(held),
            "palette": palette(mid),
            "drift": camera_drift(small, lo, hi),
            "mad_mean": round(float(mad[lo:max(lo + 1, hi - 1)].mean()), 2),
        })

    res = {"n_frames": len(small), "fps": 30, "cuts": cuts, "shots": shots}
    Path(out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"{len(small)} frames -> {len(shots)} shots")
    for s in shots:
        pal = " ".join("#%02x%02x%02x" % tuple(c["rgb"]) for c in s["palette"][:4])
        print(f"  shot{s['idx']:02d} f{s['start']:4d}-{s['end']:4d} ({s['dur']:5.2f}s) "
              f"draws={s['new_drawings']:3d} on{s['cadence_median']}s drift={s['drift'][0]:6.1f},{s['drift'][1]:6.1f}  {pal}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
