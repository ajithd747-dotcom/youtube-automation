"""Join the finished shots into one video and score the whole thing against the reference.

Usage:
  python recreate/assemble.py <script.json> <out.mp4> [--shots 0-12] [--audio ref.mp4]
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def expand(spec, all_idx):
    if not spec:
        return all_idx
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [i for i in out if i in all_idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--work", default="recreate/out")
    ap.add_argument("--shots", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--side-by-side", action="store_true")
    ap.add_argument("--ref-frames", default="recreate/ref_analysis/flip_hd")
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    idx = expand(a.shots, [s["idx"] for s in scr["shots"]])
    work = Path(a.work)

    seq = work / "_final"
    seq.mkdir(parents=True, exist_ok=True)
    for old in seq.glob("f_*.png"):
        old.unlink()

    n = 0
    missing = []
    for i in idx:
        sh = next(s for s in scr["shots"] if s["idx"] == i)
        src = work / f"s{i:02d}"
        got = 0
        for k in range(sh["n"]):
            p = src / f"f_{k + 1:04d}.png"
            if not p.exists():
                continue
            n += 1
            got += 1
            (seq / f"f_{n:05d}.png").write_bytes(p.read_bytes())
        if got != sh["n"]:
            missing.append((i, got, sh["n"]))

    if missing:
        print("incomplete shots (idx, have, want):", missing)
    if not n:
        print("nothing to assemble")
        return

    cmd = ["ffmpeg", "-y", "-framerate", str(a.fps), "-i", str(seq / "f_%05d.png")]
    if a.audio:
        cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
            "-preset", "slow", str(a.out)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="ignore")
    if r.returncode:
        print(r.stderr[-1500:])
        return
    print(f"assembled {n} frames ({n / a.fps:.2f}s) -> {a.out}")

    if a.side_by_side:
        build_side_by_side(a, scr, idx, seq, n)


def build_side_by_side(a, scr, idx, seq, n):
    """Reference on the left, rebuild on the right, so the two can be watched together.

    Only the stretch of reference the rebuilt shots actually cover is used, so the two
    sides stay in step even when some shots are skipped.
    """
    ref = sorted(Path(a.ref_frames).glob("f_*.png"))
    pair = Path(a.work) / "_sbs"
    pair.mkdir(parents=True, exist_ok=True)
    for old in pair.glob("f_*.png"):
        old.unlink()

    j = 0
    for i in idx:
        sh = next(s for s in scr["shots"] if s["idx"] == i)
        for k in range(sh["n"]):
            ours = seq / f"f_{j + 1:05d}.png"
            if not ours.exists():
                continue
            A = cv2.imread(str(ref[sh["start"] + k]))
            B = cv2.imread(str(ours))[:, :, :3]
            h = 540
            A = cv2.resize(A, (int(A.shape[1] * h / A.shape[0]), h))
            B = cv2.resize(B, (A.shape[1], h))
            cv2.putText(A, "reference", (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(B, "blender rebuild", (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2, cv2.LINE_AA)
            j += 1
            cv2.imwrite(str(pair / f"f_{j:05d}.png"), np.hstack([A, B]))

    out = str(Path(a.out).with_name(Path(a.out).stem + "_sbs.mp4"))
    r = subprocess.run(["ffmpeg", "-y", "-framerate", str(a.fps),
                        "-i", str(pair / "f_%05d.png"), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "18", out],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    print(f"side-by-side -> {out}" if not r.returncode else r.stderr[-800:])


if __name__ == "__main__":
    main()
