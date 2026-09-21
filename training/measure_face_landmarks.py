"""Measure each shot's anime face structure: 28 facial landmarks (hysts/anime-face-detector: YOLOv3 face box + HRNetV2
landmarks, plain PyTorch on CPU).

    .venv/bin/python training/measure_face_landmarks.py <slug> [--shots 27,50]

On the first, middle and last frame of every shot (the frames measure_character_outlines.py uses), the largest detected face:
box and 28 points in frame fractions of the content area, each with the model's confidence. Point order (model's own):
0-4 face contour (0 = image-left temple, 2 = chin, 4 = image-right temple), 5-7 / 8-10 brows (image-left / image-right),
11-16 / 17-22 eyes (image-left / image-right; six points around each eye opening), 23 nose, 24-27 mouth -- read off the
drawn landmarks on FF shots 27, 50, 32. Consumers use hulls of the eye/mouth groups, not the order inside a group. A frame without a detection above MIN_SCORE is NOT MEASURED.
Writes training/reference/<slug>/face_landmarks.json, merged into the shot script by write_shot_scripts.py as
characters.face_landmarks.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ.setdefault("HF_HOME", str(ROOT / "tools" / "hf"))
MODEL = "hysts/anime-face-detector 0.1.0 (yolov3 + hrnetv2 28 points)"
MIN_SCORE = 0.5
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
    for s in shots:
        if wanted and s["idx"] not in wanted:
            continue
        entry = []
        for f in sorted({s["start"], (s["start"] + s["end"] - 1) // 2, s["end"] - 1}):
            im = cv2.imread(str(D / "frames" / f"f_{f + 1:05d}.jpg"))[y0:y1, x0:x1]
            face = measure_face_of_frame(detector, im)
            entry.append({"frame": f - s["start"], **(face or {"bbox_xywh": NM, "points": NM})})
        out["shots"][str(s["idx"])] = entry
        print(f"shot {s['idx']}: " + " ".join(f"{e.get('score', '--')}" for e in entry), flush=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
