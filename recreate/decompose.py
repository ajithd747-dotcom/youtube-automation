"""Decompose a cel-animation frame into the layers it was drawn with.

Anime cel art is not "a field of flat colours" - it is flat colour fills with an ink
line layer on top.  Quantising the whole frame destroys the lines and the result looks
muddy, so we pull the layers apart first:

    lines   thin locally-dark ink strokes  -> polylines, drawn with real stroke width
    fills   flat colour regions underneath -> filled polygons
    glow    bright saturated FX            -> filled polygons flagged for bloom

`ink_mask` finds pixels that are markedly darker than their neighbourhood, which is what
an ink line is regardless of the local fill colour.
"""
import cv2
import numpy as np


# ---------------------------------------------------------------- ink lines

def ink_mask(img, block=25, offset=9, max_width=9):
    """Pixels that are much darker than the local background = ink.

    block/offset drive an adaptive threshold; max_width discards anything too thick to
    be a line (those are fills, e.g. a dark jacket).
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    bg = cv2.medianBlur(L, block | 1)
    dark = cv2.subtract(bg, L)                        # how much darker than surroundings
    m = (dark > offset).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # drop blobs thicker than a line: erode by max_width/2, anything surviving is a fill
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max_width, max_width))
    thick = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    m = cv2.subtract(m, thick)
    # remove speckle
    nlab, lbl, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros(nlab, np.uint8)
    keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= 12).astype(np.uint8)
    return (keep[lbl] * 255).astype(np.uint8)


def _neighbours(y, x, h, w):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    yield ny, nx


def trace_skeleton(skel, min_len=7):
    """Walk a 1-px skeleton into polylines (list of Nx2 arrays, x,y order)."""
    h, w = skel.shape
    on = skel > 0
    deg = cv2.filter2D(on.astype(np.uint8), -1,
                       np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.uint8),
                       borderType=cv2.BORDER_CONSTANT)
    deg = deg * on
    used = np.zeros_like(on)
    paths = []

    def walk(sy, sx):
        path = [(sx, sy)]
        used[sy, sx] = True
        cy, cx = sy, sx
        while True:
            nxt = None
            for ny, nx in _neighbours(cy, cx, h, w):
                if on[ny, nx] and not used[ny, nx]:
                    nxt = (ny, nx)
                    if abs(ny - cy) + abs(nx - cx) == 1:   # prefer 4-connected
                        break
            if nxt is None:
                return path
            cy, cx = nxt
            used[cy, cx] = True
            path.append((cx, cy))

    ends = np.argwhere(on & (deg != 2))        # endpoints and junctions first
    for sy, sx in ends:
        if used[sy, sx]:
            continue
        p = walk(sy, sx)
        if len(p) >= min_len:
            paths.append(np.array(p, np.int32))
    for sy, sx in np.argwhere(on):             # then leftover closed loops
        if used[sy, sx]:
            continue
        p = walk(sy, sx)
        if len(p) >= min_len:
            paths.append(np.array(p, np.int32))
    return paths


def line_strokes(img, eps=1.2, min_len=7, **kw):
    """Ink lines as {pts, width, color} ready to become Grease Pencil strokes."""
    m = ink_mask(img, **kw)
    if m.sum() == 0:
        return [], m
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    skel = _skeleton(m)
    out = []
    for p in trace_skeleton(skel, min_len):
        simp = cv2.approxPolyDP(p.reshape(-1, 1, 2), eps, False).reshape(-1, 2)
        if len(simp) < 2:
            continue
        wid = float(np.median(dist[p[:, 1], p[:, 0]]) * 2.0)
        cols = img[p[:, 1], p[:, 0]].astype(np.float32)
        out.append({"pts": simp, "width": max(1.2, wid),
                    "color": [int(v) for v in np.median(cols, axis=0)]})
    return out, m


def _skeleton(mask):
    from skimage.morphology import skeletonize
    return (skeletonize(mask > 0).astype(np.uint8)) * 255


# ---------------------------------------------------------------- fills

def fill_image(img, mask):
    """Remove the ink so the palette is built from fill colours only."""
    return cv2.inpaint(img, cv2.dilate(mask, np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)


def is_mono(img, sat_max=26.0, bimodal_min=0.75, tail_min=0.12):
    """True for the stark two-tone impact frames.

    Those shots are black silhouettes on white with no painted background and no ink
    layer - the shapes are the art.  Running the normal cel path over them is wrong in
    every stage: there is no plate to recover, the ink detector fires on everything, and
    the fills shatter into thousands of fragments along the explosion's ragged edge.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    if float(hsv[:, :, 1].mean()) > sat_max:
        return False
    # Bimodality is what actually separates these frames, not how little colour they
    # have: the grey wasteland shots are just as desaturated but their tones are spread
    # across the midrange (0.14-0.27 here) while the impact frames pile up at pure black
    # and pure white (0.82-0.86).  Keying on desaturation alone swept up half the film
    # and cost 0.04 weighted ssim before the scores caught it.
    #
    # Both tails have to be populated, or "bimodal" is satisfied by a frame that is all
    # one tone. The tutorial half of this reference is thin red construction lines on
    # white paper: 99% of it is above the light threshold and 0.3% below the dark one,
    # so the combined test alone called all 117 of its drawings two-tone and would have
    # sent them down a path that throws their line layer away. A true impact frame keeps
    # both tails heavy (0.43/0.37 and 0.21/0.57 on shot 10).
    v = hsv[:, :, 2]
    dark = float((v < 70).mean())
    light = float((v > 195).mean())
    return dark + light >= bimodal_min and min(dark, light) >= tail_min


def is_flat_tone(img, sat_max=26.0, dark_min=0.75, light_max=0.05):
    """A desaturated frame that is nearly all dark, with no line layer to pull off it.

    The same full-frame treatment as a two-tone frame suits these, for different
    reasons: shot 12's fade frames are a smooth near-black glow, so there is no ink to
    extract, the cel matte has no dense line work to find, and the shot's median plate
    is nothing like them - painting the whole frame off the grey ramp beats compositing
    cels over that plate (ssim 0.955 against 0.943 when they went down the cel path).

    Deliberately one-sided. The mirror case, a frame that is nearly all *light*, is the
    tutorial half of this reference - white paper carrying thin red construction lines -
    and that art is its line layer, so it has to stay on the cel path.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    if float(hsv[:, :, 1].mean()) > sat_max:
        return False
    v = hsv[:, :, 2]
    return float((v < 70).mean()) >= dark_min and float((v > 195).mean()) <= light_max


def fill_holes(m):
    ff = m.copy()
    h, w = m.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    return cv2.bitwise_or(m, cv2.bitwise_not(ff))


def cel_matte(img, ink=None, scale=0.25, min_area=400, grow=6):
    """The drawn cel (character + FX) as against the painted background.

    A drawn character carries dense line work and the painted sky carries almost none,
    so growing the ink and filling the enclosed area isolates the cel.  The morphology
    runs on a downscaled copy - the matte only needs to be roughly right, and at full
    resolution the big kernels are far too slow to run over every drawing.
    """
    if ink is None:
        ink = ink_mask(img)
    small = cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = (small > 20).astype(np.uint8) * 255
    small = cv2.dilate(small, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    small = cv2.morphologyEx(small, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    small = fill_holes(small)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats((small > 0).astype(np.uint8), 8)
    keep = np.zeros(n, np.uint8)
    keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= min_area).astype(np.uint8)
    small = (keep[lbl] * 255).astype(np.uint8)
    small = cv2.dilate(small, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow)))
    m = cv2.resize(small, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(m, (5, 5), 0) > 40


def glow_mask(img, sat_min=60, val_min=150, core_val=235, reach=25):
    """Bright saturated FX (the teal energy) - these want bloom, not flat paint.

    The white-hot middle of an FX blob is by definition *not* saturated - it has blown
    out to white - so the saturation test throws away the brightest part of the very
    thing it is trying to find. Measured on an energy orb: the pixels over `core_val`
    average saturation 7.2 against the gate's 60, and only 3.5% of them landed inside
    the mask, so the orb lost its core and rendered as a flat teal sticker.

    So bright pixels are added back, but only where they are within `reach` of real
    saturated glow. That keeps the core of an orb and still refuses a sheet of white
    paper, which has no saturated glow anywhere near it.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat, val = hsv[:, :, 1], hsv[:, :, 2]
    m = ((sat > sat_min) & (val > val_min)).astype(np.uint8) * 255
    k7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k7)
    if m.any():
        # Only holes small enough to *be* a core. Hole-filling is what catches an orb,
        # whose blown-out middle is wider than any sensible dilation - but unbounded it
        # also floods a sheet of white paper that happens to be ringed by unrelated
        # saturated marks, which is the tutorial half of this reference: shot 16 went
        # from 4.6% glow to 33%. A core cannot be bigger than the ring around it, nor a
        # large part of the frame.
        holes = cv2.subtract(fill_holes(m), m)
        cap = min(float((m > 0).sum()), 0.05 * m.size)
        if holes.any():
            n, lbl, stats, _ = cv2.connectedComponentsWithStats((holes > 0).astype(np.uint8), 8)
            keep = np.zeros(n, np.uint8)
            keep[1:] = (stats[1:, cv2.CC_STAT_AREA] <= cap).astype(np.uint8)
            holes = (keep[lbl] * 255).astype(np.uint8)
        core = ((val > core_val).astype(np.uint8) * 255) & holes
        m = cv2.morphologyEx(cv2.bitwise_or(m, core), cv2.MORPH_CLOSE, k7)
    return m
