"""Face shapes derived from the 28 anime face landmarks (training/measure_face_landmarks.py order). Pure Python (math only) so
the measurement side and Blender (training/blender_level3.py) use the same polygons -- what is measured is what is drawn.

Points are (x, y) frame fractions, y down: 0-4 jaw contour (image-left temple -> chin -> image-right temple), 5-7 / 8-10
brows, 11-16 / 17-22 eyes (six points around each opening), 23 nose, 24-27 mouth.
"""
import math

FOREHEAD_ABOVE_BROWS = 0.35      # forehead top = brows - this x (eye line - brow line): anime bangs begin just above the brows


def hull_pts(pts):
    """Convex hull, counter-clockwise, so a landmark group becomes a polygon whatever its point order."""
    pts = sorted(set(map(tuple, pts)))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def face_outline(P):
    """Skin area of the face: the jaw contour closed by an arc that tops out just above the brows."""
    jaw = [tuple(p[:2]) for p in P[0:5]]
    brow_y = min(p[1] for p in P[5:11])
    eye_y = sum(p[1] for p in P[11:23]) / 12
    top = brow_y - FOREHEAD_ABOVE_BROWS * max(eye_y - brow_y, 0.02)
    (lx, ly), (rx, ry) = jaw[0], jaw[4]
    cx, rw = (lx + rx) / 2, (rx - lx) / 2
    arc = [(cx + rw * math.cos(math.pi * k / 12), min(ly, ry) - (min(ly, ry) - top) * math.sin(math.pi * k / 12)) for k in range(1, 12)]
    return jaw + arc


def eye_hulls(P):
    return hull_pts([tuple(p[:2]) for p in P[11:17]]), hull_pts([tuple(p[:2]) for p in P[17:23]])


def mouth_hull(P):
    return hull_pts([tuple(p[:2]) for p in P[24:28]])


def clip_half_plane(pts, nx, ny, c):
    """Sutherland-Hodgman clip of polygon pts to the half-plane nx*x + ny*y >= c."""
    out = []
    for i, (x1, y1) in enumerate(pts):
        x0, y0 = pts[i - 1]
        s0, s1 = nx * x0 + ny * y0 - c, nx * x1 + ny * y1 - c
        if (s0 >= 0) != (s1 >= 0):
            t = s0 / (s0 - s1)
            out.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
        if s1 >= 0:
            out.append((x1, y1))
    return out


def polygon_area(pts):
    return abs(sum(pts[i - 1][0] * p[1] - p[0] * pts[i - 1][1] for i, p in enumerate(pts))) / 2


def shadow_polygon(face, direction_deg, share, aspect):
    """The part of `face` lying toward `direction_deg` (screen angle, 0 = right, 90 = down) that covers `share` of its area:
    a straight terminator perpendicular to the direction, found by bisection. aspect = width / height of the frame, so the
    direction is measured in pixels, not fractions."""
    if share <= 0.01 or len(face) < 3:
        return []
    a = math.radians(direction_deg)
    nx, ny = math.cos(a), math.sin(a) / aspect                  # pixel-space direction expressed in frame fractions
    proj = [nx * x + ny * y for x, y in face]
    lo, hi = min(proj), max(proj)
    total = polygon_area(face)
    for _ in range(30):
        mid = (lo + hi) / 2
        if polygon_area(clip_half_plane(face, nx, ny, mid)) / total > share:
            lo = mid
        else:
            hi = mid
    return clip_half_plane(face, nx, ny, (lo + hi) / 2)


def interpolate_points(keys, frame):
    """keys: [{"frame", "points"}] sorted by frame; linear in time between the measured keyframes, held at the ends."""
    if frame <= keys[0]["frame"]:
        return keys[0]["points"]
    if frame >= keys[-1]["frame"]:
        return keys[-1]["points"]
    for k0, k1 in zip(keys, keys[1:]):
        if k0["frame"] <= frame <= k1["frame"]:
            t = (frame - k0["frame"]) / max(k1["frame"] - k0["frame"], 1)
            return [[a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), min(a[2], b[2])] for a, b in zip(k0["points"], k1["points"])]
    return keys[-1]["points"]
