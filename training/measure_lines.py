"""Measured line work of a frame: edge contours as polylines, each with the ink colour sampled from the frame itself.

Everything here is read off pixels (Canny edges of the reference frame at analysis size); nothing is invented. The
parameters are what a recreation iteration adjusts: canny thresholds, minimum contour length, simplification.
"""
import cv2
import numpy as np


def extract_line_segments(bgr, canny=(60, 120), min_len=10, epsilon=0.8, ink_darkness=0.35, keep_mask=None):
    """Returns (seg_a [S,2], seg_b [S,2], seg_rgb [S,3] uint8, n_polylines). Coordinates in pixels of `bgr` (x right, y down)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), canny[0], canny[1])
    if keep_mask is not None:            # burned-in subtitles and streaming logos are overlays, not part of the animation
        edges = edges * keep_mask.astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_len
    edges = (keep[labels] * 255).astype(np.uint8)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    soft = cv2.GaussianBlur(bgr, (0, 0), 2)
    a_list, b_list, c_list, npoly = [], [], [], 0
    for c in contours:
        if len(c) < 2:
            continue
        pl = cv2.approxPolyDP(c, epsilon, False).reshape(-1, 2).astype(np.float64)
        if len(pl) < 2:
            continue
        npoly += 1
        mid = pl[len(pl) // 2].astype(int)
        rgb = soft[min(mid[1], soft.shape[0] - 1), min(mid[0], soft.shape[1] - 1)][::-1].astype(np.float32) * ink_darkness
        a_list.append(pl[:-1]); b_list.append(pl[1:])
        c_list.append(np.repeat(rgb[None, :], len(pl) - 1, axis=0))
    if not a_list:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 3), np.uint8), 0
    return np.concatenate(a_list), np.concatenate(b_list), np.concatenate(c_list).astype(np.uint8), npoly
