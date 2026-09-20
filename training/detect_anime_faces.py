"""Anime-face detection for every extracted frame -> characters rows (jsonl).

    PYTHONPATH=tools/cv4 .venv/bin/python training/detect_anime_faces.py <frames_dir> <out.jsonl>

Runs as its own process because the venv's OpenCV 5 dropped CascadeClassifier; OpenCV 4.10 lives in tools/cv4
(installed by tools/README.md steps) and is put first on PYTHONPATH by ingest_reference.py.

A frame with no detection is reported as count 0 with shot_scale null. That means "the detector saw none" -- the
lbpcascade_animeface cascade misses profiles, hair-only shots and stylised faces -- NOT "no character on screen".
"""
import json
import multiprocessing as mp
import sys
from pathlib import Path

import cv2

CASCADE = Path(__file__).resolve().parent.parent / "tools" / "models" / "lbpcascade_animeface.xml"


def shot_scale(face_height_fraction):
    """Framing by the tallest face: extreme close-up, close-up, medium, wide."""
    if face_height_fraction >= 0.5:
        return "ECU"
    if face_height_fraction >= 0.25:
        return "CU"
    if face_height_fraction >= 0.10:
        return "MS"
    return "WS"


def detect_chunk(args):
    paths, first_index = args
    cascade = cv2.CascadeClassifier(str(CASCADE))
    rows = []
    for k, p in enumerate(paths):
        im = cv2.imread(str(p))
        h, w = im.shape[:2]
        gray = cv2.equalizeHist(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
        found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
        faces = [[round(x / w, 4), round(y / h, 4), round(fw / w, 4), round(fh / h, 4)] for x, y, fw, fh in found]
        tallest = max((f[3] for f in faces), default=None)
        rows.append({"frame": first_index + k, "detector": "lbpcascade_animeface", "count": len(faces), "faces": faces,
                     "largest_face_height": tallest, "shot_scale": shot_scale(tallest) if tallest is not None else None})
    return rows


def main(frames_dir, out_jsonl, chunk=48):
    paths = sorted(Path(frames_dir).glob("f_*.jpg"))
    tasks = [(paths[i:i + chunk], i) for i in range(0, len(paths), chunk)]
    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.map(detect_chunk, tasks, chunksize=1)
    rows = [row for part in results for row in part]
    Path(out_jsonl).write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} frames, {sum(1 for x in rows if x['count'])} with a detected face -> {out_jsonl}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
