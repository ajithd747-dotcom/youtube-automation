"""Measure each shot's character silhouette with an anime segmentation model (skytnt/anime-seg, ISNet, ONNX on CPU).

    .venv/bin/python training/measure_character_outlines.py <slug>

For the first, middle and last frame of every shot: foreground probability at 320x180 -> threshold 0.6 -> largest connected
region -> outer contour simplified to <= 40 points (frame fractions). A shot whose foreground covers < 1% of the frame is
NOT MEASURED (the model misses small full-body figures in wide shots). Writes training/reference/<slug>/character_outlines.json,
merged into the shot script by write_shot_scripts.py as characters.silhouette_outline.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ.setdefault("HF_HOME", str(ROOT / "tools" / "hf"))
MODEL = ("skytnt/anime-seg", "isnetis.onnx")
THRESHOLD = 0.6
MIN_SHARE = 0.01
MAX_POINTS = 40


def load_session():
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    return ort.InferenceSession(hf_hub_download(*MODEL), providers=["CPUExecutionProvider"])


def foreground(sess, bgr, s=1024):
    h, w = bgr.shape[:2]
    k = s / max(h, w)
    nh, nw = int(h * k), int(w * k)
    img = np.zeros((s, s, 3), np.float32)
    ph, pw = (s - nh) // 2, (s - nw) // 2
    img[ph:ph + nh, pw:pw + nw] = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (nw, nh)).astype(np.float32) / 255
    m = sess.run(None, {sess.get_inputs()[0].name: img.transpose(2, 0, 1)[None]})[0][0, 0]
    return cv2.resize(m[ph:ph + nh, pw:pw + nw], (w, h))


def outline_polygon(prob):
    fg = (prob > THRESHOLD).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    if n < 2:
        return None, 0.0
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    fg = (lab == k).astype(np.uint8)
    share = float(fg.mean())
    if share < MIN_SHARE:
        return None, share
    c = max(cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
    eps = 0.003 * cv2.arcLength(c, True)
    while True:
        p = cv2.approxPolyDP(c, eps, True)
        if len(p) <= MAX_POINTS:
            break
        eps *= 1.2
    h, w = fg.shape
    return [[round(float(x) / w, 4), round(float(y) / h, 4)] for x, y in p[:, 0, :]], share


def main():
    frag = sys.argv[1]
    hits = [p for p in (HERE / "reference").iterdir() if p.is_dir() and frag in p.name]
    if len(hits) != 1:
        sys.exit(f"'{frag}' matches {[h.name for h in hits]}")
    D = hits[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    x0, y0, x1, y1 = meta["content_rect_640"]
    shots = json.loads((D / "shots.json").read_text(encoding="utf-8"))["shots"]
    sess = load_session()
    out = {"model": "/".join(MODEL), "threshold": THRESHOLD, "units": "frame fractions (x right, y down), content area", "shots": {}}
    for s in shots:
        keys = sorted({s["start"], (s["start"] + s["end"] - 1) // 2, s["end"] - 1})
        entry = []
        for f in keys:
            im = cv2.imread(str(D / "frames" / f"f_{f + 1:05d}.jpg"))[y0:y1, x0:x1]
            poly, share = outline_polygon(foreground(sess, cv2.resize(im, (320, 180), interpolation=cv2.INTER_AREA)))
            entry.append({"frame": f - s["start"], "foreground_share": round(share, 4), "polygon": poly if poly else "NOT MEASURED"})
        out["shots"][str(s["idx"])] = entry
        print(f"shot {s['idx']}: " + " ".join(f"{e['foreground_share']:.2f}" for e in entry), flush=True)
    (D / "character_outlines.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"-> {D / 'character_outlines.json'}")


if __name__ == "__main__":
    main()
