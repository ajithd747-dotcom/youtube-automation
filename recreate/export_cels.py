"""Decompose every distinct drawing of a shot into cel data for the Blender build.

Reads the shot script, and for each shot writes one pickle holding the shot palette and,
per distinct drawing, the fill polygons and ink polylines.  Holds are not re-processed -
the script already says which frames are new drawings.

Usage:
  python recreate/export_cels.py <script.json> <hd_frames_dir> <out_dir> [--shots 0,1,5] [--jobs 2]
"""
import argparse
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import (cel_matte, fill_image, glow_mask, is_flat_tone,  # noqa: E402
                        is_mono, line_strokes)
from vectorize import shot_palette, vectorize_frame  # noqa: E402


def _drawing(args):
    """Decompose one frame. Runs in a worker process."""
    path, palette, cfg = args
    img = cv2.imread(str(path))

    # The two-tone impact frames are their own thing: the silhouettes ARE the drawing,
    # there is no painted background behind them and no ink layer over them.  They turn
    # up interleaved with normal drawings inside a shot, so this is decided per drawing.
    mono = is_mono(img) or is_flat_tone(img)
    if mono:
        flat = cv2.bilateralFilter(img, 7, 60, 60)
        strokes, m = [], np.zeros(img.shape[:2], np.uint8)
        gm = glow_mask(img)
        matte = None                       # paint the whole frame, plate included
    else:
        strokes, m = line_strokes(img, eps=cfg["ink_eps"], min_len=cfg["ink_min_len"],
                                  block=cfg["ink_block"], offset=cfg["ink_offset"],
                                  max_width=cfg["ink_max_width"])
        flat = fill_image(img, m)
        gm = glow_mask(img)
        matte = None
        if cfg.get("use_matte"):
            # with a painted background plate behind, the cels must not repaint the sky
            matte = cel_matte(img, ink=m)
            matte |= gm > 0
    if mono:
        # The explosion edge is fractal, so the detail pass has to stay above the noise
        # floor - chasing every speck produces thousands of fragments that read as noise
        # - but on its own it then leaves a third to a half of the frame bare. A coarse
        # pass underneath closes that speckle up and lays down the local tone for the
        # detail shapes to sit on.
        #
        # This only pays once the palette keeps the shot's greys (see main): quantised
        # against the grey ramp alone the coarse blobs land on mid-grey, which reads as
        # smudge against a crisp bimodal frame and measured worse than leaving the gaps
        # (ssim 0.656, or 0.616 restricted to the frame's own two extremes). With the
        # greys back the same pass is the single biggest win on shot 10: 0.677 -> 0.723
        # ssim, mae 18.1 -> 14.0. The threshold itself barely matters (0.7231 at 1200,
        # 0.7228 at 3000, 0.7207 at 6000).
        fills = []
        if MONO["coarse_area"]:
            fills += vectorize_frame(flat, palette, min_area=MONO["coarse_area"],
                                     eps=2.2, open_px=0, close_px=13, max_polys=80,
                                     matte=None)
        fills += vectorize_frame(flat, palette, min_area=MONO["min_area"],
                                 eps=MONO["eps"], open_px=MONO["open_px"],
                                 close_px=MONO["close_px"],
                                 max_polys=MONO["max_polys"], matte=None)
        # No edge-to-edge rectangle of the dominant tone either: that fixed the teal
        # leaking through the gaps, but wherever it guessed the wrong extreme the error
        # went to maximum (mae 40.6 against 27.6 without it). post.py measures the tone
        # for the gaps against the pixels these fills actually leave bare instead.
    else:
        fills = vectorize_frame(flat, palette, min_area=cfg["min_area"],
                                eps=cfg["fill_eps"], open_px=cfg["open_px"],
                                close_px=cfg["close_px"], matte=matte)

    # Glow polygons, split into brightness bands and emitted outer-first.
    # Averaging one colour over a whole FX blob mixes its white-hot core into its teal
    # rim and the result is a flat pale sticker; banding keeps the core bright, which is
    # also what gives the bloom in post something to catch.
    gp = []
    lum = img.max(axis=2)
    bands = [(0, 205), (205, 238), (238, 256)]
    for lo, hi in bands:
        bm = ((gm > 0) & (lum >= lo) & (lum < hi)).astype(np.uint8) * 255
        if bm.sum() == 0:
            continue
        bm = cv2.morphologyEx(bm, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        cnts, _ = cv2.findContours(bm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) < 30:
                continue
            a = cv2.approxPolyDP(c, 1.2, True).reshape(-1, 2)
            if len(a) < 3:
                continue
            mask = np.zeros(gm.shape, np.uint8)
            cv2.drawContours(mask, [c], -1, 255, cv2.FILLED)
            col = cv2.mean(img, mask=cv2.bitwise_and(mask, bm))[:3]
            gp.append({"pts": a.astype(np.int16),
                       "color": [int(col[2]), int(col[1]), int(col[0])],
                       "area": float(cv2.contourArea(c))})

    return {
        "fills": [{"mat": int(p["mat"]), "pts": p["pts"].astype(np.int16),
                   "holes": [h.astype(np.int16) for h in p["holes"]],
                   "area": p["area"]} for p in fills],
        "ink": [{"pts": s["pts"].astype(np.int16), "width": float(s["width"]),
                 "color": s["color"]} for s in strokes],
        "glow": gp,
    }


CFG = dict(ink_eps=1.2, ink_min_len=7, ink_block=25, ink_offset=9, ink_max_width=9,
           min_area=40, fill_eps=0.9, open_px=3, close_px=3, use_matte=True)

# Two-tone impact frames, tuned separately from the cel frames above; see _drawing.
MONO = dict(min_area=25, eps=0.8, open_px=0, close_px=3, max_polys=8000,
            coarse_area=3000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("frames")
    ap.add_argument("out")
    ap.add_argument("--shots", default="")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--no-matte", action="store_true")
    a = ap.parse_args()

    scr = json.loads(Path(a.script).read_text(encoding="utf-8"))
    frames = sorted(Path(a.frames).glob("f_*.png"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    want = {int(x) for x in a.shots.split(",") if x.strip()} if a.shots else None

    for sh in scr["shots"]:
        if want is not None and sh["idx"] not in want:
            continue
        dst = out / f"shot{sh['idx']:02d}.pkl"
        pal = np.array([[c[2], c[1], c[0]] for c in sh["palette"]], np.float32)  # -> BGR
        cfg = dict(CFG, use_matte=not a.no_matte)

        # A shot that mixes colour drawings with two-tone impact frames gets a palette
        # built almost entirely from the colour ones, so the greyscale frames quantise
        # onto teal and their soft smoke gradients collapse. Give those frames a grey
        # ramp of their own to land on.
        mono_flags = [(lambda im: is_mono(im) or is_flat_tone(im))(
            cv2.imread(str(frames[k]))) for k in sh["keys"]]
        n_mono = sum(mono_flags)
        if n_mono:
            # The shot palette in the script is k-means over the whole shot, and k-means
            # goes by pixel count. In a shot that is mostly two-tone the black and white
            # frames own every centroid: shot 10 came out with 28 pure greys and not one
            # teal, so its two colour drawings could only quantise to grey. Rebuild the
            # colour half from the colour drawings alone, where they are the only thing
            # competing, and keep the grey ramp for the two-tone ones.
            colour = [k for k, m in zip(sh["keys"], mono_flags) if not m]
            if colour and n_mono < len(mono_flags):
                imgs = []
                for k in colour:
                    im = cv2.imread(str(frames[k]))
                    imgs.append(cv2.resize(im, (480, int(480 * im.shape[0] / im.shape[1])),
                                           interpolation=cv2.INTER_AREA))
                # Added to the shot's own palette, not swapped for it. Replacing it
                # costs the two-tone frames the grey levels they quantise onto - on
                # shot 10 that traded ssim 0.668 for 0.618 to win the colour back.
                # Both fit: the greys serve the two-tone frames, these the colour ones.
                pal = np.vstack([pal, shot_palette(imgs, k=len(pal))])
                print(f"  S{sh['idx']:02d} +{len(pal)} colour entries from {len(colour)} "
                      f"colour drawing(s); {n_mono}/{len(mono_flags)} two-tone")
            # An even ramp, deliberately. These frames read as bimodal - one shot's
            # reference is 42% near black and 30% near white - and our output carries
            # more midtone than it should (30% of the frame against the reference's
            # 17%), so weighting the ramp towards the extremes looks like the obvious
            # fix. It is not: a ramp drawn from the drawings' own luminance quantiles
            # collapses to ~15 distinct levels, and the smoke's real gradients then have
            # nowhere to land (ssim 0.730 -> 0.719, mae 12.7 -> 16.5). The excess
            # midtone comes from the coarse pass averaging speckle, not from the ramp,
            # and that pass is still worth far more than it costs.
            ramp = np.linspace(4, 252, 22, dtype=np.float32)
            pal = np.vstack([pal, np.repeat(ramp[:, None], 3, axis=1)])
            print(f"  S{sh['idx']:02d} {n_mono}/{len(sh['keys'])} two-tone drawings; "
                  f"palette extended to {len(pal)}")

        jobs = [(frames[k], pal, cfg) for k in sh["keys"]]
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            draws = list(ex.map(_drawing, jobs))
        data = {"shot": sh, "palette_bgr": pal, "keys": sh["keys"], "drawings": draws}
        with open(dst, "wb") as f:
            pickle.dump(data, f, protocol=4)
        nf = sum(len(d["fills"]) for d in draws)
        ni = sum(len(d["ink"]) for d in draws)
        print(f"  S{sh['idx']:02d} {len(draws):3d} drawings  fills={nf:5d} ink={ni:5d} -> {dst.name}")


if __name__ == "__main__":
    main()
