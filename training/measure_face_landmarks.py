"""Measure each shot's anime face structure: 28 facial landmarks (hysts/anime-face-detector: YOLOv3 face box + HRNetV2
landmarks, plain PyTorch on CPU).

    .venv/bin/python training/measure_face_landmarks.py <slug> [--shots 27,50]

On the first, middle and last frame of every shot (the frames measure_character_outlines.py uses), the largest detected face:
box and 28 points in frame fractions of the content area, each with the model's confidence. Point order (model's own):
0-4 face contour (0 = image-left temple, 2 = chin, 4 = image-right temple), 5-7 / 8-10 brows (image-left / image-right),
11-16 / 17-22 eyes (image-left / image-right; six points around each eye opening), 23 nose, 24-27 mouth -- read off the
drawn landmarks on FF shots 27, 50, 32. Consumers use hulls of the eye/mouth groups, not the order inside a group.
Per face also `hair_tones` (measure_hair_tones: light/dark hair colour and dark share inside the measured outline above
the chin, minus the face) and `tones` (measure_face_tones): skin colour, and the colour, share and side of the darker tone (shadow or bangs). A frame without a detection above MIN_SCORE is NOT MEASURED.
Writes training/reference/<slug>/face_landmarks.json, merged into the shot script by write_shot_scripts.py as
characters.face_landmarks.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from face_geometry import eye_hulls, face_outline, hair_region, mouth_hull  # noqa: E402
os.environ.setdefault("HF_HOME", str(ROOT / "tools" / "hf"))
MODEL = "hysts/anime-face-detector 0.1.0 (yolov3 + hrnetv2 28 points)"
MIN_SCORE = 0.5
MIN_TONE_GAP_L = 8.0             # two skin clusters closer than this in LAB L* are one flat tone: no dark tone
NM = "NOT MEASURED"


def measure_face_of_frame(detector, bgr):
    """Largest face in bgr, or None. Returns {"bbox_xywh", "score", "points" [[x, y, conf]]} in frame fractions."""
    h, w = bgr.shape[:2]
    preds = [p for p in detector(bgr) if float(p["bbox"][4]) >= MIN_SCORE]
    if not preds:
        return None
    p = max(preds, key=lambda q: (q["bbox"][2] - q["bbox"][0]) * (q["bbox"][3] - q["bbox"][1]))
    x0, y0, x1, y1, s = (float(v) for v in p["bbox"])
    return {"bbox_xywh": [round(x0 / w, 4), round(y0 / h, 4), round((x1 - x0) / w, 4), round((y1 - y0) / h, 4)], "score": round(s, 3),
            "points": [[round(float(x) / w, 4), round(float(y) / h, 4), round(float(c), 3)] for x, y, c in p["keypoints"]]}


def measure_face_tones(bgr, points):
    """Two tones inside face_geometry.face_outline, minus eyes, mouth and brows, clustered in LAB: light_rgb (the skin),
    dark_rgb, dark_share, dark_direction_deg (screen angle from the region's centroid to the dark cluster's, 0 = right,
    90 = down). The dark tone is skin shadow OR hair falling over the face (bangs) -- the measurement cannot tell them apart,
    so the name does not claim either. One flat tone when the clusters are < MIN_TONE_GAP_L apart."""
    h, w = bgr.shape[:2]
    px = lambda poly: np.int32([[x * w, y * h] for x, y in poly])
    skin = np.zeros((h, w), np.uint8)
    cv2.fillPoly(skin, [px(face_outline(points))], 1)
    cut = np.zeros((h, w), np.uint8)
    for poly in (*eye_hulls(points), mouth_hull(points)):
        if len(poly) >= 3:
            cv2.fillPoly(cut, [px(poly)], 1)
    for brow in (points[5:8], points[8:11]):
        cv2.polylines(cut, [px(sorted((p[0], p[1]) for p in brow))], False, 1, 3)
    cut = cv2.dilate(cut, np.ones((5, 5), np.uint8))
    m = (skin > 0) & (cut == 0)
    if m.sum() < 50:
        return {"light_rgb": NM, "dark_rgb": NM, "dark_share": NM, "dark_direction_deg": NM}
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[m].astype(np.float32)
    _, lab_idx, centres = cv2.kmeans(lab, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    lab_idx = lab_idx.ravel()
    light = int(np.argmax(centres[:, 0]))
    rgb = bgr[m][:, ::-1]
    light_rgb = [int(v) for v in np.median(rgb[lab_idx == light], axis=0)]
    if abs(centres[0, 0] - centres[1, 0]) * 100 / 255 < MIN_TONE_GAP_L:          # OpenCV L* is 0..255
        return {"light_rgb": [int(v) for v in np.median(rgb, axis=0)], "dark_rgb": NM, "dark_share": 0.0, "dark_direction_deg": NM}
    ys, xs = np.nonzero(m)
    sh = lab_idx != light
    ang = float(np.degrees(np.arctan2(ys[sh].mean() - ys.mean(), xs[sh].mean() - xs.mean())) % 360)
    return {"light_rgb": light_rgb, "dark_rgb": [int(v) for v in np.median(rgb[sh], axis=0)], "dark_share": round(float(sh.mean()), 3),
            "dark_direction_deg": round(ang, 1)}


def measure_hair_tones(bgr, points, outline):
    """Two LAB tones of the hair: inside face_geometry.hair_region (measured outline above the chin) minus the face.
    light_rgb, dark_rgb, dark_share. NOT MEASURED without an outline or with < 50 hair pixels."""
    nm = {"light_rgb": NM, "dark_rgb": NM, "dark_share": NM}
    if not isinstance(outline, list):
        return nm
    h, w = bgr.shape[:2]
    px = lambda poly: np.int32([[x * w, y * h] for x, y in poly])
    region = hair_region(outline, points)
    if len(region) < 3:
        return nm
    hair = np.zeros((h, w), np.uint8)
    cv2.fillPoly(hair, [px(region)], 1)
    cv2.fillPoly(hair, [px(face_outline(points))], 0)
    m = hair > 0
    if m.sum() < 50:
        return nm
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[m].astype(np.float32)
    _, idx, centres = cv2.kmeans(lab, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    idx = idx.ravel()
    light = int(np.argmax(centres[:, 0]))
    rgb = bgr[m][:, ::-1]
    return {"light_rgb": [int(v) for v in np.median(rgb[idx == light], axis=0)], "dark_rgb": [int(v) for v in np.median(rgb[idx != light], axis=0)],
            "dark_share": round(float((idx != light).mean()), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--shots", default="")
    a = ap.parse_args()
    from anime_face_detector import create_detector
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    x0, y0, x1, y1 = json.loads((D / "meta.json").read_text(encoding="utf-8"))["content_rect_640"]
    shots = json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"]
    wanted = {int(x) for x in a.shots.split(",") if x.strip()}
    path = D / "face_landmarks.json"
    out = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"shots": {}}
    out.update({"model": MODEL, "min_score": MIN_SCORE, "units": "frame fractions (x right, y down), content area; point = [x, y, confidence]"})
    detector = create_detector("yolov3", device="cpu")
    ol_path = D / "character_outlines.json"
    outlines = json.loads(ol_path.read_text(encoding="utf-8"))["shots"] if ol_path.exists() else {}
    for s in shots:
        if wanted and s["idx"] not in wanted:
            continue
        entry = []
        for f in sorted({s["start"], (s["start"] + s["end"] - 1) // 2, s["end"] - 1}):
            im = cv2.imread(str(D / "frames" / f"f_{f + 1:05d}.jpg"))[y0:y1, x0:x1]
            face = measure_face_of_frame(detector, im)
            if face:
                face["tones"] = measure_face_tones(im, face["points"])
                ol = next((k["polygon"] for k in outlines.get(str(s["idx"]), []) if k["frame"] == f - s["start"]), None)
                face["hair_tones"] = measure_hair_tones(im, face["points"], ol)
            entry.append({"frame": f - s["start"], **(face or {"bbox_xywh": NM, "points": NM})})
        out["shots"][str(s["idx"])] = entry
        print(f"shot {s['idx']}: " + " ".join(f"{e.get('score', '--')}" for e in entry), flush=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
