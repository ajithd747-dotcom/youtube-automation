"""Recreate the 12 s Grease-Pencil anime action reference from scratch with the project's tools.

    python blender_agent/recreate/anime_clip.py [--quality standard] [--rounds N] [--only video|audio|compare]

Pipeline: shot spec (from the reference analysis) -> Blender anime presets (cached per shot) -> concat -> speed-line overlay
(numpy) -> music agent (reference-matched, FluidSynth + numpy FX) -> mux -> benchmark/compare.py against the reference.
The hero and all art are original; only structure, timing, palette logic and audio *characteristics* are matched.
"""
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BA = HERE.parent
ROOT = BA.parent
sys.path.insert(0, str(BA))
sys.path.insert(0, str(ROOT / "agents"))
import blender_runner  # noqa: E402

REF = ROOT / "reference vedios" / "vedios" / "blender reference vedios" / "vidssave.com Blender _ Grease pencil practice _ Fantasy Anime scene 1080P.mp4"
WORK = BA / "work" / "recreate_anime"
OUT = ROOT / "video" / "recreation_anime_action.mp4"
W, H, FPS = 1920, 1080, 24

# (preset, seconds, params) - boundaries measured from the reference (cuts + contact sheet); total 11.7 s
SHOTS = [("plunge", 1.50, {"black_until": 0.9}), ("aerial_dive", 0.80, {}), ("side_lunge", 1.10, {}), ("up_shot", 0.75, {}),
         ("crouch_explosion", 0.80, {}), ("top_down", 0.55, {}), ("smear", 0.35, {}), ("speed_close", 0.60, {}), ("grin_close", 0.55, {}),
         ("black", 0.12, {}), ("back_leap", 0.78, {}), ("ledge_small", 0.65, {}), ("hair_close", 1.00, {}), ("black", 2.15, {})]
# radial speed-line windows (seconds): dive-with-shard, smear, close-up
SPEEDLINES = [(1.95, 2.30, (0.5, 0.62)), (5.50, 5.85, (0.5, 0.5)), (5.90, 6.45, (0.5, 0.55))]


def render_shots(quality="standard"):
    WORK.mkdir(parents=True, exist_ok=True)
    files, t0 = [], 0.0
    for i, (preset, dur, params) in enumerate(SHOTS):
        shot = {"style": "anime", "preset": preset, "params": params}
        key = hashlib.sha1(json.dumps([shot, dur, W, H, FPS, quality, (BA / "blender_side" / "anime_lib.py").stat().st_mtime,
                                        (BA / "blender_side" / "anime_recipes.py").stat().st_mtime, (BA / "blender_side" / "render_shot.py").stat().st_mtime]).encode()).hexdigest()[:10]
        f = WORK / f"shot{i:02d}_{preset}_{key}.mp4"
        if not f.exists():
            t = time.time()
            r = blender_runner.run_job({"shot": shot, "width": W, "height": H, "fps": FPS, "duration": dur, "quality": quality, "mode": "render", "out": str(f)}, timeout=3600)
            if not r.get("ok"):
                raise SystemExit(f"shot {i} {preset} failed: {r.get('error')}\n{r.get('traceback', '')}")
            print(f"[{i + 1}/{len(SHOTS)}] {preset} {dur}s rendered in {time.time() - t:.0f}s", flush=True)
        files.append(f)
        t0 += dur
    return files


def concat(files, out):
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in files), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-c:v", "libx264", "-crf", "16", "-r", str(FPS),
                    "-pix_fmt", "yuv420p", str(out)], cwd=WORK, check=True)


def speedlines(total):
    """RGBA PNG sequence with radial dark speed lines inside the windows; re-randomised every 2nd frame (drawn-on-twos look)."""
    from PIL import Image, ImageDraw
    d = WORK / "speedlines"
    d.mkdir(exist_ok=True)
    n = int(total * FPS)
    empty = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for f in range(n):
        t = f / FPS
        win = next((w for w in SPEEDLINES if w[0] <= t < w[1]), None)
        if win is None:
            im = empty
        else:
            rnd = random.Random(f // 2 + 11)
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            cx, cy = W * win[2][0], H * win[2][1]
            for _ in range(46):
                a = rnd.uniform(0, 2 * math.pi)
                r0 = rnd.uniform(0.38, 0.62) * H
                r1 = r0 + rnd.uniform(0.3, 0.8) * H
                wd = rnd.uniform(0.0015, 0.005)
                x0, y0, x1, y1 = cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1, cy + math.sin(a) * r1
                px, py = -math.sin(a) * wd * H, math.cos(a) * wd * H
                dr.polygon([(x0 - px, y0 - py), (x0 + px, y0 + py), (x1, y1)], fill=(70, 68, 82, 150))
        im.save(d / f"sl_{f:04d}.png")
    return d


def build_video(quality):
    files = render_shots(quality)
    base = WORK / "video_raw.mp4"
    concat(files, base)
    total = sum(s[1] for s in SHOTS)
    d = speedlines(total)
    out = WORK / "video_fx.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(base), "-framerate", str(FPS), "-i", str(d / "sl_%04d.png"), "-filter_complex",
                    "[0:v][1:v]overlay=shortest=1,eq=saturation=0.82:contrast=1.04:gamma=1.02,colorbalance=rm=0.02:bm=0.03:rh=0.02:bh=0.04[v]", "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def build_music(rounds=3):
    from core import load_agent
    music = load_agent("music")
    plan, ref = music.plan_from_reference(str(REF), duration=sum(s[1] for s in SHOTS))
    wav = WORK / "music.wav"
    best = music.refine_to_reference(plan, ref, wav, rounds=rounds)
    (WORK / "music_report.json").write_text(json.dumps(best[1], indent=1), encoding="utf-8")
    return wav, best[1]


def main():
    quality = sys.argv[sys.argv.index("--quality") + 1] if "--quality" in sys.argv else "standard"
    rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 3
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"
    WORK.mkdir(parents=True, exist_ok=True)
    if only in ("all", "video"):
        vid = build_video(quality)
    else:
        vid = WORK / "video_fx.mp4"
    wav, mrep = (build_music(rounds) if only in ("all", "audio") else (WORK / "music.wav", None))
    if only in ("all", "video", "audio"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT)], check=True)
        print("recreation written:", OUT, "music score:", mrep and mrep["score"], flush=True)
    subprocess.run([sys.executable, str(BA / "benchmark" / "compare.py"), str(REF), str(OUT), str(WORK / "compare")], check=True)


if __name__ == "__main__":
    main()
