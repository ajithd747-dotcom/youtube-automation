"""Read a reference animation and write the shot script the Blender build renders from.

The script is the contract between "what the reference does" and "what we build":
per shot it records timing, drawing cadence, palette, camera drift and the content
class (background-only / character / FX / lineart), plus the list of distinct drawings.

Usage: python recreate/make_script.py <hd_frames_dir> <out_json> [--end N]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import fill_image, glow_mask, ink_mask  # noqa: E402
from vectorize import shot_palette  # noqa: E402

FPS = 30


def load_small(paths, w=192):
    out = []
    for p in paths:
        im = cv2.imread(str(p))
        h = int(im.shape[0] * w / im.shape[1])
        out.append(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA))
    return out


def hists(small):
    hs = []
    for im in small:
        h = cv2.calcHist([im], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).flatten()
        hs.append(h / (h.sum() + 1e-9))
    return np.array(hs)


def detect_cuts(small, hs, mad_th=22.0, hist_th=0.6):
    cuts = []
    for i in range(len(small) - 1):
        mad = np.abs(small[i].astype(np.int16) - small[i + 1].astype(np.int16)).mean()
        hd = np.abs(hs[i] - hs[i + 1]).sum()
        if mad > mad_th and hd > hist_th:
            cuts.append(i + 1)
    return cuts


def merge_similar(bounds, hs, min_len=10, hist_th=0.45):
    """Fast action reads as a cut; merge neighbours that still share a colour world."""
    out = [bounds[0]]
    for b in bounds[1:-1]:
        lo = out[-1]
        if b - lo < min_len:
            continue
        a = hs[lo:b].mean(axis=0)
        c = hs[b:min(b + 12, len(hs))].mean(axis=0)
        if np.abs(a - c).sum() < hist_th:
            continue
        out.append(b)
    out.append(bounds[-1])
    return out


def distinct_drawings(small, lo, hi, th=0.6):
    """Indices where a new drawing appears (the rest are holds)."""
    keys = [lo]
    for i in range(lo + 1, hi):
        d = np.abs(small[i].astype(np.int16) - small[i - 1].astype(np.int16)).mean()
        if d > th:
            keys.append(i)
    return keys


def drift_track(small, lo, hi):
    """Cumulative camera translation across the shot, in analysis pixels."""
    pts = [(0.0, 0.0)]
    for i in range(lo, min(hi - 1, len(small) - 1)):
        a = cv2.cvtColor(small[i], cv2.COLOR_BGR2GRAY).astype(np.float64)
        b = cv2.cvtColor(small[i + 1], cv2.COLOR_BGR2GRAY).astype(np.float64)
        try:
            (sx, sy), resp = cv2.phaseCorrelate(a, b)
        except cv2.error:
            sx = sy = 0.0
            resp = 0.0
        if resp < 0.05 or abs(sx) > 30 or abs(sy) > 30:
            sx = sy = 0.0
        pts.append((pts[-1][0] + sx, pts[-1][1] + sy))
    return [[round(x, 2), round(y, 2)] for x, y in pts]


def classify(img, glow_share, ink_share):
    """What kind of shot this is, which decides how the Blender build treats it."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    whiteish = float(((hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 200)).mean())
    if whiteish > 0.45:
        return "lineart"          # the behind-the-scenes breakdown section
    if ink_share > 0.010:
        return "character"
    if glow_share > 0.02:
        return "fx"
    return "background"


def main(frames_dir, out_json, end=None):
    paths = sorted(Path(frames_dir).glob("f_*.png"))
    if end:
        paths = paths[:end]
    small = load_small(paths)
    hs = hists(small)
    cuts = detect_cuts(small, hs)
    bounds = merge_similar([0] + cuts + [len(small)], hs)

    shots = []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        mid_path = paths[(lo + hi) // 2]
        mid = cv2.imread(str(mid_path))
        im_ink = ink_mask(mid)
        im_glow = glow_mask(mid)
        ink_share = float(im_ink.mean() / 255)
        glow_share = float(im_glow.mean() / 255)

        keys = distinct_drawings(small, lo, hi)
        # palette from a handful of drawings across the shot, ink removed
        samp = [paths[k] for k in keys[:: max(1, len(keys) // 6)]][:6] or [mid_path]
        flats = []
        for sp in samp:
            im = cv2.imread(str(sp))
            flats.append(fill_image(im, ink_mask(im)))
        pal = shot_palette(flats, k=28)

        runs = np.diff(keys + [hi])
        shots.append({
            "idx": i,
            "start": lo, "end": hi, "n": hi - lo,
            "t_start": round(lo / FPS, 3), "dur": round((hi - lo) / FPS, 3),
            "kind": classify(mid, glow_share, ink_share),
            "ink_share": round(ink_share, 4),
            "glow_share": round(glow_share, 4),
            "keys": keys,
            "n_drawings": len(keys),
            "on_ns": int(np.median(runs)) if len(runs) else 1,
            "palette": [[int(c[2]), int(c[1]), int(c[0])] for c in pal],   # RGB
            "drift": drift_track(small, lo, hi),
            "ref_mid": mid_path.name,
        })

    res = {"source": str(frames_dir), "fps": FPS, "n_frames": len(small),
           "analysis_width": small[0].shape[1], "shots": shots}
    Path(out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")

    print(f"{len(small)} frames -> {len(shots)} shots  -> {out_json}")
    for s in shots:
        d = s["drift"][-1]
        print(f"  S{s['idx']:02d} f{s['start']:4d}-{s['end']:4d} {s['dur']:5.2f}s "
              f"{s['kind']:10s} draws={s['n_drawings']:3d} on{s['on_ns']}s "
              f"ink={s['ink_share']:.3f} glow={s['glow_share']:.3f} "
              f"pan=({d[0]:6.1f},{d[1]:6.1f})")


if __name__ == "__main__":
    a = sys.argv[1:]
    end = int(a[a.index("--end") + 1]) if "--end" in a else None
    main(a[0], a[1], end)
