"""Per-frame colour grade for a shot's background plate.

One plate per shot assumes the background keeps one colour for the whole shot.  That
holds for the quiet shots, but in the FX shots the energy blast lights the whole scene
and the sky swings from grey to saturated teal within the shot - the median plate
averages that away and the composite sits grey under a bright blast.

So we measure, for every frame, the per-channel gain and offset that takes the plate to
that frame's own background, and store it next to the plate.  `post.py` applies it, so
compositing stays a lookup rather than another pass over the reference.

Usage: python recreate/grade.py <script.json> <hd_frames> <bg_dir> [--shots 1,2]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import cel_matte, glow_mask, is_flat_tone, is_mono  # noqa: E402


def frame_grade(plate, frame, exclude, lo_px=20000):
    """Per-channel (gain, offset) mapping plate -> frame over background pixels only."""
    ok = ~exclude
    if ok.sum() < lo_px:
        return [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]
    g, o = [], []
    for c in range(3):
        p = plate[:, :, c][ok].astype(np.float32)
        f = frame[:, :, c][ok].astype(np.float32)
        vp = p.var()
        if vp < 4.0:                                 # flat plate: offset only
            g.append(1.0)
            o.append(float(f.mean() - p.mean()))
            continue
        a = float(((p - p.mean()) * (f - f.mean())).mean() / vp)
        a = float(np.clip(a, 0.4, 2.5))              # keep it a grade, not a remap
        g.append(a)
        o.append(float(f.mean() - a * p.mean()))
    return g, o


def apply_grade(plate, gain, off):
    out = plate.astype(np.float32)
    for c in range(3):
        out[:, :, c] = out[:, :, c] * gain[c] + off[c]
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("frames")
    ap.add_argument("bg")
    ap.add_argument("--shots", default="")
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    frames = sorted(Path(a.frames).glob("f_*.png"))
    bgd = Path(a.bg)
    want = {int(x) for x in a.shots.split(",") if x.strip()} if a.shots else None

    for sh in scr["shots"]:
        if want is not None and sh["idx"] not in want:
            continue
        p = bgd / f"shot{sh['idx']:02d}_bg.png"
        if not p.exists():
            continue
        plate = cv2.imread(str(p))
        gains, offs, mono, base = [], [], [], []
        for k in range(sh["start"], sh["end"]):
            fr = cv2.imread(str(frames[k]))
            ex = cel_matte(fr) | (glow_mask(fr) > 0)
            g, o = frame_grade(plate, fr, ex)
            gains.append([round(v, 4) for v in g])
            offs.append([round(v, 2) for v in o])
            # A two-tone impact frame has no painted background to grade. Record it, and
            # the tone its paper actually is, so post.py can put a flat plate behind it
            # rather than letting the shot's teal sky show through the smoke.
            m = is_mono(fr) or is_flat_tone(fr)
            mono.append(bool(m))
            base.append([int(v) for v in np.median(
                fr[~(cel_matte(fr))] if (~cel_matte(fr)).any() else fr.reshape(-1, 3),
                axis=0)] if m else [0, 0, 0])
        (bgd / f"shot{sh['idx']:02d}_grade.json").write_text(
            json.dumps({"gain": gains, "off": offs, "mono": mono, "base": base}),
            encoding="utf-8")
        spread = max(max(o) for o in offs) - min(min(o) for o in offs)
        print(f"  S{sh['idx']:02d} graded {len(gains)} frames, offset range {spread:.0f}"
              + (f", {sum(mono)} two-tone" if any(mono) else ""))


if __name__ == "__main__":
    main()
