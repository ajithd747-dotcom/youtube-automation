"""Turn flat cel-shaded frames into layered filled polygons (Grease Pencil stroke data).

The reference art is flat-shaded 2D anime, so each frame is well approximated by a
stack of solid-colour polygons.  We build one palette per shot, then per drawing emit
polygons back-to-front so painting them in order reproduces the frame.

Exports:
    shot_palette(paths, k)        -> [(r,g,b), ...]
    vectorize_frame(img, palette) -> [ {mat, pts, holes, area}, ... ] painted in order
    rasterize(polys, palette, wh) -> np.uint8 BGR   (for fidelity measurement)
"""
import cv2
import numpy as np


# ---------------------------------------------------------------- palette

def shot_palette(imgs, k=28, sample=40000, accent_frac=0.25):
    """K-means palette over every drawing in a shot, so colours stay stable frame to frame.

    Plain k-means is driven by pixel counts, so a small but vivid accent - the
    character's blue hair against a whole sky - gets folded into a grey neighbour and the
    art goes flat.  So we spend part of the palette on a second pass over the pixels the
    first pass reproduced worst, which is exactly where those accents live.
    """
    px = []
    per = max(1, sample // max(1, len(imgs)))
    rng = np.random.default_rng(0)
    for im in imgs:
        f = im.reshape(-1, 3)
        idx = rng.choice(len(f), size=min(per, len(f)), replace=False)
        px.append(f[idx])
    px = np.concatenate(px).astype(np.float32)

    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    k_main = max(2, int(round(k * (1 - accent_frac))))
    _, lbl, cen = cv2.kmeans(px, k_main, None, crit, 5, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lbl.flatten(), minlength=k_main)
    cen = cen[np.argsort(-counts)]                   # most common first

    # Spend the accent budget on a colour-uniform sample rather than a pixel-uniform
    # one.  The character's blue hair is a few tenths of a percent of the frame, so by
    # pixel count it is invisible next to the sky and gets merged into a grey; giving
    # every distinct colour roughly equal weight puts it back in contention.
    k_acc = k - k_main
    if k_acc > 0:
        uni = _colour_uniform_sample(imgs, rng, cap=200)
        if len(uni) > k_acc * 8:
            d = ((uni[:, None, :] - cen[None]) ** 2).sum(2)
            worst = uni[np.sqrt(d.min(axis=1)) > 10.0]
            if len(worst) > k_acc * 8:
                _, _, acc = cv2.kmeans(worst.astype(np.float32), k_acc, None, crit, 5,
                                       cv2.KMEANS_PP_CENTERS)
                cen = np.vstack([cen, acc])
    return cen.astype(np.float32)                    # BGR float


def _colour_uniform_sample(imgs, rng, bits=5, cap=200):
    """One sample per distinct colour bucket (up to `cap` pixels each), so a rare colour
    weighs as much as a common one."""
    px = np.concatenate([im.reshape(-1, 3) for im in imgs])
    q = (px >> (8 - bits)).astype(np.int32)
    keys = (q[:, 0] << (2 * bits)) | (q[:, 1] << bits) | q[:, 2]
    order = np.argsort(keys, kind="stable")
    keys, px = keys[order], px[order]
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    ends = np.r_[starts[1:], len(keys)]
    out = []
    for s, e in zip(starts, ends):
        n = min(cap, e - s)
        out.append(px[s:s + n] if n == e - s else px[rng.integers(s, e, n)])
    return np.concatenate(out).astype(np.float32)


def quantize(img, palette, chunk=262144):
    """Nearest-palette-colour index per pixel.

    Done in chunks: the whole-image form allocates pixels x palette x 3 floats at once,
    which is over a gigabyte for a 1080p frame against a 50-entry palette and runs this
    machine out of memory.
    """
    h, w = img.shape[:2]
    f = img.reshape(-1, 3).astype(np.float32)
    pal = palette.reshape(1, -1, 3).astype(np.float32)
    out = np.empty(len(f), np.int32)
    for i in range(0, len(f), chunk):
        blk = f[i:i + chunk].reshape(-1, 1, 3)
        out[i:i + chunk] = ((blk - pal) ** 2).sum(axis=2).argmin(axis=1)
    return out.reshape(h, w)


# ---------------------------------------------------------------- vectorize

def _clean(mask, open_px, close_px):
    if close_px:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px, close_px))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    if open_px:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_px, open_px))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    return mask


def vectorize_frame(img, palette, min_area=40, eps=0.9, open_px=3, close_px=3,
                    max_polys=1400, matte=None):
    """Return polygons painted back-to-front.

    Each entry: {mat: palette index, pts: Nx2 int32, holes: [Nx2,...], area: float}
    Ordering: by area descending, so big background shapes are laid down first and
    small details (eyes, highlights, line work) end up on top.
    """
    lab = quantize(img, palette)
    polys = []
    for mi in range(len(palette)):
        mask = (lab == mi).astype(np.uint8) * 255
        if matte is not None:
            # only paint the cel; the painted background plate shows through elsewhere
            mask[~matte] = 0
        if mask.sum() == 0:
            continue
        mask = _clean(mask, open_px, close_px)
        cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hier is None:
            continue
        hier = hier[0]
        for ci, c in enumerate(cnts):
            if hier[ci][3] != -1:                    # a hole; attached to its parent below
                continue
            a = cv2.contourArea(c)
            if a < min_area:
                continue
            approx = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
            if len(approx) < 3:
                continue
            holes = []
            hi = hier[ci][2]                         # first child
            while hi != -1:
                hc = cnts[hi]
                if cv2.contourArea(hc) >= min_area:
                    ha = cv2.approxPolyDP(hc, eps, True).reshape(-1, 2)
                    if len(ha) >= 3:
                        holes.append(ha)
                hi = hier[hi][0]                     # next sibling
            polys.append({"mat": mi, "pts": approx, "holes": holes, "area": float(a)})

    polys.sort(key=lambda p: -p["area"])
    return polys[:max_polys]


# ---------------------------------------------------------------- check

def rasterize(polys, palette, wh):
    """Paint the polygons the way Blender will, to measure what we lose."""
    w, h = wh
    out = np.zeros((h, w, 3), np.uint8)
    for p in polys:
        col = tuple(int(v) for v in palette[p["mat"]])
        cv2.fillPoly(out, [p["pts"].astype(np.int32)], col, lineType=cv2.LINE_AA)
        # holes are re-filled by whatever polygon comes later; approximate by leaving them
    return out


def rasterize_with_holes(polys, palette, wh):
    """More faithful: holes punched by painting them from the frame behind."""
    w, h = wh
    out = np.zeros((h, w, 3), np.uint8)
    for p in polys:
        col = tuple(int(v) for v in palette[p["mat"]])
        cv2.drawContours(out, [p["pts"].astype(np.int32)], -1, col, cv2.FILLED)
    return out
