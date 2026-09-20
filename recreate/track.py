"""Track the camera move of a shot from its background alone.

Whole-frame phase correlation is dragged around by the character - it is the biggest
moving thing in frame - and badly under-reports the real camera move, which then shows
up as a background that will not sit still against the reference.  So the cel is masked
out first and only background pixels vote.

    track_shot(paths, lo, hi) -> [[dx, dy], ...] cumulative, in full-res pixels
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decompose import cel_matte, glow_mask, ink_mask  # noqa: E402


def flow_shift(a_img, b_img, a_m):
    """Translation from sparse optical flow on background corners.

    Phase correlation gives up on this sky - it is nearly featureless once the cel is
    removed - while corners on the horizon and cloud edges track well.  The FX has to be
    excluded alongside the character: the energy bolt travels across frame and, being the
    highest-contrast thing in the shot, otherwise captures the whole estimate.
    """
    ga = cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(b_img, cv2.COLOR_BGR2GRAY)
    mask = ((~a_m) & (glow_mask(a_img) == 0)).astype(np.uint8) * 255
    if mask.mean() < 25:
        return 0.0, 0.0, 0.0
    p0 = cv2.goodFeaturesToTrack(ga, maxCorners=800, qualityLevel=0.006,
                                 minDistance=12, mask=mask, blockSize=9)
    if p0 is None or len(p0) < 12:
        return 0.0, 0.0, 0.0
    p1, st, _ = cv2.calcOpticalFlowPyrLK(
        ga, gb, p0, None, winSize=(31, 31), maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    ok = st.ravel() == 1
    if ok.sum() < 12:
        return 0.0, 0.0, 0.0
    src, dst = p0[ok].reshape(-1, 2), p1[ok].reshape(-1, 2)
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                         ransacReprojThreshold=2.0, maxIters=3000)
    if M is None or inl is None or inl.sum() < 10:
        return 0.0, 0.0, 0.0
    return float(M[0, 2]), float(M[1, 2]), float(inl.mean())


def _prep(img, matte, w=960):
    """Grayscale, downscaled, cel removed, high-passed so flat sky still has signal."""
    h = int(img.shape[0] * w / img.shape[1])
    g = cv2.cvtColor(cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA),
                     cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = cv2.resize(matte.astype(np.uint8) * 255, (w, h),
                   interpolation=cv2.INTER_NEAREST) > 0
    g = g - cv2.GaussianBlur(g, (0, 0), 12)          # high-pass: keep structure, drop level
    g[m] = 0.0                                       # cel pixels do not vote
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    return g * win, (~m)


def pair_shift(a_img, b_img, a_m, b_m, w=960):
    ga, va = _prep(a_img, a_m, w)
    gb, vb = _prep(b_img, b_m, w)
    if va.mean() < 0.15 or vb.mean() < 0.15:         # almost no background visible
        return 0.0, 0.0, 0.0
    (dx, dy), resp = cv2.phaseCorrelate(ga.astype(np.float64), gb.astype(np.float64))
    scale = a_img.shape[1] / w
    return dx * scale, dy * scale, float(resp)


def track_shot(paths, lo, hi, w=960, max_step=90.0):
    """Cumulative background motion, full-res pixels, one entry per frame in [lo,hi)."""
    imgs = [cv2.imread(str(p)) for p in paths[lo:hi]]
    mattes = [cel_matte(im, ink=ink_mask(im)) for im in imgs]
    out = [[0.0, 0.0]]
    for i in range(len(imgs) - 1):
        dx, dy, conf = flow_shift(imgs[i], imgs[i + 1], mattes[i])
        if conf < 0.12:                              # fall back only when RANSAC found nothing
            dx, dy, resp = pair_shift(imgs[i], imgs[i + 1], mattes[i], mattes[i + 1], w)
            if resp < 0.02:
                dx = dy = 0.0
        if abs(dx) > max_step or abs(dy) > max_step:
            dx = dy = 0.0                            # a cut or a bad read; hold still
        out.append([out[-1][0] + dx, out[-1][1] + dy])
    return [[round(x, 2), round(y, 2)] for x, y in out]


if __name__ == "__main__":
    # sanity check: does the tracked vertical move follow the reference horizon?
    paths = sorted(Path(sys.argv[1]).glob("f_*.png"))
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    tr = track_shot(paths, lo, hi)
    ys = []
    for k in range(lo, hi, 4):
        g = cv2.cvtColor(cv2.imread(str(paths[k]))[:, 1300:1900], cv2.COLOR_BGR2GRAY)
        p = cv2.GaussianBlur(g.astype(np.float32).mean(axis=1).reshape(-1, 1), (1, 31), 0)
        ys.append(int(np.argmax(np.abs(np.diff(p.ravel())))))
    print("horizon  :", ys)
    print("tracked dy:", [round(tr[min(k - lo, len(tr) - 1)][1], 1) for k in range(lo, hi, 4)])
    print("horizon d :", [y - ys[0] for y in ys])
