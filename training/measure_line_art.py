"""Measure each shot's line art -- how much ink, what colour, how thick, which way it runs -- inside and outside the character.

    .venv/bin/python training/measure_line_art.py <slug> [--shots 27,50]

On the frames where training/measure_character_outlines.py measured a silhouette (first, middle, last of the shot), with
burned-in subtitles and logo corners masked out (score_recreation.build_mask):

  edge_density_inside / _outside   share of Canny(60,120) edge pixels inside / outside the measured outline. These are NOT
                                   the scorer's thresholds (80,160), so matching them is not the metric agreeing with itself.
  ink_rgb                          median colour of line pixels inside the outline: pixels >= 12 levels darker than their
                                   own neighbourhood (Gaussian sigma 3) that lie on an edge -- anime ink lines.
  stroke_width_frac                2 x median distance-transform value on the ridge of those line pixels, as a fraction of
                                   frame width.
  edge_density_grid                GRID x GRID edge densities over the outline's bounding box (row-major, top-left first,
                                   NOT MEASURED for cells with no counted pixel inside the outline) -- WHERE the ink is, at a
                                   resolution far too coarse to place a single line.
  vertical_stroke_share            share of edge pixels in the upper half of the outline (hair) whose stroke runs within 30
                                   degrees of vertical -- hair strands fall, so this says how strand-like the hair lines are.

Summary statistics of the picture, never positions of lines: rung 3+ still builds its strokes from the script, not by
tracing the reference (that was rung 2). Shots without a measured outline are NOT MEASURED.
Writes training/reference/<slug>/line_art.json, merged into the shot script by write_shot_scripts.py as characters.line_art.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from score_recreation import build_mask  # noqa: E402

CANNY = (60, 120)
DARKER_BY = 12
VERTICAL_WITHIN_DEG = 30
GRID = 8
NM = "NOT MEASURED"


def polygon_mask(poly, h, w):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.int32(np.array(poly) * [w, h])], 1)
    return m > 0


def measure_line_art_of_frame(bgr, poly, keep):
    """bgr: content-area frame; poly: outline in frame fractions; keep: bool mask of pixels that count. Returns a dict."""
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = (cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), *CANNY) > 0) & keep
    inside = polygon_mask(poly, h, w) & keep
    outside = ~polygon_mask(poly, h, w) & keep
    out = {"edge_density_inside": round(float(edges[inside].mean()), 4) if inside.any() else NM,
           "edge_density_outside": round(float(edges[outside].mean()), 4) if outside.any() else NM}

    xs_, ys_ = np.array(poly)[:, 0], np.array(poly)[:, 1]
    bx0, bx1, by0, by1 = xs_.min() * w, xs_.max() * w, ys_.min() * h, ys_.max() * h
    grid = []
    for gy in range(GRID):
        for gx in range(GRID):
            cell = np.zeros((h, w), bool)
            cell[int(by0 + gy * (by1 - by0) / GRID):int(by0 + (gy + 1) * (by1 - by0) / GRID),
                 int(bx0 + gx * (bx1 - bx0) / GRID):int(bx0 + (gx + 1) * (bx1 - bx0) / GRID)] = True
            cell &= inside
            grid.append(round(float(edges[cell].mean()), 4) if cell.any() else NM)
    out["edge_density_grid"] = grid

    local = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 3)
    dark = (gray.astype(np.float32) < local - DARKER_BY) & inside
    on_line = dark & (cv2.dilate(edges.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    if on_line.sum() >= 30:
        out["ink_rgb"] = [int(v) for v in np.median(bgr[on_line], axis=0)[::-1]]
        dist = cv2.distanceTransform(dark.astype(np.uint8), cv2.DIST_L2, 3)
        ridge = dark & (dist >= cv2.dilate(dist, np.ones((3, 3), np.uint8)))
        out["stroke_width_frac"] = round(float(2 * np.median(dist[ridge]) / w), 5)
    else:
        out["ink_rgb"], out["stroke_width_frac"] = NM, NM

    ys = np.array(poly)[:, 1]
    hair = inside.copy()
    hair[int(h * (ys.min() + ys.max()) / 2):, :] = False
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    sel = edges & hair
    if sel.sum() >= 30:
        stroke_deg = (np.degrees(np.arctan2(gy[sel], gx[sel])) + 90) % 180       # a stroke runs perpendicular to its gradient
        out["vertical_stroke_share"] = round(float((np.abs(stroke_deg - 90) < VERTICAL_WITHIN_DEG).mean()), 4)
    else:
        out["vertical_stroke_share"] = NM
    return out


def summarise(keyframes):
    """Median over the keyframes that measured each field; NM when none did."""
    s = {}
    for k in ("edge_density_inside", "edge_density_outside", "stroke_width_frac", "vertical_stroke_share"):
        v = [e[k] for e in keyframes if isinstance(e.get(k), (int, float))]
        s[k] = round(float(np.median(v)), 5) if v else NM
    cells = []
    for c in range(GRID * GRID):
        v = [e["edge_density_grid"][c] for e in keyframes if isinstance(e.get("edge_density_grid"), list) and isinstance(e["edge_density_grid"][c], float)]
        cells.append(round(float(np.median(v)), 4) if v else NM)
    s["edge_density_grid"] = cells
    inks = [e["ink_rgb"] for e in keyframes if isinstance(e.get("ink_rgb"), list)]
    s["ink_rgb"] = [int(v) for v in np.median(np.array(inks), axis=0)] if inks else NM
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--shots", default="", help="comma list; default all shots with a measured outline")
    a = ap.parse_args()
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    x0, y0, x1, y1 = meta["content_rect_640"]
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    shots = {str(s["idx"]): s for s in json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"]}
    outlines = json.loads((D / "character_outlines.json").read_text(encoding="utf-8"))["shots"]
    wanted = [x.strip() for x in a.shots.split(",") if x.strip()] or list(outlines)
    path = D / "line_art.json"
    out = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out.update({"measured_by": "training/measure_line_art.py", "canny": list(CANNY), "units": "densities = share of pixels; width = fraction of frame width"})
    out.setdefault("shots", {})
    for i in wanted:
        keys = []
        for k in outlines.get(i, []):
            if not isinstance(k["polygon"], list):
                continue
            f = shots[i]["start"] + k["frame"]
            im = cv2.imread(str(D / "frames" / f"f_{f + 1:05d}.jpg"))[y0:y1, x0:x1]
            keep = build_mask(im.shape[0], im.shape[1], bool(rows[f]["text_on_screen"]["subtitle_present"]))
            keys.append({"frame": k["frame"], **measure_line_art_of_frame(im, k["polygon"], keep)})
        out["shots"][i] = {"keyframes": keys, **summarise(keys)} if keys else {"keyframes": [], "summary": NM}
        s = out["shots"][i]
        print(f"shot {i}: " + ("NOT MEASURED (no outline)" if not keys else
              f"inside {s['edge_density_inside']} outside {s['edge_density_outside']} ink {s['ink_rgb']} width {s['stroke_width_frac']} vertical {s['vertical_stroke_share']}"), flush=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
