"""Score a rebuilt shot against the reference, frame by frame.

This is the feedback loop: it says which frames are worst and why, so the next pass
changes something specific instead of guessing.

Usage:
  python recreate/compare.py <script.json> <shot_idx> <ref_frames> <our_frames> <out_dir>
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


def regions(h):
    return {"sky": (0, int(h * 0.45)), "mid": (int(h * 0.45), int(h * 0.72)),
            "low": (int(h * 0.72), h)}


def score_pair(a, b):
    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    s, dmap = ssim(ga, gb, full=True)
    e = 1.0 - dmap
    out = {"ssim": float(s),
           "mae": float(np.abs(a.astype(int) - b.astype(int)).mean())}
    for name, (lo, hi) in regions(a.shape[0]).items():
        out[f"err_{name}"] = float(e[lo:hi].mean())
    # how far the overall colour is off, which flat-palette errors show up in
    out["dhue"] = float(np.abs(cv2.cvtColor(a, cv2.COLOR_BGR2LAB).astype(int)
                               - cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(int))[:, :, 1:].mean())
    return out, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("shot", type=int)
    ap.add_argument("ref")
    ap.add_argument("ours")
    ap.add_argument("out")
    ap.add_argument("--worst", type=int, default=6)
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    sh = next(s for s in scr["shots"] if s["idx"] == a.shot)
    ref = sorted(Path(a.ref).glob("f_*.png"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(sh["n"]):
        ours = Path(a.ours) / f"f_{i + 1:04d}.png"
        if not ours.exists():
            continue
        A = cv2.imread(str(ref[sh["start"] + i]))
        B = cv2.imread(str(ours))[:, :, :3]
        if B.shape != A.shape:
            B = cv2.resize(B, (A.shape[1], A.shape[0]))
        sc, _ = score_pair(A, B)
        sc["frame"] = i + 1
        sc["ref_frame"] = sh["start"] + i
        rows.append(sc)

    if not rows:
        print("no rendered frames found")
        return

    keys = ["ssim", "mae", "err_sky", "err_mid", "err_low", "dhue"]
    mean = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    rows.sort(key=lambda r: r["ssim"])
    worst = rows[:a.worst]

    (out / f"shot{a.shot:02d}_scores.json").write_text(
        json.dumps({"shot": a.shot, "n": len(rows), "mean": mean,
                    "worst": worst, "frames": sorted(rows, key=lambda r: r["frame"])},
                   indent=1), encoding="utf-8")

    tiles = []
    for r in worst:
        A = cv2.imread(str(ref[r["ref_frame"]]))
        B = cv2.imread(str(Path(a.ours) / f"f_{r['frame']:04d}.png"))[:, :, :3]
        if B.shape != A.shape:
            B = cv2.resize(B, (A.shape[1], A.shape[0]))
        _, e = score_pair(A, B)
        hm = cv2.applyColorMap((np.clip(e, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        row = np.hstack([cv2.resize(x, (480, 270)) for x in (A, B, hm)])
        cv2.putText(row, f"f{r['frame']} ssim={r['ssim']:.3f}", (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(row)
    cv2.imwrite(str(out / f"shot{a.shot:02d}_worst.png"), np.vstack(tiles))

    print(f"shot {a.shot}: {len(rows)} frames  "
          + "  ".join(f"{k}={mean[k]:.4f}" for k in keys))
    print("  worst: " + ", ".join(f"f{r['frame']}({r['ssim']:.3f})" for r in worst))
    print(f"  -> {out}/shot{a.shot:02d}_worst.png")


if __name__ == "__main__":
    main()
