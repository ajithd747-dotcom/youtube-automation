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


HAIR_REACH_FACE_WIDTHS = 1.3     # hair extends at most this many face widths either side of the face centre
HAIR_REACH_FACE_HEIGHTS = 1.5    # ... and at most this many face heights (brows -> chin) above the brows


def hair_region(outline, P):
    """Hair as seen: the measured character outline above the chin (landmark 2), limited to the head's neighbourhood -- the
    segmentation sometimes merges dark background shapes into the character (FF 27: hanging cloth, outline spanning 87% of
    the frame width), and hair does not reach that far. The face is drawn in front of it."""
    fx = (P[0][0] + P[4][0]) / 2
    fw = max(abs(P[4][0] - P[0][0]), 1e-3)
    brow_y = min(p[1] for p in P[5:11])
    fh = max(P[2][1] - brow_y, 1e-3)
    r = clip_half_plane([tuple(p) for p in outline], 0.0, -1.0, -P[2][1])
    for nx, ny, c in ((1.0, 0.0, fx - HAIR_REACH_FACE_WIDTHS * fw), (-1.0, 0.0, -(fx + HAIR_REACH_FACE_WIDTHS * fw)),
                      (0.0, 1.0, brow_y - HAIR_REACH_FACE_HEIGHTS * fh)):
        if len(r) >= 3:
            r = clip_half_plane(r, nx, ny, c)
    return r


def point_in_polygon(x, y, poly):
    inside = False
    for i, (x1, y1) in enumerate(poly):
        x0, y0 = poly[i - 1]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def hair_locks(hair, P, n, aspect):
    """Split the hair region into n locks fanning out from a crown point above the face: wedges between rays from the
    crown, each clipped to the hair polygon, plus the ray segments inside the hair (the ink lines between locks, drawn from
    35% of the way out, where anime strand lines start). Angles are taken in pixel space (y / aspect).
    Returns (wedges [[(x, y)]], rays [[(x, y), (x, y)]])."""
    if len(hair) < 3 or n < 2:
        return [], []
    brow_y = min(p[1] for p in P[5:11])
    top_y = min(p[1] for p in hair)
    cx = (P[0][0] + P[4][0]) / 2
    cy = top_y + 0.25 * (brow_y - top_y)
    ang = lambda x, y: math.atan2((y - cy) / aspect, x - cx)
    angles = sorted(ang(x, y) for x, y in hair)
    gaps = [(angles[(i + 1) % len(angles)] - a) % (2 * math.pi) for i, a in enumerate(angles)]
    k = max(range(len(gaps)), key=lambda i: gaps[i])              # the span starts after the widest empty gap
    a0 = angles[(k + 1) % len(angles)]
    span = (2 * math.pi - gaps[k]) if len(angles) > 1 else 0.0
    bounds = [a0 + span * i / n for i in range(n + 1)]
    wedges, rays = [], []
    for t0, t1 in zip(bounds, bounds[1:]):
        d0 = (math.cos(t0), math.sin(t0) * aspect)
        d1 = (math.cos(t1), math.sin(t1) * aspect)
        w = clip_half_plane(hair, -d0[1], d0[0], -d0[1] * cx + d0[0] * cy)
        w = clip_half_plane(w, d1[1], -d1[0], d1[1] * cx - d1[0] * cy) if len(w) >= 3 else []
        wedges.append(w)
    for t in bounds[1:-1]:
        dx, dy = math.cos(t), math.sin(t) * aspect
        reach = 0.0
        for s in range(1, 200):
            r = s / 200 * 1.5
            if point_in_polygon(cx + dx * r, cy + dy * r, hair):
                reach = r
        if reach > 0:
            rays.append([(cx + dx * reach * 0.35, cy + dy * reach * 0.35), (cx + dx * reach, cy + dy * reach)])
    return wedges, rays
