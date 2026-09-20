"""Composite a rendered shot: painted background plate, cels over it, then bloom.

Blender renders the cels alone on a transparent film; the plate goes under them here and
the glow is added here too.  Both stay out of Blender deliberately - an image-textured
plane crashes this machine's Radeon driver, and compositor glare costs seconds a frame
on it, while doing the same work on the frames costs milliseconds.

Usage:
  python recreate/post.py <script.json> <shot> <cels_dir> <bg.png> <out_dir> [--bloom 0.8]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import is_flat_tone, is_mono  # noqa: E402
from grade import apply_grade  # noqa: E402


def warp(bg, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(bg, M, (bg.shape[1], bg.shape[0]),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def over(fg_rgba, bg):
    a = (fg_rgba[:, :, 3:4].astype(np.float32) / 255.0)
    return (fg_rgba[:, :, :3].astype(np.float32) * a
            + bg.astype(np.float32) * (1 - a)).astype(np.uint8)


def bloom(img, strength=0.8, thresh=185, sigma=21):
    """Screen a blurred copy of the bright areas back over the frame.

    The reference's energy FX has a white core bleeding into a teal halo, which is what
    this reproduces; without it the orb reads as a flat sticker.
    """
    if strength <= 0:
        return img
    f = img.astype(np.float32)
    lum = f.max(axis=2)
    keep = np.clip((lum - thresh) / max(1.0, 255.0 - thresh), 0, 1)[..., None]
    bright = f * keep
    k = int(sigma) * 4 + 1
    g = cv2.GaussianBlur(bright, (k, k), sigma)
    g += cv2.GaussianBlur(bright, (k * 2 + 1, k * 2 + 1), sigma * 2.5) * 0.6
    out = 255.0 - (255.0 - f) * (255.0 - np.clip(g * strength, 0, 255)) / 255.0
    return np.clip(out, 0, 255).astype(np.uint8)


def bright_fraction(img, thresh=185):
    """Share of the frame already above the bloom threshold."""
    return float((img.max(axis=2) > thresh).mean())


def mono_base(grade, j, sh, i, fg, refs, min_bare=2000):
    """Tone for the flat plate behind a two-tone frame.

    The median over the pixels this frame's cels actually leave bare is the flat fill
    with the smallest possible absolute error there, so it beats any guess made before
    the render. Falls back to grade.py's estimate when the render is opaque, the bare
    area is too small to measure, or the reference frames are not to hand.
    """
    if refs is not None and len(refs) and fg.ndim == 3 and fg.shape[2] == 4:
        k = sh["start"] + i
        if 0 <= k < len(refs):
            bare = fg[:, :, 3] < 128
            if int(bare.sum()) >= min_bare:
                r = cv2.imread(str(refs[k]))
                if r is not None and r.shape[:2] == bare.shape:
                    return np.median(r[bare], axis=0)
    return np.array(grade["base"][j], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("shot", type=int)
    ap.add_argument("cels")
    ap.add_argument("bg")
    ap.add_argument("out")
    # 0.25, not the 0.8 this was tuned to. That value was compensating for a glow
    # layer that was throwing its blown-out core away (see decompose.glow_mask);
    # with the core actually rendered, bloom on top double-counts the light and
    # washes the saturated halo towards white. Both metrics improve monotonically
    # as it comes down and plateau at 0.12-0.25 (shot 9 mae 8.65 -> 7.38), and 0.25
    # is where the reference's soft outer halo is still there - at 0.0 the FX goes
    # flat and shot 1's ssim turns back down.
    ap.add_argument("--bloom", type=float, default=0.25)
    ap.add_argument("--bloom-max-bright", type=float, default=0.5,
                    help="skip bloom once this share of the frame is already bright")
    # Default 0: the plate is composited over the whole shot, so it already sits at the
    # mean camera position. Pushing it around by an imperfect track measured worse than
    # leaving it still (ssim 0.914 at 0.0, 0.911 at 0.5, 0.909 at 1.0).
    ap.add_argument("--plate-motion", type=float, default=0.0,
                    help="scale on the measured plate offsets; 0 pins the plate still")
    ap.add_argument("--ref-frames", default="recreate/ref_analysis/flip_hd",
                    help="reference frames, used to tone the flat plate behind a "
                         "two-tone frame against the area the cels leave bare")
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    sh = next(s for s in scr["shots"] if s["idx"] == a.shot)
    bg = cv2.imread(a.bg)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # Offsets measured per frame straight against the plate; fall back to the shot
    # script's coarse drift only if that step has not been run.
    op = Path(a.bg).with_name(Path(a.bg).name.replace("_bg.png", "_offsets.json"))
    if op.exists():
        offs = json.loads(op.read_text(encoding="utf-8"))
        sc = 1.0                                    # already in full-res pixels
    else:
        offs = sh["drift"]
        sc = bg.shape[1] / scr["analysis_width"]

    # Per-frame grade on the plate, when it has been measured (see grade.py). Without it
    # an FX shot composites a grey sky under a blast that should be lighting the scene.
    gp = Path(a.bg).with_name(Path(a.bg).name.replace("_bg.png", "_grade.json"))
    grade = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else None

    # Two-tone frames get a flat plate, and its tone matters more than anywhere else in
    # the film: the fractal explosion edge leaves a third to a half of the frame bare, so
    # a wrong guess is a wrong half-frame. grade.py has to guess it from the cel matte
    # before the render exists, and on these frames that matte is unreliable - it put
    # black behind a bright frame on 8 of shot 10's 9 two-tone frames, which was nearly
    # the whole of that shot's error. Here the render exists, so the bare pixels are
    # known exactly and the tone can be measured on them instead of guessed.
    refs = sorted(Path(a.ref_frames).glob("f_*.png")) if Path(a.ref_frames).is_dir() else []

    n = 0
    for i in range(sh["n"]):
        src = Path(a.cels) / f"f_{i + 1:04d}.png"
        if not src.exists():
            continue
        fg = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
        plate = bg
        if grade is not None:
            j = min(i, len(grade["gain"]) - 1)
            if grade.get("mono") and grade["mono"][j]:
                # two-tone frame: flat paper behind it, not the shot's painted sky
                plate = np.full_like(bg, np.array(mono_base(grade, j, sh, i, fg, refs),
                                                  np.uint8))
            else:
                plate = apply_grade(bg, grade["gain"][j], grade["off"][j])
        if fg.shape[2] == 3:                        # rendered opaque; nothing to composite
            frame = fg
        else:
            # phaseCorrelate(plate, frame) gives the shift taking the plate TO the
            # frame, so the plate moves by +d to sit where this frame sees it
            dx, dy = offs[min(i, len(offs) - 1)]
            k = a.plate_motion
            frame = over(fg, warp(plate, dx * sc * k, dy * sc * k))
        # No bloom on a frame that is mostly paper. Bloom is meant for a localised
        # energy FX; when most of the frame already sits over the threshold the glare
        # has nowhere to fall off and blows the whole thing to white. The tutorial
        # shots are 95-99% white paper and came out as blank white frames (std 0.08
        # against the reference's 23) while still scoring ssim 0.95, because the paper
        # they got right is most of the picture - exactly the kind of silent failure
        # the scores cannot see. Measured on bright coverage rather than inferred from
        # the frame's class: the shots that need bloom peak at 0.34, the paper ones
        # start at 0.95.
        strength = 0.0 if (is_mono(frame) or is_flat_tone(frame)
                           or bright_fraction(frame) > a.bloom_max_bright) else a.bloom
        cv2.imwrite(str(out / f"f_{i + 1:04d}.png"), bloom(frame, strength))
        n += 1
    print(f"shot {a.shot}: composited {n} frames -> {out}")


if __name__ == "__main__":
    main()
