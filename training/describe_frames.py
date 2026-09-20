"""Layer A of the per-frame script: measure one frame against its neighbours.

Every number here comes from pixels. Where a measurement is impossible (no previous frame, RANSAC found no camera
model, no salient blob) the field is None -- serialised as null -- which means NOT MEASURED, never "zero" or "default".

Units: positions are fractions of the (letterbox-cropped) frame, 0..1, x right, y down. Speeds are fractions of the
frame WIDTH per frame. Angles are degrees, 0 = right, 90 = down, clockwise on screen. Luma is 0..1.
"""
import math
from functools import lru_cache

import cv2
import numpy as np

MEASURE_WIDTH = 320
PARTICLE_AREA_PX = (2, 90)          # connected moving blob size (px at MEASURE_WIDTH) that counts as a particle
MOVING_PIXEL_PX = 0.5               # residual flow above this (px at MEASURE_WIDTH) counts as moving


def r(x, n=4):
    return None if x is None else round(float(x), n)


def find_content_rect(sample_frames_bgr):
    """(x0, y0, x1, y1) of the picture without black letterbox/pillarbox bars, median over sample frames."""
    tops, bots, lefts, rights = [], [], [], []
    for im in sample_frames_bgr:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        rows = g.max(axis=1) > 16
        cols = g.max(axis=0) > 16
        if not rows.any() or not cols.any():
            continue
        tops.append(int(np.argmax(rows)))
        bots.append(int(len(rows) - np.argmax(rows[::-1])))
        lefts.append(int(np.argmax(cols)))
        rights.append(int(len(cols) - np.argmax(cols[::-1])))
    if not tops:
        return (0, 0, sample_frames_bgr[0].shape[1], sample_frames_bgr[0].shape[0])
    return (int(np.median(lefts)), int(np.median(tops)), int(np.median(rights)), int(np.median(bots)))


def prepare_frame(bgr, crop):
    """Crop the bars off and shrink to MEASURE_WIDTH. Returns (bgr, gray uint8)."""
    x0, y0, x1, y1 = crop
    im = bgr[y0:y1, x0:x1]
    h = max(2, int(round(im.shape[0] * MEASURE_WIDTH / im.shape[1])))
    im = cv2.resize(im, (MEASURE_WIDTH, h), interpolation=cv2.INTER_AREA)
    return im, cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)


@lru_cache(maxsize=8)
def coordinate_grids(h, w):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs, ys


# ----------------------------------------------------------------------------- lighting + colour
def measure_lighting(bgr, gray_u8, prev_mean_luma):
    g = gray_u8.astype(np.float32) / 255.0
    h, w = g.shape
    p5, p50, p95 = np.percentile(g, [5, 50, 95])
    xs, ys = coordinate_grids(h, w)

    # brightest region: where the light source / sun / lamp is on screen
    blur = cv2.GaussianBlur(g, (0, 0), 4)
    thr = max(float(np.percentile(blur, 97)), 0.5)
    mask = (blur >= thr).astype(np.uint8)
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        bright_xy = (cents[k][0] / w, cents[k][1] / h)
        bright_area = stats[k, cv2.CC_STAT_AREA] / (h * w)
    else:
        bright_xy, bright_area = (None, None), None

    # plane fit luma ~ a*x + b*y + c : (a, b) points toward the brighter side = key light direction on screen
    A = np.stack([(xs / w).ravel()[::7], (ys / h).ravel()[::7], np.ones(xs.size)[::7]], axis=1)
    coef, *_ = np.linalg.lstsq(A, g.ravel()[::7], rcond=None)
    grad_mag = math.hypot(coef[0], coef[1])
    grad_angle = math.degrees(math.atan2(coef[1], coef[0])) % 360 if grad_mag > 0.02 else None

    bright = g > 0.85
    halo = cv2.GaussianBlur(bright.astype(np.float32), (0, 0), 6)
    bloom = float(halo[~bright].mean()) if (~bright).any() else 0.0

    ch, cw = int(h * 0.15), int(w * 0.15)
    corners = np.mean([g[:ch, :cw].mean(), g[:ch, -cw:].mean(), g[-ch:, :cw].mean(), g[-ch:, -cw:].mean()])
    centre = g[int(h * 0.35):int(h * 0.65), int(w * 0.35):int(w * 0.65)].mean()

    b, gr, rr = [bgr[:, :, i].astype(np.float32).mean() for i in range(3)]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    mean_luma = float(g.mean())
    return {
        "luma_mean": r(mean_luma), "luma_std": r(g.std()), "luma_p5": r(p5), "luma_p50": r(p50), "luma_p95": r(p95),
        "clipped_highlights": r((g > 0.97).mean()), "crushed_shadows": r((g < 0.03).mean()),
        "warmth_r_over_b": r(rr / (b + 1e-6)), "lab_a": r(lab[:, :, 1].mean() - 128), "lab_b": r(lab[:, :, 2].mean() - 128),
        "brightest_x": r(bright_xy[0]), "brightest_y": r(bright_xy[1]), "brightest_area": r(bright_area),
        "key_gradient_strength": r(grad_mag), "key_gradient_angle_deg": r(grad_angle, 1),
        "top_minus_bottom": r(g[:h // 3].mean() - g[-(h // 3):].mean()), "left_minus_right": r(g[:, :w // 3].mean() - g[:, -(w // 3):].mean()),
        "bloom": r(bloom), "vignette_corner_over_centre": r(corners / (centre + 1e-6)),
        "luma_grid3x3": [r(g[gy * h // 3:(gy + 1) * h // 3, gx * w // 3:(gx + 1) * w // 3].mean()) for gy in range(3) for gx in range(3)],
        "exposure_delta": None if prev_mean_luma is None else r(mean_luma - prev_mean_luma),
    }, mean_luma


def measure_colour(bgr):
    small = cv2.resize(bgr, (48, 27), interpolation=cv2.INTER_AREA)
    data = small.reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 8, 1.0)
    _, labels, centres = cv2.kmeans(data, 5, None, crit, 1, cv2.KMEANS_PP_CENTERS)
    shares = np.bincount(labels.ravel(), minlength=5) / len(labels)
    order = np.argsort(-shares)
    palette = [{"rgb": [int(centres[i][2]), int(centres[i][1]), int(centres[i][0])], "share": r(shares[i], 3)} for i in order]

    f = bgr.astype(np.float32)
    B, G, R = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    rg, yb = R - G, 0.5 * (R + G) - B
    colourfulness = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    grey = f.mean(axis=2)
    lo, hi = np.percentile(grey, [20, 80])

    def tint(mask):
        if mask.sum() < 20:
            return None
        m = f[mask].mean(axis=0)
        t = m - m.mean()
        return [r(t[2], 1), r(t[1], 1), r(t[0], 1)]      # RGB deviation from neutral

    return {"palette": palette, "saturation_mean": r(hsv[:, :, 1].mean() / 255), "colourfulness": r(colourfulness / 255),
            "shadow_tint_rgb": tint(grey <= lo), "highlight_tint_rgb": tint(grey >= hi)}


# ----------------------------------------------------------------------------- motion + physics
def measure_motion_and_physics(prev_gray, gray, prev_bgr, bgr):
    """Camera model + residual (subject) motion + particle statistics from Farneback flow prev -> current."""
    none_cam = {"dx": None, "dy": None, "zoom": None, "roll_deg": None}
    if prev_gray is None:
        return (none_cam, {k: None for k in ("mean_speed", "p95_speed", "moving_share", "direction_deg", "coherence", "direction_hist8",
                                             "divergence", "curl", "cadence_mad", "new_drawing")},
                {k: None for k in ("particle_count", "particle_vx", "particle_vy", "fall_speed", "downward_share", "streakiness",
                                   "roundness", "turbulence", "particle_area_share", "large_motion_share", "particle_spread")},
                {"fast_layer_share": None, "layer_speed_ratio": None})
    h, w = gray.shape
    flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    xs, ys = coordinate_grids(h, w)

    step = 6
    sx, sy = xs[::step, ::step].ravel(), ys[::step, ::step].ravel()
    src = np.stack([sx, sy], axis=1)
    dst = src + flow[::step, ::step].reshape(-1, 2)
    M, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=0.8)
    if M is None:
        cam, pred = none_cam, np.zeros_like(flow)
    else:
        scale = math.hypot(M[0, 0], M[1, 0])
        cx, cy = w / 2, h / 2
        cam = {"dx": r((M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx) / w, 5), "dy": r((M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy) / w, 5),
               "zoom": r(scale - 1, 5), "roll_deg": r(math.degrees(math.atan2(M[1, 0], M[0, 0])), 3)}
        pred = np.stack([M[0, 0] * xs + M[0, 1] * ys + M[0, 2] - xs, M[1, 0] * xs + M[1, 1] * ys + M[1, 2] - ys], axis=2)

    res = flow - pred
    mag = np.hypot(res[:, :, 0], res[:, :, 1])
    moving = mag > MOVING_PIXEL_PX
    msum = float(mag.sum()) + 1e-9
    vx, vy = float((res[:, :, 0] * mag).sum() / msum), float((res[:, :, 1] * mag).sum() / msum)
    mean_vec = (float(res[:, :, 0][moving].mean()), float(res[:, :, 1][moving].mean())) if moving.any() else (0.0, 0.0)
    ang = np.degrees(np.arctan2(res[:, :, 1], res[:, :, 0])) % 360
    hist = np.bincount((ang[moving] // 45).astype(int) % 8, weights=mag[moving], minlength=8) if moving.any() else np.zeros(8)
    hist = hist / (hist.sum() + 1e-9)
    dfx_dx = np.gradient(res[:, :, 0], axis=1)
    dfy_dy = np.gradient(res[:, :, 1], axis=0)
    dfy_dx = np.gradient(res[:, :, 1], axis=1)
    dfx_dy = np.gradient(res[:, :, 0], axis=0)
    mad = float(np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16)).mean())
    motion = {
        "mean_speed": r(mag.mean() / w, 5), "p95_speed": r(np.percentile(mag, 95) / w, 5), "moving_share": r(moving.mean()),
        "direction_deg": r(math.degrees(math.atan2(mean_vec[1], mean_vec[0])) % 360, 1) if moving.any() else None,
        "coherence": r(math.hypot(*mean_vec) / (mag[moving].mean() + 1e-9)) if moving.any() else None,
        "direction_hist8": [r(x, 3) for x in hist],
        "divergence": r((dfx_dx + dfy_dy).mean(), 5), "curl": r((dfy_dx - dfx_dy).mean(), 5),
        "cadence_mad": r(mad, 3), "new_drawing": bool(mad > 0.6),
    }

    # particles: small moving blobs (petals, snow, rain, dust, sparks). Their mean velocity is the gravity/wind direction.
    mask = cv2.morphologyEx(moving.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask)
    blob_v, aspect, round_, blob_xy, particle_area = [], [], [], [], 0
    large_area = int(sum(stats[k, cv2.CC_STAT_AREA] for k in range(1, n) if stats[k, cv2.CC_STAT_AREA] > PARTICLE_AREA_PX[1]))
    for k in range(1, n):
        area = stats[k, cv2.CC_STAT_AREA]
        if not (PARTICLE_AREA_PX[0] <= area <= PARTICLE_AREA_PX[1]):
            continue
        blob_xy.append((cents[k][0] / w, cents[k][1] / h))
        particle_area += int(area)
        bw, bh = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT]
        sel = labels == k
        blob_v.append((float(res[:, :, 0][sel].mean()), float(res[:, :, 1][sel].mean())))
        aspect.append(max(bh, 1) / max(bw, 1))
        round_.append(area / (math.pi * (max(bw, bh) / 2) ** 2 + 1e-9))
    if blob_v:
        bv = np.array(blob_v)
        physics = {"particle_count": len(blob_v), "particle_vx": r(bv[:, 0].mean() / w, 5), "particle_vy": r(bv[:, 1].mean() / w, 5),
                   "fall_speed": r(max(bv[:, 1].mean(), 0) / w, 5), "downward_share": r((bv[:, 1] > 0.2).mean(), 3),
                   "streakiness": r(np.mean(aspect), 3), "roundness": r(np.mean(round_), 3),
                   "turbulence": r((bv[:, 0].std() + bv[:, 1].std()) / w, 5),
                   "particle_area_share": r(particle_area / (h * w), 5),
                   "large_motion_share": r(large_area / (h * w), 5),
                   "particle_spread": r(float(np.mean(np.std(np.array(blob_xy), axis=0))), 4) if len(blob_xy) > 1 else 0.0}
    else:
        physics = {"particle_count": 0, "large_motion_share": r(large_area / (h * w), 5),
                   **{k: None for k in ("particle_vx", "particle_vy", "fall_speed", "downward_share", "streakiness",
                                        "roundness", "turbulence", "particle_area_share", "particle_spread")}}

    # parallax: split the RAW flow into a fast and a slow layer (Otsu). Foreground moves faster than background under a pan.
    raw = np.hypot(flow[:, :, 0], flow[:, :, 1])
    if raw.max() > 1.0:
        u8 = np.clip(raw / raw.max() * 255, 0, 255).astype(np.uint8)
        t, fastmask = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        fast, slow = raw[fastmask > 0], raw[fastmask == 0]
        layers = {"fast_layer_share": r((fastmask > 0).mean()),
                  "layer_speed_ratio": r(fast.mean() / (slow.mean() + 1e-3)) if fast.size and slow.size else None}
    else:
        layers = {"fast_layer_share": None, "layer_speed_ratio": None}
    return cam, motion, physics, layers


# ----------------------------------------------------------------------------- depth, composition
def measure_depth_and_composition(bgr, gray_u8):
    h, w = gray_u8.shape
    sharp = []
    for gy in range(3):
        for gx in range(3):
            cell = gray_u8[gy * h // 3:(gy + 1) * h // 3, gx * w // 3:(gx + 1) * w // 3]
            sharp.append(float(cv2.Laplacian(cell, cv2.CV_32F).var()))
    sharp_arr = np.array(sharp)
    depth = {"sharpness_grid3x3": [r(x, 2) for x in sharp_arr], "sharpness_centre_over_edges": r(sharp_arr[4] / (np.delete(sharp_arr, 4).mean() + 1e-6), 3)}

    # frequency-tuned saliency: distance of a lightly blurred Lab pixel from the image's mean Lab colour
    lab = cv2.cvtColor(cv2.GaussianBlur(bgr, (0, 0), 2), cv2.COLOR_BGR2LAB).astype(np.float32)
    sal = np.linalg.norm(lab - lab.reshape(-1, 3).mean(axis=0), axis=2)
    mask = (sal > 2 * sal.mean()).astype(np.uint8)
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    if n > 1 and sal.mean() > 1.0:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        cxn, cyn = cents[k][0] / w, cents[k][1] / h
        thirds = [(1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3)]
        comp = {"subject_x": r(cxn), "subject_y": r(cyn), "subject_area": r(stats[k, cv2.CC_STAT_AREA] / (h * w)),
                "subject_bbox": [r(stats[k, cv2.CC_STAT_LEFT] / w), r(stats[k, cv2.CC_STAT_TOP] / h),
                                 r(stats[k, cv2.CC_STAT_WIDTH] / w), r(stats[k, cv2.CC_STAT_HEIGHT] / h)],
                "dist_to_thirds": r(min(math.hypot(cxn - a, cyn - b) for a, b in thirds))}
    else:
        comp = {"subject_x": None, "subject_y": None, "subject_area": None, "subject_bbox": None, "dist_to_thirds": None}

    gx = cv2.Sobel(gray_u8, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray_u8, cv2.CV_32F, 0, 1)
    gm = np.hypot(gx, gy)
    edge_angle = np.degrees(np.arctan2(gy, gx)) % 180            # gradient direction; a horizontal edge has a ~90 deg gradient
    horiz = (np.abs(edge_angle - 90) < 20) & (gm > np.percentile(gm, 90))
    if horiz.sum() > 30:
        comp["horizon_tilt_deg"] = r(np.average(edge_angle[horiz] - 90, weights=gm[horiz]), 2)
        comp["horizon_strength"] = r(gm[horiz].sum() / (gm.sum() + 1e-9), 4)
    else:
        comp["horizon_tilt_deg"] = comp["horizon_strength"] = None
    comp["edge_density"] = r((gm > 60).mean(), 4)
    return depth, comp


# ----------------------------------------------------------------------------- text on screen
SUBTITLE_PRESENT_ABOVE = 0.0005     # calibrated on a real trailer: no-subtitle frames score exactly 0, a short line scores ~0.0015


def measure_text_overlay(bgr, crop):
    """Burned-in subtitles: white strokes with a dark outline in the lower band. Says WHETHER text is on screen and how much;
    what it says is NOT MEASURED here (Whisper gives the spoken words, OCR is not installed). Corner logos are NOT MEASURED."""
    x0, y0, x1, y1 = crop
    im = bgr[y0:y1, x0:x1]
    h, w = im.shape[:2]
    band = im[int(h * 0.72):, int(w * 0.10):int(w * 0.90)]
    white = (band.min(axis=2) > 235).astype(np.uint8)
    dark = (band.max(axis=2) < 60).astype(np.uint8)
    share = float((white & cv2.dilate(dark, np.ones((5, 5), np.uint8))).mean())
    return {"subtitle_stroke_share": r(share, 5), "subtitle_present": share > SUBTITLE_PRESENT_ABOVE,
            "text_content": "NOT MEASURED", "corner_logo": "NOT MEASURED"}


# ----------------------------------------------------------------------------- transitions
def measure_transition(prev_small, cur_small, next_small, cur_mean_luma):
    """Scores at 80 px width; interpretation (cut vs dissolve vs fade) happens per shot in write_shot_scripts.py."""
    def d(a, b):
        return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())

    out = {"mad_prev": None, "mad_next": None, "dissolve_score": None,
           "fade_black_score": r(np.clip(1 - cur_mean_luma / 0.08, 0, 1)), "fade_white_score": r(np.clip((cur_mean_luma - 0.92) / 0.08, 0, 1))}
    if prev_small is not None:
        out["mad_prev"] = r(d(prev_small, cur_small), 3)
    if next_small is not None:
        out["mad_next"] = r(d(cur_small, next_small), 3)
    if prev_small is not None and next_small is not None:
        d_pn = d(prev_small, next_small)
        if d_pn > 8:
            out["dissolve_score"] = r(np.clip(1 - max(d(prev_small, cur_small), d(cur_small, next_small)) / d_pn, 0, 1))
        else:
            out["dissolve_score"] = 0.0
    return out


# ----------------------------------------------------------------------------- one chunk of frames
def describe_chunk(args):
    """args = (paths, first_index, pad_before, pad_after, crop, fps). Rows for the frames after pad_before and before pad_after."""
    paths, first_index, pad_before, pad_after, crop, fps = args
    prepared, full = [], []
    for p in paths:
        bgr = cv2.imread(str(p))
        full.append(bgr)
        prepared.append(prepare_frame(bgr, crop))
    smalls = [cv2.resize(g, (80, max(2, int(g.shape[0] * 80 / g.shape[1]))), interpolation=cv2.INTER_AREA) for _, g in prepared]

    rows = []
    prev_luma = None
    if pad_before:
        prev_luma = float(prepared[pad_before - 1][1].mean() / 255.0)
    for k in range(pad_before, len(paths) - pad_after):
        bgr, gray = prepared[k]
        prev_bgr, prev_gray = (prepared[k - 1] if k > 0 else (None, None))
        light, luma = measure_lighting(bgr, gray, prev_luma)
        cam, motion, physics, layers = measure_motion_and_physics(prev_gray, gray, prev_bgr, bgr)
        depth, comp = measure_depth_and_composition(bgr, gray)
        depth.update(layers)
        idx = first_index + (k - pad_before)
        rows.append({"frame": idx, "t": r(idx / fps, 4), "lighting": light, "colour": measure_colour(bgr),
                     "camera": cam, "motion": motion, "physics": physics, "depth": depth, "composition": comp,
                     "text_on_screen": measure_text_overlay(full[k], crop),
                     "transition": measure_transition(smalls[k - 1] if k > 0 else None, smalls[k],
                                                      smalls[k + 1] if k + 1 < len(smalls) else None, luma)})
        prev_luma = luma
    return rows
