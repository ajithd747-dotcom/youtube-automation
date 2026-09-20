"""Turn reference frames into layered cel data (fills + ink + glow) and check fidelity.

This is the representation the Blender Grease Pencil build consumes:
    fills : filled polygons, painted back-to-front
    ink   : polylines with a width, drawn on top
    glow  : filled polygons flagged for bloom in the compositor

`preview()` paints the same data with OpenCV so fidelity can be measured without
waiting on a render.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import fill_image, glow_mask, ink_mask, line_strokes  # noqa: E402
from vectorize import shot_palette, vectorize_frame  # noqa: E402


def build_frame(img, palette, ink_kw=None, min_area=40, eps=0.9):
    ink_kw = ink_kw or {}
    strokes, m = line_strokes(img, **ink_kw)
    flat = fill_image(img, m)
    fills = vectorize_frame(flat, palette, min_area=min_area, eps=eps)
    glow = glow_mask(img)
    return {"fills": fills, "ink": strokes, "glow": glow, "flat": flat}


def preview(cel, palette, wh, draw_ink=True):
    w, h = wh
    out = np.zeros((h, w, 3), np.uint8)
    for p in cel["fills"]:
        col = tuple(int(v) for v in palette[p["mat"]])
        cv2.drawContours(out, [p["pts"].astype(np.int32)], -1, col, cv2.FILLED, cv2.LINE_AA)
    if draw_ink:
        for s in cel["ink"]:
            cv2.polylines(out, [s["pts"].astype(np.int32)], False,
                          tuple(int(v) for v in s["color"]),
                          max(1, int(round(s["width"]))), cv2.LINE_AA)
    return out


def score(a, b):
    from skimage.metrics import structural_similarity as ssim
    g1 = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    return (float(ssim(g1, g2)),
            float(np.abs(a.astype(int) - b.astype(int)).mean()))


if __name__ == "__main__":
    import time
    nums = [int(x) for x in sys.argv[1:]] or [130, 160, 200, 300]
    imgs = [cv2.imread(f"recreate/ref_analysis/flip_hd/f_{n:04d}.png") for n in nums]
    pal = shot_palette([fill_image(im, ink_mask(im)) for im in imgs], k=28)
    for n, im in zip(nums, imgs):
        t = time.time()
        cel = build_frame(im, pal)
        rec = preview(cel, pal, (im.shape[1], im.shape[0]))
        s_no = score(im, preview(cel, pal, (im.shape[1], im.shape[0]), draw_ink=False))
        s, mae = score(im, rec)
        print(f"f{n}: fills={len(cel['fills']):4d} ink={len(cel['ink']):4d} "
              f"ssim={s:.4f} (no-ink {s_no[0]:.4f}) mae={mae:5.2f}  {time.time()-t:.1f}s")
        cv2.imwrite(f"recreate/ref_analysis/rec_{n:04d}.png", rec)
