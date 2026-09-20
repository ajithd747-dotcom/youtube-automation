"""Recover each shot's painted background plate.

2D animation is painted backgrounds with character cels on top, and that is how this
rebuild should be layered too.  Polygonising a brush-textured sky gives horizontal
streaks; a plate carries the texture properly and matches how the shot was made.

The character moves across the shot while the sky does not, so a per-pixel median over
the shot's drawings removes the character.  Where the character barely moves the median
keeps a ghost, so those pixels are inpainted instead.

Usage: python recreate/background.py <script.json> <hd_frames> <out_dir> [--shots 0,1]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import cel_matte  # noqa: E402


def align_stack(imgs, drift, scale):
    """Shift each drawing back onto the first one using the tracked camera drift."""
    out = []
    h, w = imgs[0].shape[:2]
    for im, (dx, dy) in zip(imgs, drift):
        M = np.float32([[1, 0, -dx * scale], [0, 1, -dy * scale]])
        out.append(cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE))
    return out


def _fill_holes(m):
    ff = m.copy()
    h, w = m.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    return cv2.bitwise_or(m, cv2.bitwise_not(ff))


def _cel_mask(img, bg, tol=20, ink=None):
    """The cel is the inked region: a drawn character carries dense line work, the
    painted sky carries almost none, so growing the ink and filling it gives a far more
    reliable matte than differencing against a background we are still guessing at.

    The growing runs downscaled (see `cel_matte`) - at full resolution the kernels this
    needs are far too slow to run over every drawing of every shot.
    """
    m = cel_matte(img, ink=ink).astype(np.uint8) * 255
    if bg is not None:                            # add anything clearly not background
        d = np.abs(img.astype(np.int16) - bg.astype(np.int16)).max(axis=2)
        extra = (d > tol).astype(np.uint8) * 255
        small = cv2.resize(extra, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        small = cv2.morphologyEx((small > 40).astype(np.uint8) * 255, cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        small = _fill_holes(small)
        n, lbl, stats, _ = cv2.connectedComponentsWithStats((small > 0).astype(np.uint8), 8)
        keep = np.zeros(n, np.uint8)
        keep[1:] = (stats[1:, cv2.CC_STAT_AREA] > 400).astype(np.uint8)
        small = (keep[lbl] * 255).astype(np.uint8)
        m = cv2.bitwise_or(m, cv2.resize(small, (img.shape[1], img.shape[0]),
                                         interpolation=cv2.INTER_NEAREST))
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))


def _row_fill(img, hole):
    """Fill each row by mirroring clean sky into the gap.

    Interpolating across the gap smears it into a grey smudge; a painted sky is
    horizontally coherent, so reflecting the nearest clean run back over the hole keeps
    the cloud texture and reads as real background.
    """
    out = img.copy()
    h, w = hole.shape
    for y in range(h):
        bad = hole[y] > 0
        if not bad.any():
            continue
        known = np.flatnonzero(~bad)
        if len(known) < 16:                       # nothing to go on; use the row above
            if y:
                out[y] = out[y - 1]
            continue

        src = np.arange(w)
        # walk each contiguous gap and mirror the neighbouring clean run into it
        edges = np.flatnonzero(np.diff(np.r_[0, bad.astype(np.int8), 0]))
        for a, b in zip(edges[::2], edges[1::2] - 1):
            idx = np.arange(a, b + 1)
            left_ok = a > 0 and not bad[a - 1]
            right_ok = b < w - 1 and not bad[b + 1]
            if left_ok and (not right_ok or a >= w - 1 - b):
                s = (a - 1) - (idx - a)           # reflect the run on the left
            elif right_ok:
                s = (b + 1) + (b - idx)           # reflect the run on the right
            else:
                s = np.full(len(idx), known[np.argmin(np.abs(known - a))])
            s = np.clip(s, 0, w - 1)
            # a reflection can land back inside another gap; snap those to real pixels
            still = bad[s]
            if still.any():
                pos = np.clip(np.searchsorted(known, s[still]), 0, len(known) - 1)
                s[still] = known[pos]
            src[a:b + 1] = s
        out[y] = img[y, src]
    return out


def plate(imgs, drift, scale, rounds=2, sharp=False, row_fill_max=0.15):
    """Masked median: rebuild the plate from only the pixels that are really background."""
    st = np.stack(align_stack(imgs, drift, scale))
    bg = np.median(st.astype(np.float32), axis=0).astype(np.uint8)

    for _ in range(rounds):
        masks = np.stack([_cel_mask(im, bg) for im in st])          # N,H,W
        vis = (masks == 0)
        cnt = vis.sum(axis=0)
        never = (cnt == 0).astype(np.uint8) * 255                    # always covered
        # In row bands. The nan-masked copy this median runs over is float32 and as tall
        # as the whole stack, so at 1080p it is 25 MB per drawing - shot 15's 60 drawings
        # asked for 1.5 GB in one allocation and background.py died without printing
        # anything, which finalize.py then reported only as a skipped shot. Banding keeps
        # the peak flat in the number of drawings; the result is identical.
        newbg = bg.copy()
        rows = max(16, int(1.5e8 // max(1, st.shape[0] * st.shape[2] * 12)))
        for y0 in range(0, st.shape[1], rows):
            y1 = min(y0 + rows, st.shape[1])
            acc = np.where(vis[:, y0:y1, :, None], st[:, y0:y1], np.nan).astype(np.float32)
            with np.errstate(all="ignore"):
                med = np.nanmedian(acc, axis=0)
            newbg[y0:y1] = np.where(np.isnan(med), bg[y0:y1].astype(np.float32),
                                    med).astype(np.uint8)
        bg = newbg

    if sharp:
        # Keep one real drawing's own pixels instead of the median, for brush texture.
        # Off by default: it also carries that drawing's own artefacts into the sky and
        # measured slightly worse (ssim 0.913 vs 0.914) as well as looking blotchier.
        cover = [float(m.mean()) for m in masks]
        best = int(np.argmin(cover))
        hole = cv2.dilate(masks[best],
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        soft = cv2.bilateralFilter(bg, 7, 35, 35)
        feather = cv2.GaussianBlur(hole.astype(np.float32) / 255.0, (41, 41), 0)[..., None]
        bg = (st[best] * (1 - feather) + soft * feather).astype(np.uint8)
    else:
        # Smooth only what we had to invent. Edge-preserving smoothing cleans up the
        # blotches the masked median leaves behind a character (shot 5: 0.842 -> 0.849),
        # but applied to the whole plate it also wipes the real brush texture off the
        # shots that barely needed repairing - it cost shot 11 0.966 -> 0.863. So it is
        # feathered in over the reconstructed area and the rest is left alone.
        soft = cv2.edgePreservingFilter(bg, flags=1, sigma_s=60, sigma_r=0.4)
        repaired = cv2.dilate(never, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
        if repaired.mean() > 0.5:
            f = cv2.GaussianBlur(repaired.astype(np.float32) / 255.0, (61, 61), 0)[..., None]
            bg = (bg * (1 - f) + soft * f).astype(np.uint8)
        bg = cv2.bilateralFilter(bg, 7, 35, 35)

    # Mirroring only makes sense for a hole small enough to have real sky beside it.
    # Where the mask covers a whole band of the frame in every drawing there is nothing
    # to mirror from, and reflecting the sky above down over the sea paints a pale band
    # where the reference is dark - shots 6/7/8 had 59-74% of the plate invented this
    # way and their lower third was the worst part of the film. Above the limit the
    # plain (unmasked) median is left in place: it is the better estimate precisely
    # because a region masked in every drawing is usually one the matte over-claimed,
    # so the median there is the background, not the character.
    frac = float((never > 0).mean())
    if 0.002 < frac < row_fill_max:
        bg = _row_fill(bg, never)
    return bg, never


def _hp(g):
    g = g.astype(np.float32)
    return g - cv2.GaussianBlur(g, (0, 0), 9)


def align_to_plate(bg, pairs, w=960, max_shift=260.0):
    """Per-frame offset of the plate, measured straight against each drawing.

    Chaining frame-to-frame deltas accumulates drift and breaks on held frames - the
    reference animates on 2s, so consecutive frames are often identical and the real
    camera move lands in a single jump when the drawing changes.  Registering every
    frame against the clean plate independently has neither problem.

    `pairs` is any iterable of (drawing, matte), so a long shot can be streamed off disk
    a frame at a time rather than held in memory - shot 15 is 91 frames, which is over
    half a gigabyte of decoded PNG before its mattes are counted.
    """
    h = int(bg.shape[0] * w / bg.shape[1])
    scale = bg.shape[1] / w
    P = _hp(cv2.cvtColor(cv2.resize(bg, (w, h), interpolation=cv2.INTER_AREA),
                         cv2.COLOR_BGR2GRAY))
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    out = []
    for im, mt in pairs:
        G = _hp(cv2.cvtColor(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2GRAY))
        m = cv2.resize(mt.astype(np.uint8) * 255, (w, h),
                       interpolation=cv2.INTER_NEAREST) > 0
        if m.mean() > 0.9:                        # matte swallowed the frame; trust nothing
            out.append(out[-1] if out else [0.0, 0.0])
            continue
        G = G.copy()
        G[m] = 0.0
        (dx, dy), resp = cv2.phaseCorrelate((P * win).astype(np.float64),
                                            (G * win).astype(np.float64))
        dx, dy = dx * scale, dy * scale
        if resp < 0.03 or abs(dx) > max_shift or abs(dy) > max_shift:
            dx, dy = (out[-1] if out else [0.0, 0.0])
        out.append([round(float(dx), 2), round(float(dy), 2)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("frames")
    ap.add_argument("out")
    ap.add_argument("--shots", default="")
    ap.add_argument("--sharp", action="store_true")
    ap.add_argument("--aligned", action="store_true")
    ap.add_argument("--row-fill-max", type=float, default=0.15,
                    help="skip the mirroring inpaint once this share of the "
                         "plate was masked in every drawing")
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    frames = sorted(Path(a.frames).glob("f_*.png"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    want = {int(x) for x in a.shots.split(",") if x.strip()} if a.shots else None

    for sh in scr["shots"]:
        if want is not None and sh["idx"] not in want:
            continue
        keys = sh["keys"]
        imgs = [cv2.imread(str(frames[k])) for k in keys]
        mattes = [cel_matte(im) for im in imgs]

        # One pass only. Re-deriving the plate from frames aligned by the first track
        # measured worse, not better (40px of camera move recovered against 107px): the
        # second plate is smeared by the first track's own error, and re-registering
        # against it just pulls the estimate back toward that error.
        bg, busy = plate(imgs, [[0.0, 0.0]] * len(keys), 1.0, sharp=a.sharp,
                         row_fill_max=a.row_fill_max)
        offs = align_to_plate(bg, zip(imgs, mattes))

        if a.aligned:
            # Rebuild in aligned space. A shot that pans a long way smears badly when
            # every drawing is stacked where it fell, and compositing that smear without
            # motion smears it twice. Building and compositing through the same track is
            # at least self-consistent: the background may lag the reference slightly,
            # but it stays sharp instead of dissolving.
            key_offs = [offs[min(k - sh["start"], len(offs) - 1)] for k in keys]
            bg, busy = plate(imgs, key_offs, 1.0, sharp=a.sharp,
                             row_fill_max=a.row_fill_max)
        cv2.imwrite(str(out / f"shot{sh['idx']:02d}_bg.png"), bg)
        cv2.imwrite(str(out / f"shot{sh['idx']:02d}_mask.png"), busy)
        n_drawings = len(imgs)
        del imgs, mattes                          # the plate is built; free it before
                                                  # streaming every frame of the shot

        # offsets for every frame of the shot, not just the distinct drawings
        def _stream(lo, hi):
            for k in range(lo, hi):
                im = cv2.imread(str(frames[k]))
                yield im, cel_matte(im)

        offs = align_to_plate(bg, _stream(sh["start"], sh["end"]))
        (out / f"shot{sh['idx']:02d}_offsets.json").write_text(
            json.dumps(offs), encoding="utf-8")

        rng = (max(o[1] for o in offs) - min(o[1] for o in offs))
        print(f"  S{sh['idx']:02d} plate from {n_drawings} drawings, "
              f"inpainted {busy.mean()/255*100:.1f}%, vertical move {rng:.0f}px "
              f"-> shot{sh['idx']:02d}_bg.png")


if __name__ == "__main__":
    main()
