"""Score a recreation against its reference, frame by frame -- the feedback signal of the training loop.

    .venv/bin/python training/score_recreation.py <slug> <recreation video | frames dir> [--start 0] [--shots 3,7-9] [--run NAME]

Compares reference frame (start + i) with recreation frame i, at reference analysis size, over the picture area only
(letterbox removed) and with burned-in subtitles masked out on the frames where the reference measured them. Missing
recreation frames score 0: a recreation that renders half the shot does not get credit for the half it skipped.

Metrics per frame (see training/SPEC.md section 1): ssim, hist, edge_f1, dhue -> frame_score.
Two holdouts, reported and never tuned against: grad_ssim_holdout (structure of gradient maps, pixel-exact) and
lpips_holdout = 1 - LPIPS(alex) distance (learned perceptual similarity; tolerant of small offsets and style), the latter on
at most LPIPS_MAX_FRAMES evenly spaced frames per run.
Writes training/runs/<slug>/<run>/scores.json and worst_frames.jpg.
"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity

HERE = Path(__file__).resolve().parent
os.environ.setdefault("TORCH_HOME", str(HERE.parent / "tools" / "torch"))     # AlexNet weights stay inside the project
REF = HERE / "reference"
RUNS = HERE / "runs"
WEIGHTS = {"ssim": 0.40, "hist": 0.25, "edge_f1": 0.25, "colour": 0.10}
SUBTITLE_BAND_FROM = 0.72
LOGO_CORNERS = ((0.0, 0.13, 0.0, 0.34), (0.0, 0.13, 0.82, 1.0))   # (y0, y1, x0, x1) fractions: title text top-left, streaming logo top-right


def build_mask(h, w, subtitle_present, mask_corners=True):
    m = np.ones((h, w), bool)
    if subtitle_present:
        m[int(h * SUBTITLE_BAND_FROM):, :] = False
    if mask_corners:
        for y0, y1, x0, x1 in LOGO_CORNERS:
            m[int(h * y0):int(h * y1), int(w * x0):int(w * x1)] = False
    return m


def edge_map(gray):
    return cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 80, 160) > 0


def score_frame_pair(ref, rec, mask=None):
    """ref, rec: BGR uint8 of identical size. mask: bool array, True = pixels that count."""
    if mask is None:
        mask = np.ones(ref.shape[:2], bool)
    gr, gc = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), cv2.cvtColor(rec, cv2.COLOR_BGR2GRAY)
    _, smap = structural_similarity(gr, gc, full=True, data_range=255)
    ssim = float(smap[mask].mean())

    lab_r, lab_c = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB), cv2.cvtColor(rec, cv2.COLOR_BGR2LAB)
    m8 = mask.astype(np.uint8)
    hr = cv2.calcHist([lab_r], [0, 1, 2], m8, [8, 8, 8], [0, 256] * 3).ravel()
    hc = cv2.calcHist([lab_c], [0, 1, 2], m8, [8, 8, 8], [0, 256] * 3).ravel()
    hist = float(np.minimum(hr / (hr.sum() + 1e-9), hc / (hc.sum() + 1e-9)).sum())

    er, ec = edge_map(gr) & mask, edge_map(gc) & mask
    k = np.ones((5, 5), np.uint8)
    prec = float((ec & (cv2.dilate(er.astype(np.uint8), k) > 0)).sum() / max(ec.sum(), 1))
    reca = float((er & (cv2.dilate(ec.astype(np.uint8), k) > 0)).sum() / max(er.sum(), 1))
    if er.sum() == 0 and ec.sum() == 0:
        f1 = 1.0
    else:
        f1 = 2 * prec * reca / (prec + reca) if prec + reca > 0 else 0.0

    # HOLDOUT (not part of frame_score, never tuned against): structure similarity of Sobel gradient magnitudes. A recreation that only
    # traces Canny edges to please edge_f1 cannot fake this one, because it looks at edge strength and shape, not a binary edge map.
    def grad_mag(g):
        g = cv2.GaussianBlur(g, (0, 0), 1.2)
        return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    mr, mc = grad_mag(gr), grad_mag(gc)
    top = max(float(mr.max()), 1.0)
    _, gmap = structural_similarity(np.clip(mr / top * 255, 0, 255).astype(np.uint8), np.clip(mc / top * 255, 0, 255).astype(np.uint8), full=True, data_range=255)
    grad_ssim = float(gmap[mask].mean())

    dhue = float(np.abs(lab_r[:, :, 1:].astype(int) - lab_c[:, :, 1:].astype(int))[mask].mean())
    colour = 1.0 - min(dhue / 20.0, 1.0)
    score = WEIGHTS["ssim"] * max(ssim, 0.0) + WEIGHTS["hist"] * hist + WEIGHTS["edge_f1"] * f1 + WEIGHTS["colour"] * colour
    return {"ssim": round(ssim, 4), "hist": round(hist, 4), "edge_f1": round(f1, 4), "dhue": round(dhue, 3), "frame_score": round(score, 4),
            "grad_ssim_holdout": round(grad_ssim, 4)}, 1.0 - smap


LPIPS_MAX_FRAMES = 300
_LPIPS = {}


def lpips_similarity(ref, rec, mask=None):
    """1 - LPIPS(alex) distance between two BGR uint8 frames of the same size; pixels outside `mask` (subtitles, logos) are
    copied from the reference into the recreation first, so they cannot count either way."""
    import torch
    if "net" not in _LPIPS:
        import lpips
        _LPIPS["net"] = lpips.LPIPS(net="alex", verbose=False).eval()
    if mask is not None:
        rec = np.where(mask[:, :, None], rec, ref)
    t = lambda im: torch.from_numpy(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)).permute(2, 0, 1)[None].float() / 127.5 - 1.0
    with torch.no_grad():
        return 1.0 - float(_LPIPS["net"](t(ref), t(rec)))


def crop_to_content(img, rect):
    x0, y0, x1, y1 = rect
    return img[y0:y1, x0:x1]


def load_reference_frame(slug_dir, i, rect):
    return crop_to_content(cv2.imread(str(slug_dir / "frames" / f"f_{i + 1:05d}.jpg")), rect)


def prepare_recreation_frames(source, work_dir, size_wh, count):
    """Frames dir for a recreation: a video is decoded to numbered PNGs at reference analysis size."""
    source = Path(source)
    if source.is_dir():
        return sorted(p for p in source.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    work_dir.mkdir(parents=True, exist_ok=True)
    for old in work_dir.glob("r_*.png"):
        old.unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-vf", f"scale={size_wh[0]}:{size_wh[1]}:flags=area",
                    "-fps_mode", "passthrough", "-frames:v", str(count), str(work_dir / "r_%05d.png")], check=True)
    return sorted(work_dir.glob("r_*.png"))


def score_chunk(args):
    slug_dir, rect, pairs, rec_paths, sub_flags, mask_corners = args
    out = []
    for i, ri in pairs:
        ref = load_reference_frame(Path(slug_dir), ri, rect)
        if i >= len(rec_paths):
            out.append({"frame": ri, "ssim": 0.0, "hist": 0.0, "edge_f1": 0.0, "dhue": None, "frame_score": 0.0, "missing": True})
            continue
        rec = cv2.imread(str(rec_paths[i]))
        if rec.shape[:2] != ref.shape[:2]:
            rec = cv2.resize(rec, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
        sc, _ = score_frame_pair(ref, rec, build_mask(ref.shape[0], ref.shape[1], sub_flags[ri], mask_corners))
        sc["frame"] = ri
        out.append(sc)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("recreation")
    ap.add_argument("--start", type=int, default=0, help="reference frame that recreation frame 0 corresponds to")
    ap.add_argument("--end", type=int, default=None, help="last reference frame (exclusive); default = start + recreation frames")
    ap.add_argument("--run", default="run")
    ap.add_argument("--no-corner-mask", action="store_true")
    a = ap.parse_args()

    hits = [p for p in REF.iterdir() if p.is_dir() and a.slug in p.name]
    if len(hits) != 1:
        sys.exit(f"'{a.slug}' matches {[h.name for h in hits]}")
    D = hits[0]
    meta = json.loads((D / "meta.json").read_text(encoding="utf-8"))
    rect = tuple(meta["content_rect_640"])
    rows = [json.loads(x) for x in (D / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    sub_flags = [bool(r["text_on_screen"]["subtitle_present"]) for r in rows]
    shot_of = [r["shot"] for r in rows]
    size_wh = (rect[2] - rect[0], rect[3] - rect[1])

    run_dir = RUNS / D.name / a.run
    run_dir.mkdir(parents=True, exist_ok=True)
    src = Path(a.recreation)
    n_hint = (a.end - a.start) if a.end else len(rows) - a.start
    rec_paths = prepare_recreation_frames(src, run_dir / "frames", size_wh, n_hint)
    end = a.end if a.end else min(len(rows), a.start + len(rec_paths))
    pairs = [(i, a.start + i) for i in range(end - a.start)]
    chunks = [(str(D), rect, pairs[k:k + 24], rec_paths, sub_flags, not a.no_corner_mask) for k in range(0, len(pairs), 24)]
    with mp.Pool(os.cpu_count() or 4) as pool:
        frames = [row for part in pool.map(score_chunk, chunks, chunksize=1) for row in part]
    frames.sort(key=lambda r: r["frame"])
    step = max(1, -(-len(frames) // LPIPS_MAX_FRAMES))
    for r in frames[::step]:
        if r.get("missing"):
            r["lpips_holdout"] = 0.0
            continue
        ref = load_reference_frame(D, r["frame"], rect)
        rec = cv2.imread(str(rec_paths[r["frame"] - a.start]))
        if rec.shape[:2] != ref.shape[:2]:
            rec = cv2.resize(rec, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
        r["lpips_holdout"] = round(lpips_similarity(ref, rec, build_mask(ref.shape[0], ref.shape[1], sub_flags[r["frame"]], not a.no_corner_mask)), 4)

    per_shot = {}
    for r in frames:
        per_shot.setdefault(shot_of[r["frame"]], []).append(r)
    shots = {str(k): {"frames": len(v), "frame_score": round(float(np.mean([x["frame_score"] for x in v])), 4),
                      "ssim": round(float(np.mean([x["ssim"] for x in v])), 4), "hist": round(float(np.mean([x["hist"] for x in v])), 4),
                      "edge_f1": round(float(np.mean([x["edge_f1"] for x in v])), 4),
                      "lpips_holdout": round(float(np.mean([x["lpips_holdout"] for x in v if "lpips_holdout" in x])), 4) if any("lpips_holdout" in x for x in v) else None}
             for k, v in sorted(per_shot.items())}
    overall = {k: round(float(np.mean([x.get(k, 0.0) for x in frames])), 4) for k in ("frame_score", "ssim", "hist", "edge_f1", "grad_ssim_holdout")}
    overall["lpips_holdout"] = round(float(np.mean([x["lpips_holdout"] for x in frames if "lpips_holdout" in x])), 4)
    overall["dhue"] = round(float(np.mean([x["dhue"] for x in frames if x["dhue"] is not None])), 3) if any(x["dhue"] is not None for x in frames) else None
    coverage = round(sum(1 for x in frames if not x.get("missing")) / max(len(frames), 1), 4)
    worst = sorted(frames, key=lambda r: r["frame_score"])[:8]
    (run_dir / "scores.json").write_text(json.dumps({"slug": D.name, "run": a.run, "reference_start": a.start, "n_frames": len(frames), "coverage": coverage,
                                                     "overall": overall, "shots": shots, "worst": worst, "frames": frames}, indent=1), encoding="utf-8")

    tiles = []
    for r in worst:
        if r.get("missing"):
            continue
        ref = load_reference_frame(D, r["frame"], rect)
        rec = cv2.imread(str(rec_paths[r["frame"] - a.start]))
        rec = cv2.resize(rec, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
        _, err = score_frame_pair(ref, rec)
        heat = cv2.applyColorMap((np.clip(err, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        row = np.hstack([cv2.resize(x, (400, 225)) for x in (ref, rec, heat)])
        cv2.putText(row, f"f{r['frame']} score={r['frame_score']:.3f} ssim={r['ssim']:.3f}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(row)
    if tiles:
        cv2.imwrite(str(run_dir / "worst_frames.jpg"), np.vstack(tiles))
    print(f"{D.name} run '{a.run}': {len(frames)} frames, coverage {coverage:.0%}")
    print("  overall " + "  ".join(f"{k}={v}" for k, v in overall.items()))
    print(f"  worst shots: " + ", ".join(f"S{k}={v['frame_score']}" for k, v in sorted(shots.items(), key=lambda kv: kv[1]['frame_score'])[:5]))
    print(f"  -> {run_dir}/scores.json  worst_frames.jpg")


if __name__ == "__main__":
    main()
