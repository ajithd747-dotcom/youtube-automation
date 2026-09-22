"""Split every reference video into individual frames and measure them all (Layer A of the per-frame script).

    .venv/bin/python training/ingest_reference.py                 # every video in "reference vedios/"
    .venv/bin/python training/ingest_reference.py --only fragrant # slugs containing this text
    .venv/bin/python training/ingest_reference.py --force         # redo finished stages

Per video, under training/reference/<slug>/ (gitignored: these are other people's videos):
    meta.json            probe data, content rectangle (letterbox removed), measurement settings
    frames/f_00001.jpg   EVERY frame at 640 px wide, in order (file number = frame index + 1)
    frames_table.jsonl   one measured row per frame: lighting, colour, camera, motion, physics, depth, composition,
                         transition, audio, characters, text_on_screen ("NOT MEASURED")
    shots.json           shot boundaries
    audio.wav            mono 22.05 kHz
Uses every core: ffmpeg per video in parallel, then one worker per core over frame chunks, then the face detector.
"""
import argparse
import concurrent.futures as cf
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "blender_agent"))
sys.path.insert(0, str(ROOT / "recreate"))
import describe_frames as DF  # noqa: E402
from describe_audio import measure_audio_per_frame  # noqa: E402
from skill_extract import slug as slug_of  # noqa: E402

REF_DIR = ROOT / "reference vedios"
OUT = HERE / "reference"
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
FRAME_WIDTH = 640
CHUNK = 64
CPU = os.cpu_count() or 4


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def probe_video(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    d = json.loads(r.stdout)
    v = d["streams"][0]
    n, den = v["avg_frame_rate"].split("/")
    return {"width": v["width"], "height": v["height"], "fps": float(n) / float(den), "fps_rational": v["avg_frame_rate"],
            "nb_frames": int(v["nb_frames"]), "duration": float(d["format"]["duration"]), "codec": v["codec_name"]}


def extract_all_frames(video, frames_dir, n_expected, threads):
    frames_dir.mkdir(parents=True, exist_ok=True)
    if len(list(frames_dir.glob("f_*.jpg"))) == n_expected:
        return
    for old in frames_dir.glob("f_*.jpg"):
        old.unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-threads", str(threads), "-i", str(video),
                    "-vf", f"scale={FRAME_WIDTH}:-2:flags=area", "-fps_mode", "passthrough", "-q:v", "3",
                    str(frames_dir / "f_%05d.jpg")], check=True)


def extract_audio(video, wav):
    if not wav.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "22050", str(wav)], check=True)


def find_video_content_rect(paths):
    idx = np.linspace(0, len(paths) - 1, 40).astype(int)
    return DF.find_content_rect([cv2.imread(str(paths[i])) for i in idx])


ISOLATED_CUT_MAD = 22.0          # same mean-abs-difference floor as make_script.detect_cuts
ISOLATED_CUT_NEIGHBOUR_SHARE = 0.3  # both frame differences either side stay below this share of the jump
ISOLATED_CUT_MAX_NCC = 0.3       # blurred-gray correlation across the jump; real missed cuts measured <= 0.22, a
                                 # redrawn close-up inside a shot 0.43 (FF 809) -- checked by eye on Fragrant and Blue Box
ISOLATED_CUT_MIN_HIST = 0.6      # ... or the colour histogram jumps like a raw cut (make_script.detect_cuts hist_th): BB 2165
                                 # (correlation 0.45, histogram 1.45) was folded away by min_len; redraws measured <= 0.26


def detect_isolated_cuts(small):
    """Cuts the colour-histogram test misses or merge_similar folds away: one frame whose picture changes structurally or
    in colour while the frames around it hold (a cut inside the same room -- FF 1698 -- or a short shot less than min_len
    after the previous cut -- FF 1268, BB 2165). Runs of flashes and fast action are not isolated, so they are not caught."""
    import make_script as MS
    hs = MS.hists(small)
    gray = [cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2) for im in small]
    mad = np.array([0.0] + [float(np.abs(small[i - 1].astype(np.int16) - small[i].astype(np.int16)).mean()) for i in range(1, len(small))])
    cuts = []
    for i in range(2, len(small) - 2):
        if mad[i] <= ISOLATED_CUT_MAD or max(mad[i - 2:i].max(), mad[i + 1:i + 3].max()) >= ISOLATED_CUT_NEIGHBOUR_SHARE * mad[i]:
            continue
        if (float(np.corrcoef(gray[i - 1].ravel(), gray[i].ravel())[0, 1]) < ISOLATED_CUT_MAX_NCC
                or float(np.abs(hs[i - 1] - hs[i]).sum()) > ISOLATED_CUT_MIN_HIST):
            cuts.append(i)
    return cuts


def detect_shots(paths, fps):
    """Shot boundaries with the same cut logic the 2D-animation pipeline already uses (recreate/make_script.py), plus
    isolated structural cuts, which are always kept."""
    import make_script as MS
    small = MS.load_small(paths)
    hs = MS.hists(small)
    bounds = MS.merge_similar([0] + MS.detect_cuts(small, hs) + [len(small)], hs)
    bounds = sorted(set(bounds) | set(detect_isolated_cuts(small)))
    return [{"idx": i, "start": lo, "end": hi, "n": hi - lo, "t_start": round(lo / fps, 4), "dur": round((hi - lo) / fps, 4)}
            for i, (lo, hi) in enumerate(zip(bounds, bounds[1:]))]


def detect_shots_for(args):
    slug_name, fps = args
    paths = sorted((OUT / slug_name / "frames").glob("f_*.jpg"))
    return slug_name, detect_shots(paths, fps)


def run_faces(slug_name):
    out = OUT / slug_name / "faces.jsonl"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "tools" / "cv4")}
    subprocess.run([sys.executable, str(HERE / "detect_anime_faces.py"), str(OUT / slug_name / "frames"), str(out)], check=True, env=env)
    return [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    videos = sorted(p for p in REF_DIR.iterdir() if p.suffix.lower() in VIDEO_EXT and a.only in slug_of(p))
    if not videos:
        sys.exit("no reference videos matched")
    jobs = {slug_of(p): {"video": p, "meta": probe_video(p)} for p in videos}
    todo = {s: j for s, j in jobs.items() if a.force or not (OUT / s / "frames_table.jsonl").exists()}
    for s, j in jobs.items():
        m = j["meta"]
        log(f"{s}: {m['width']}x{m['height']} {m['fps']:.3f} fps {m['nb_frames']} frames {m['duration']:.1f}s" + ("" if s in todo else "  (already ingested)"))
    if not todo:
        return

    log(f"stage 1/6 extract every frame ({len(todo)} videos in parallel)")
    per = max(2, CPU // len(todo))
    with cf.ThreadPoolExecutor(len(todo)) as ex:
        list(ex.map(lambda s: extract_all_frames(todo[s]["video"], OUT / s / "frames", todo[s]["meta"]["nb_frames"], per), todo))
        list(ex.map(lambda s: extract_audio(todo[s]["video"], OUT / s / "audio.wav"), todo))
    for s, j in todo.items():
        n = len(list((OUT / s / "frames").glob("f_*.jpg")))
        assert n == j["meta"]["nb_frames"], f"{s}: extracted {n} frames, ffprobe says {j['meta']['nb_frames']}"
        j["paths"] = sorted((OUT / s / "frames").glob("f_*.jpg"))
        j["crop"] = find_video_content_rect(j["paths"])
        log(f"  {s}: {n} frames extracted, content rect {j['crop']} of {FRAME_WIDTH}x{cv2.imread(str(j['paths'][0])).shape[0]}")

    log(f"stage 2/6 measure lighting/colour/motion/physics/depth/composition/transitions on {CPU} cores")
    tasks = []
    for s, j in todo.items():
        n = len(j["paths"])
        for lo in range(0, n, CHUNK):
            hi = min(lo + CHUNK, n)
            plo, phi = max(lo - 1, 0), min(hi + 1, n)
            tasks.append((s, (j["paths"][plo:phi], lo, lo - plo, phi - hi, j["crop"], j["meta"]["fps"])))
    t0 = time.time()
    rows = {s: [] for s in todo}
    with mp.Pool(CPU) as pool:
        for k, (s, out) in enumerate(zip([t[0] for t in tasks], pool.imap(DF.describe_chunk, [t[1] for t in tasks], chunksize=1))):
            rows[s].extend(out)
            if k % 40 == 0:
                log(f"  {k + 1}/{len(tasks)} chunks ({time.time() - t0:.0f}s)")
    log(f"  measured {sum(len(v) for v in rows.values())} frames in {time.time() - t0:.0f}s")

    log("stage 3/6 anime-face detection (OpenCV 4 in tools/cv4)")
    faces = {s: run_faces(s) for s in todo}

    log("stage 4/6 audio per frame")
    audio = {s: measure_audio_per_frame(OUT / s / "audio.wav", j["meta"]["fps"], j["meta"]["nb_frames"]) for s, j in todo.items()}

    log("stage 5/6 shot boundaries")
    with cf.ProcessPoolExecutor(min(len(todo), CPU)) as ex:
        shots = dict(ex.map(detect_shots_for, [(s, j["meta"]["fps"]) for s, j in todo.items()]))

    log("stage 6/6 write tables")
    for s, j in todo.items():
        rs = sorted(rows[s], key=lambda x: x["frame"])
        for row, fc, au in zip(rs, faces[s], audio[s]):
            assert row["frame"] == fc["frame"], "frame misalignment between measurement and face detection"
            row["characters"] = {k: v for k, v in fc.items() if k != "frame"}
            row["audio"] = au
        for sh in shots[s]:
            for row in rs[sh["start"]:sh["end"]]:
                row["shot"] = sh["idx"]
        (OUT / s / "frames_table.jsonl").write_text("\n".join(json.dumps(x) for x in rs) + "\n", encoding="utf-8")
        (OUT / s / "shots.json").write_text(json.dumps({"slug": s, "fps": j["meta"]["fps"], "n_frames": len(rs), "shots": shots[s]}, indent=1), encoding="utf-8")
        (OUT / s / "meta.json").write_text(json.dumps({**j["meta"], "slug": s, "source": j["video"].name, "content_rect_640": list(j["crop"]),
                                                        "frame_width": FRAME_WIDTH, "measure_width": DF.MEASURE_WIDTH,
                                                        "units": "positions = frame fractions (x right, y down); speeds = frame widths per frame; angles deg, 0=right 90=down; luma 0..1"},
                                                       indent=1), encoding="utf-8")
        log(f"  {s}: {len(rs)} rows, {len(shots[s])} shots")
    log("done")


if __name__ == "__main__":
    main()
